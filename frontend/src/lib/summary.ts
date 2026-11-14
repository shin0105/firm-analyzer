/**
 * How a `summary.md` is laid out for reading.
 *
 * The file starts with a header the pipeline writes: `# <firm name>`, then
 * `**Address:** …`-style fields, then the AI notice (see
 * `parse_summary_header` and `with_notice` in `core/results.py`). The viewer
 * already shows the name, the category badge and the notice banner, so the
 * header is turned into a short list of facts and the body is shown without
 * those repeats.
 */

/** Same line the backend writes: `NOTICE_MARKER` in `src/firm_analyzer/notice.py`. */
const NOTICE_MARKER = '> ⚠️ **AI 생성 콘텐츠**';
const HEADER_FIELD = /^\*\*([^*]+?):\*\*\s*(.*)$/;

const CONFIDENCE_LABEL: Record<string, string> = {
  high: '높음',
  medium: '보통',
  low: '낮음',
};

export interface SummaryFact {
  label: string;
  value: string;
  /** Set when the value is a web address safe to link to. */
  href?: string;
  note?: string;
}

export interface SummaryParts {
  facts: SummaryFact[];
  body: string;
}

/** The URL in `value`, written bare or as `[label](url)` (summarize writes the latter). */
function webHref(value: string): string | undefined {
  const trimmed = value.trim();
  const link = /^\[[^\]]*\]\((\S+)\)$/.exec(trimmed);
  const url = link ? link[1] : trimmed;
  return /^https?:\/\/\S+$/i.test(url) ? url : undefined;
}

function displayUrl(href: string): string {
  return href.replace(/^https?:\/\//i, '').replace(/\/$/, '');
}

function normalizeName(name: string): string {
  return name.replace(/\s+/g, '').toLowerCase();
}

export function splitSummary(markdown: string, firmName: string): SummaryParts {
  const lines = markdown.split(/\r?\n/);
  let i = 0;
  if (lines[0]?.startsWith('# ')) i = 1;
  while (i < lines.length && !lines[i].trim()) i += 1;

  const fields = new Map<string, string>();
  while (i < lines.length) {
    const match = HEADER_FIELD.exec(lines[i]);
    if (!match) break;
    fields.set(match[1].trim().toLowerCase(), match[2].trim());
    i += 1;
  }

  const rest = lines.slice(i).filter((line) => !line.startsWith(NOTICE_MARKER));
  while (rest.length && !rest[0].trim()) rest.shift();
  // Most bodies open by repeating the firm name as a heading.
  const heading = /^#{1,6}\s+(.*)$/.exec(rest[0] ?? '');
  if (heading && normalizeName(heading[1]) === normalizeName(firmName)) {
    rest.shift();
    while (rest.length && !rest[0].trim()) rest.shift();
  }

  const facts: SummaryFact[] = [];
  const address = fields.get('address');
  if (address) facts.push({ label: '주소', value: address });

  const webpage = fields.get('official webpage');
  const href = webpage ? webHref(webpage) : undefined;
  if (webpage && href) {
    const confidence = fields.get('webpage confidence')?.toLowerCase() ?? '';
    facts.push({
      label: '웹사이트',
      value: displayUrl(href),
      href,
      note: CONFIDENCE_LABEL[confidence] ? `AI 추정 · 확신도 ${CONFIDENCE_LABEL[confidence]}` : 'AI 추정',
    });
  }

  return { facts, body: rest.join('\n') };
}
