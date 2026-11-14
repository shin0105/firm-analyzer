"""The label every AI-generated firm summary carries.

Summaries are written by a language model from web search results. They can be
wrong, out of date, or about a different company with a similar name, and they
are never statements by the firms themselves. Everything that writes, shows or
exports a summary labels it with this notice, so the label travels with the
content wherever it is copied. The frontend shows the same wording in
frontend/src/components/AiNotice.tsx; keep the two in step.

This module has no imports so that any other module can use it.
"""

AI_NOTICE_KO = (
    "이 요약은 공개 웹 검색 결과를 바탕으로 AI가 자동 생성한 참고 자료입니다. "
    "사실과 다르거나 오래된 정보, 동명의 다른 기업 정보가 섞여 있을 수 있으며, "
    "해당 기업의 공식 입장이나 평가가 아닙니다. 지원·투자 등 중요한 결정 전에는 "
    "반드시 기업의 공식 채널에서 직접 확인하세요."
)

AI_NOTICE_EN = (
    "Generated automatically by AI from public web search results, for reference "
    "only. It may be inaccurate, outdated or mix up firms with similar names, and "
    "it is not a statement or assessment by the company. Verify with the "
    "company's official channels before relying on it."
)

#: Start of the notice line in summary.md; used to find (and skip) it.
NOTICE_MARKER = "> ⚠️ **AI 생성 콘텐츠**"
AI_NOTICE_MARKDOWN = f"{NOTICE_MARKER} — {AI_NOTICE_KO}"

#: Heading of the source list summarize appends to summary.md.
SOURCES_HEADING = "## 출처 (Sources)"

#: Value of the `notice` column in CSV exports, one per row so it survives
#: rows being copied out of the file.
EXPORT_NOTICE = "AI 생성·미검증 참고자료 (AI-generated / unverified)"

#: Rules added to every summary prompt, custom prompts included. They keep the
#: output to what the sources support, which is both more accurate and less
#: likely to say something unfair about a real company.
SUMMARY_GUARDRAILS = """\
Content rules (always apply):
- Use only facts stated in the search results. Do not guess, extrapolate or fill gaps from general knowledge. If something is unknown, say it is not found in the sources.
- Write neutrally and descriptively. Do not rate, rank, praise or criticise the firm.
- Do not include allegations, lawsuits, sanctions, labour disputes, financial distress or other negative claims unless a search result states them explicitly, and then attribute them to that source.
- If the results may describe a different organisation with a similar name, say so rather than merging them.
- Do not include personal information about individuals (phone numbers, personal emails, home addresses); public role titles are fine."""
