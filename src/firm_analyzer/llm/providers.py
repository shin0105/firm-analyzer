#!/usr/bin/env python3
"""One interface over the LLM back ends this project supports.

The pipeline needs exactly two things from a model: turn a prompt into a JSON
object, and turn a PDF into JSON rows. Everything provider-specific — SDK
imports, JSON-mode switches, how a document is attached to a request — lives
behind those two methods so the rest of the codebase never branches on which
vendor is in use.

Selecting a provider, in order of precedence:

  1. an explicit argument (``--provider`` on a CLI, the request field in the
     web API);
  2. the ``LLM_PROVIDER`` environment variable;
  3. ``app.llm_provider`` in config.yml;
  4. ``openai``.

Provider SDKs are imported lazily inside each implementation. Installing
`anthropic` is not a precondition for running the Gemini path, and a missing
package produces an actionable message rather than an ImportError at startup.
"""

from __future__ import annotations

import base64
import json
import os
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv()

# Anthropic caps a base64 document at 32MB; the Gemini inline-data path is
# limited to a ~20MB total request. Staying under the smaller of the two keeps
# one number to reason about for inline PDF uploads.
INLINE_PDF_LIMIT_BYTES = 18 * 1024 * 1024

# Generous by default: a parsed 인원배정 PDF can be several hundred JSON rows,
# and a truncated response is a hard failure rather than a degraded one.
DEFAULT_MAX_OUTPUT_TOKENS = 32000

#: How many PDF pages to send per extraction request. The 인원배정 tables run
#: ~35 firms per page, so a whole 28-page document would need far more output
#: tokens than any model will emit in one response. Callers split the document
#: into chunks of this many pages instead.
PDF_PAGES_PER_CHUNK = int(os.getenv("PDF_PAGES_PER_CHUNK", "6"))


class LLMError(RuntimeError):
    """Raised for any provider failure the caller is expected to surface."""


@dataclass(frozen=True)
class ProviderSpec:
    """Static facts about a provider: how to authenticate and what to run."""

    id: str
    label: str
    key_envs: tuple[str, ...]
    default_model: str
    default_parser_model: str
    install_hint: str
    supports_native_pdf: bool
    notes: str = ""

    @property
    def model_env(self) -> str:
        return f"{self.id.upper()}_MODEL"

    @property
    def parser_model_env(self) -> str:
        return f"{self.id.upper()}_PARSER_MODEL"

    def api_key(self) -> Optional[str]:
        for env in self.key_envs:
            value = os.getenv(env)
            if value:
                return value
        return None

    def is_configured(self) -> bool:
        return self.api_key() is not None


SPECS: dict[str, ProviderSpec] = {
    "openai": ProviderSpec(
        id="openai",
        label="OpenAI",
        key_envs=("OPENAI_API_KEY",),
        default_model="gpt-5",
        default_parser_model="gpt-5-mini",
        install_hint="pip install openai",
        supports_native_pdf=False,
        notes="PDFs are read with pdfplumber and sent as text.",
    ),
    "claude": ProviderSpec(
        id="claude",
        label="Claude (Anthropic)",
        key_envs=("ANTHROPIC_API_KEY", "CLAUDE_API_KEY"),
        default_model="claude-opus-5",
        default_parser_model="claude-opus-5",
        install_hint="pip install anthropic",
        supports_native_pdf=True,
        notes="PDFs are sent natively; Claude reads the page images and text.",
    ),
    "gemini": ProviderSpec(
        id="gemini",
        label="Google Gemini",
        key_envs=("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        # flash-lite by default: the free tier allows only 20 requests/day on
        # gemini-3.5-flash, which a run over a few hundred firms exhausts
        # immediately. Set GEMINI_MODEL=gemini-3.5-flash for finer judgement on
        # ambiguous firms.
        default_model="gemini-3.1-flash-lite",
        default_parser_model="gemini-3.1-flash-lite",
        install_hint="pip install google-genai",
        supports_native_pdf=True,
        notes="PDFs are sent natively as inline document data.",
    ),
    # GitHub Models speaks the OpenAI wire format and was the original back end
    # for this project. Kept so existing GITHUB_TOKEN setups keep working.
    "github": ProviderSpec(
        id="github",
        label="GitHub Models (OpenAI-compatible)",
        key_envs=("GITHUB_TOKEN",),
        default_model="gpt-4o",
        default_parser_model="gpt-4o",
        install_hint="pip install openai",
        supports_native_pdf=False,
        notes="Uses OPENAI_BASE_URL; PDFs are read with pdfplumber.",
    ),
}

PROVIDER_IDS = tuple(SPECS)
DEFAULT_PROVIDER_ID = "openai"


def resolve_provider_id(
    explicit: Optional[str] = None,
    config: Optional[dict] = None,
) -> str:
    """Pick the provider id to use, following the documented precedence."""
    candidates = [
        explicit,
        os.getenv("LLM_PROVIDER"),
        (config or {}).get("app", {}).get("llm_provider"),
        DEFAULT_PROVIDER_ID,
    ]
    for candidate in candidates:
        if not candidate:
            continue
        name = str(candidate).strip().lower()
        # Accept the vendor names people actually type.
        name = {"anthropic": "claude", "google": "gemini", "openai-compatible": "github"}.get(name, name)
        if name in SPECS:
            return name
        if candidate is explicit and explicit:
            raise LLMError(
                f"Unknown LLM provider {explicit!r}. Choose one of: {', '.join(PROVIDER_IDS)}."
            )
    return DEFAULT_PROVIDER_ID


def _resolve_model(
    spec: ProviderSpec,
    explicit: Optional[str],
    config: Optional[dict],
    purpose: str,
) -> str:
    """Model precedence: argument, purpose-specific env, env, config, default."""
    app = (config or {}).get("app", {}) or {}
    configured = (app.get("llm_models") or {}).get(spec.id)
    if purpose == "parser":
        return (
            explicit
            or os.getenv(spec.parser_model_env)
            or configured
            or spec.default_parser_model
        )
    return explicit or os.getenv(spec.model_env) or configured or spec.default_model


def extract_json(text: str) -> Any:
    """Parse JSON out of a model response, tolerating chatty wrappers.

    Providers differ in how literally they honour "return only JSON": some wrap
    the payload in a ```json fence, some add a sentence before it. Rather than
    tightening the prompt per provider, we normalise here.
    """
    if text is None:
        raise LLMError("Model returned no content.")

    cleaned = text.strip()
    if not cleaned:
        raise LLMError("Model returned an empty response.")

    fenced = re.search(r"```(?:json)?\s*(.+?)\s*```", cleaned, re.DOTALL)
    if fenced:
        cleaned = fenced.group(1).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Decode the first complete JSON value and ignore whatever follows. This is
    # what rescues the common "correct object plus one stray closing brace"
    # response, which a whole-string parse rejects outright.
    decoder = json.JSONDecoder()
    starts = [pos for pos in (cleaned.find("{"), cleaned.find("[")) if pos != -1]
    for start in sorted(starts):
        try:
            value, _ = decoder.raw_decode(cleaned[start:])
            return value
        except json.JSONDecodeError:
            continue

    # Last resort: the outermost {...} or [...] span.
    for opener, closer in (("{", "}"), ("[", "]")):
        start = cleaned.find(opener)
        end = cleaned.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                continue

    preview = cleaned[:300].replace("\n", " ")
    raise LLMError(f"Could not parse JSON from model response: {preview}")


def _read_pdf_text(pdf_path: str) -> str:
    """Extract a PDF's text layer, for providers without document input."""
    import pdfplumber

    chunks = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                chunks.append(extracted)

    text = "\n".join(chunks)
    if not text.strip():
        raise LLMError(
            f"No extractable text in {os.path.basename(pdf_path)}. "
            "This looks like a scanned PDF — use the claude or gemini provider, "
            "which read the page images directly."
        )
    return text


def pdf_page_count(pdf_path: str) -> int:
    """Page count, used to decide whether one request can cover the document."""
    import pdfplumber

    with pdfplumber.open(pdf_path) as pdf:
        return len(pdf.pages)


def split_pdf(pdf_path: str, pages_per_chunk: int, out_dir: str) -> list[str]:
    """Split a PDF into page-range chunks and return the chunk paths.

    Splitting the document itself (rather than the extracted text) keeps one
    code path for both kinds of provider: the native-document providers get a
    real, smaller PDF, and the text providers extract from it as usual. Scanned
    documents therefore chunk just as well as digital ones.
    """
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(pdf_path)
    total = len(reader.pages)
    stem = Path(pdf_path).stem
    chunks: list[str] = []

    for start in range(0, total, pages_per_chunk):
        end = min(start + pages_per_chunk, total)
        writer = PdfWriter()
        for index in range(start, end):
            writer.add_page(reader.pages[index])

        chunk_path = Path(out_dir) / f"{stem}_p{start + 1}-{end}.pdf"
        with open(chunk_path, "wb") as handle:
            writer.write(handle)
        chunks.append(str(chunk_path))

    return chunks


def _check_pdf(pdf_path: str) -> Path:
    path = Path(pdf_path)
    if not path.is_file():
        raise LLMError(f"PDF not found: {pdf_path}")
    size = path.stat().st_size
    if size > INLINE_PDF_LIMIT_BYTES:
        raise LLMError(
            f"{path.name} is {size / 1024 / 1024:.1f}MB, above the "
            f"{INLINE_PDF_LIMIT_BYTES // 1024 // 1024}MB inline upload limit."
        )
    return path


class LLMProvider(ABC):
    """A back end that can answer with JSON and read a PDF."""

    def __init__(self, spec: ProviderSpec, model: str, parser_model: str):
        self.spec = spec
        self.model = model
        self.parser_model = parser_model
        # Built once per provider instance. Some SDK clients own an HTTP
        # session that closes when the object is collected, so a client created
        # inline for a single call can be torn down mid-request.
        self._client_cache: Any = None

    @property
    def id(self) -> str:
        return self.spec.id

    @property
    def label(self) -> str:
        return self.spec.label

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{type(self).__name__} model={self.model!r}>"

    def api_key(self) -> str:
        key = self.spec.api_key()
        if not key:
            envs = " or ".join(self.spec.key_envs)
            raise LLMError(
                f"{self.spec.label} is selected but {envs} is not set. "
                "Add it to your .env file (see .env.example)."
            )
        return key

    @abstractmethod
    def complete_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    ) -> Any:
        """Run one prompt and return its parsed JSON response."""

    @abstractmethod
    def pdf_to_json(
        self,
        pdf_path: str,
        prompt: str,
        max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    ) -> Any:
        """Run one prompt against a PDF and return the parsed JSON response."""


class _OpenAICompatibleProvider(LLMProvider):
    """OpenAI and any endpoint that speaks the same Chat Completions API."""

    #: GitHub Models needs a base_url; the OpenAI provider must not inherit one.
    use_base_url = False

    def _client(self):
        if self._client_cache is None:
            from openai import OpenAI

            kwargs: dict[str, Any] = {"api_key": self.api_key()}
            if self.use_base_url:
                kwargs["base_url"] = os.getenv(
                    "OPENAI_BASE_URL", "https://models.github.ai/inference"
                )
            self._client_cache = OpenAI(**kwargs)
        return self._client_cache

    def _chat(self, model: str, system: Optional[str], prompt: str) -> str:
        # No temperature: the gpt-5 family only accepts the default and rejects
        # the request otherwise. These prompts are extraction and
        # classification, so sampling control buys nothing here anyway.
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = retry_transient(
                lambda: self._client().chat.completions.create(
                    model=model,
                    messages=messages,
                    response_format={"type": "json_object"},
                )
            )
        except LLMError:
            raise
        except Exception as exc:
            raise LLMError(f"{self.label} request failed: {exc}") from exc

        if not response.choices:
            raise LLMError(f"{self.label} returned no choices.")

        choice = response.choices[0]
        if choice.finish_reason == "length":
            raise LLMError(
                f"{self.label} hit its output limit before finishing. Reduce "
                "PDF_PAGES_PER_CHUNK or process fewer rows per request."
            )
        return choice.message.content or ""

    def complete_json(self, prompt, system=None, max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS):
        return extract_json(self._chat(self.model, system, prompt))

    def pdf_to_json(self, pdf_path, prompt, max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS):
        _check_pdf(pdf_path)
        text = _read_pdf_text(pdf_path)
        return extract_json(
            self._chat(
                self.parser_model,
                "You are a data extraction assistant. Reply with JSON only.",
                f"{prompt}\n\nDocument Text:\n{text}",
            )
        )


class OpenAIProvider(_OpenAICompatibleProvider):
    use_base_url = False


class GitHubModelsProvider(_OpenAICompatibleProvider):
    use_base_url = True


class ClaudeProvider(LLMProvider):
    """Anthropic's Messages API, including native PDF input."""

    def _client(self):
        if self._client_cache is None:
            try:
                import anthropic
            except ImportError as exc:  # pragma: no cover - depends on env
                raise LLMError(
                    f"The anthropic package is required for the Claude provider "
                    f"({self.spec.install_hint})."
                ) from exc
            self._client_cache = anthropic.Anthropic(api_key=self.api_key())
        return self._client_cache

    def _message(self, model: str, system: str, content: Any, max_output_tokens: int) -> str:
        # Streaming on every call: max_tokens here is high enough that a
        # non-streaming request risks an SDK HTTP timeout, and on thinking
        # models the wait before first output is long.
        def run():
            with self._client().messages.stream(
                model=model,
                max_tokens=max_output_tokens,
                system=system,
                messages=[{"role": "user", "content": content}],
            ) as stream:
                return stream.get_final_message()

        try:
            message = retry_transient(run)
        except LLMError:
            raise
        except Exception as exc:
            raise LLMError(f"{self.label} request failed: {exc}") from exc

        if message.stop_reason == "refusal":
            raise LLMError(
                f"{self.label} declined this request (stop_reason=refusal)."
            )
        if message.stop_reason == "max_tokens":
            raise LLMError(
                f"{self.label} hit the {max_output_tokens}-token output cap before "
                "finishing. Reduce PDF_PAGES_PER_CHUNK, or raise the limit."
            )

        # Thinking blocks come back alongside text and carry no content by
        # default, so take the text blocks only.
        return "".join(
            block.text for block in message.content if getattr(block, "type", None) == "text"
        )

    def complete_json(self, prompt, system=None, max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS):
        instruction = system or "You are a precise analyst."
        return extract_json(
            self._message(
                self.model,
                f"{instruction}\n\nAlways reply with a single valid JSON object and nothing else.",
                prompt,
                max_output_tokens,
            )
        )

    def pdf_to_json(self, pdf_path, prompt, max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS):
        path = _check_pdf(pdf_path)
        encoded = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
        content = [
            {
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": encoded,
                },
            },
            {"type": "text", "text": prompt},
        ]
        return extract_json(
            self._message(
                self.parser_model,
                "You are a data extraction assistant. Reply with JSON only.",
                content,
                max_output_tokens,
            )
        )


class GeminiProvider(LLMProvider):
    """Google Gemini via google-genai, falling back to the legacy SDK."""

    def _new_client(self):
        if self._client_cache is None:
            from google import genai

            self._client_cache = genai.Client(api_key=self.api_key())
        return self._client_cache

    def _generate(
        self,
        model: str,
        system: Optional[str],
        parts: list,
        max_output_tokens: int,
    ) -> str:
        try:
            from google import genai  # noqa: F401
            from google.genai import types
        except ImportError:
            return self._generate_legacy(model, system, parts, max_output_tokens)

        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            max_output_tokens=max_output_tokens,
        )
        try:
            response = retry_transient(
                lambda: self._new_client().models.generate_content(
                    model=model, contents=parts, config=config
                )
            )
        except LLMError:
            raise
        except Exception as exc:
            raise LLMError(f"{self.label} request failed: {exc}") from exc

        # Gemini returns a truncated-but-valid-looking body on MAX_TOKENS, so
        # without this check the failure surfaces later as a JSON parse error.
        candidates = response.candidates or []
        if candidates:
            reason = getattr(candidates[0].finish_reason, "name", str(candidates[0].finish_reason or ""))
            if reason == "MAX_TOKENS":
                usage = response.usage_metadata
                thoughts = getattr(usage, "thoughts_token_count", None) or 0
                raise LLMError(
                    f"{self.label} hit the {max_output_tokens}-token output limit "
                    f"before finishing (thinking used {thoughts} of them). Reduce "
                    "PDF_PAGES_PER_CHUNK, or raise the limit."
                )
            if reason in {"SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII", "RECITATION"}:
                raise LLMError(f"{self.label} blocked this request ({reason}).")

        return response.text or ""

    def _generate_legacy(self, model, system, parts, max_output_tokens) -> str:
        """Path for environments still on google-generativeai."""
        try:
            import google.generativeai as genai
        except ImportError as exc:  # pragma: no cover - depends on env
            raise LLMError(
                f"A Google GenAI SDK is required for the Gemini provider "
                f"({self.spec.install_hint})."
            ) from exc

        genai.configure(api_key=self.api_key())
        legacy_parts = []
        for part in parts:
            if isinstance(part, str):
                legacy_parts.append(part)
            elif isinstance(part, dict) and "inline_data" in part:
                legacy_parts.append(part["inline_data"])
            else:  # A types.Part from the new SDK cannot cross over.
                raise LLMError(
                    "Native PDF input needs google-genai; install it with "
                    f"`{self.spec.install_hint}`."
                )

        try:
            client = genai.GenerativeModel(
                model_name=model, system_instruction=system
            )
            response = retry_transient(
                lambda: client.generate_content(
                    legacy_parts,
                    generation_config={
                        "response_mime_type": "application/json",
                        "max_output_tokens": max_output_tokens,
                    },
                )
            )
        except LLMError:
            raise
        except Exception as exc:
            raise LLMError(f"{self.label} request failed: {exc}") from exc

        return response.text or ""

    def complete_json(self, prompt, system=None, max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS):
        return extract_json(self._generate(self.model, system, [prompt], max_output_tokens))

    def pdf_to_json(self, pdf_path, prompt, max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS):
        path = _check_pdf(pdf_path)
        try:
            from google.genai import types
        except ImportError as exc:  # pragma: no cover - depends on env
            raise LLMError(
                f"Native PDF input needs google-genai ({self.spec.install_hint})."
            ) from exc

        document = types.Part.from_bytes(
            data=path.read_bytes(), mime_type="application/pdf"
        )
        return extract_json(
            self._generate(
                self.parser_model,
                "You are a data extraction assistant. Reply with JSON only.",
                [document, prompt],
                max_output_tokens,
            )
        )


IMPLEMENTATIONS: dict[str, type[LLMProvider]] = {
    "openai": OpenAIProvider,
    "claude": ClaudeProvider,
    "gemini": GeminiProvider,
    "github": GitHubModelsProvider,
}


def get_provider(
    provider: Optional[str] = None,
    config: Optional[dict] = None,
    model: Optional[str] = None,
    parser_model: Optional[str] = None,
) -> LLMProvider:
    """Build the selected provider, without contacting it."""
    provider_id = resolve_provider_id(provider, config)
    spec = SPECS[provider_id]
    return IMPLEMENTATIONS[provider_id](
        spec,
        model=_resolve_model(spec, model, config, "chat"),
        parser_model=_resolve_model(spec, parser_model, config, "parser"),
    )


def describe_providers(config: Optional[dict] = None) -> list[dict]:
    """Report every provider and whether it is usable right now.

    Drives the provider picker in the UI, so the user can see at a glance which
    keys are present instead of finding out on the first failed run.
    """
    active = resolve_provider_id(None, config)
    described = []
    for spec in SPECS.values():
        described.append(
            {
                "id": spec.id,
                "label": spec.label,
                "configured": spec.is_configured(),
                "active": spec.id == active,
                "model": _resolve_model(spec, None, config, "chat"),
                "parser_model": _resolve_model(spec, None, config, "parser"),
                "key_env": spec.key_envs[0],
                "supports_native_pdf": spec.supports_native_pdf,
                "notes": spec.notes,
            }
        )
    return described


#: Retried: the provider is momentarily busy and the same request may succeed.
TRANSIENT_PATTERNS = (
    "rate limit",
    "429",
    "resource_exhausted",
    "overloaded",
    "503",
    "unavailable",
    "high demand",
    "500",
    "internal error",
    "timeout",
    "timed out",
)

#: Not retried: retrying cannot fix a spent quota or a rejected key, and the
#: delay only postpones a message the user needs to see.
PERMANENT_PATTERNS = (
    "insufficient_quota",
    "exceeded your current quota",
    "invalid_api_key",
    "incorrect api key",
    "authentication",
    "permission",
    "retirement",
)


def retry_transient(fn, attempts: int = 3, base_delay: float = 2.0):
    """Retry a provider call through momentary unavailability.

    Matching is on the message rather than on SDK exception classes: the three
    SDKs raise unrelated hierarchies for the same conditions, and a busy Gemini
    endpoint (503 "high demand") is as retryable as an OpenAI 429.
    """
    last: Optional[Exception] = None
    for attempt in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - re-raised below
            message = str(exc).lower()
            if any(pattern in message for pattern in PERMANENT_PATTERNS):
                raise
            if not any(pattern in message for pattern in TRANSIENT_PATTERNS):
                raise
            last = exc
            if attempt < attempts - 1:
                delay = base_delay * (2**attempt)
                print(f"  (transient provider error, retrying in {delay:.0f}s)")
                time.sleep(delay)
    raise LLMError(f"Provider still unavailable after {attempts} attempts: {last}")
