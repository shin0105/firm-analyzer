#!/usr/bin/env python3
"""Live connectivity check for every configured LLM provider.

Not a unit test — it spends real API calls, so it is named out of pytest's
collection pattern and must be run by hand:

    python tests/live_provider_check.py            # every configured provider
    python tests/live_provider_check.py gemini     # just one

Each provider gets one tiny JSON round trip. Providers without a key are
reported as skipped rather than failed.
"""

import json
import os
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

load_dotenv()

from firm_analyzer.llm import (  # noqa: E402
    PROVIDER_IDS,
    LLMError,
    describe_providers,
    get_provider,
)

PROMPT = (
    'Reply with exactly this JSON and nothing else: '
    '{"ok": true, "model_family": "<your model family>"}'
)


def main() -> int:
    requested = sys.argv[1:] or list(PROVIDER_IDS)
    unknown = [name for name in requested if name not in PROVIDER_IDS]
    if unknown:
        print(f"Unknown provider(s): {', '.join(unknown)}")
        print(f"Choose from: {', '.join(PROVIDER_IDS)}")
        return 2

    status = {row["id"]: row for row in describe_providers()}
    failures = 0

    for provider_id in requested:
        row = status[provider_id]
        print(f"\n=== {row['label']} ({provider_id}) ===")
        if not row["configured"]:
            print(f"  SKIP — {row['key_env']} is not set")
            continue

        try:
            provider = get_provider(provider_id)
            answer = provider.complete_json(
                PROMPT, system="You answer in JSON.", max_output_tokens=2000
            )
            print(f"  OK — {provider.model}: {json.dumps(answer, ensure_ascii=False)[:160]}")
        except LLMError as exc:
            failures += 1
            print(f"  FAIL — {exc}")

    print()
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
