import { Fragment, type ReactNode } from 'react';
import Highlight from './Highlight';

/**
 * Minimal Markdown renderer for the summaries the backend writes as
 * `summary.md`. It builds React elements directly — never `innerHTML` — so
 * model-generated summary text cannot inject markup.
 *
 * Supported: ATX headings, `-`/`*`/`1.` lists, `---` rules, blockquotes,
 * pipe tables, fenced and inline code, bold, italic and links. `highlight`
 * marks a search term wherever it appears in the text.
 */

type Inline = { text: string; key: number };

const INLINE_PATTERN =
  /(\*\*[^*]+\*\*|__[^_]+__|\*[^*\n]+\*|_[^_\n]+_|`[^`]+`|\[[^\]]+\]\([^)\s]+\))/g;

/** Only allow link targets that are safe to hand to the browser. */
function safeHref(href: string): string | null {
  const trimmed = href.trim();
  return /^(https?:\/\/|mailto:)/i.test(trimmed) ? trimmed : null;
}

/** Plain text, with the search term `term` (if any) in highlighter. */
function plain(text: string, key: string, term: string): ReactNode {
  return term ? <Highlight key={key} text={text} term={term} /> : text;
}

function renderInline(text: string, keyPrefix: string, term: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let lastIndex = 0;
  let key = 0;

  for (const match of text.matchAll(INLINE_PATTERN)) {
    const token = match[0];
    const start = match.index ?? 0;

    if (start > lastIndex) {
      nodes.push(plain(text.slice(lastIndex, start), `${keyPrefix}-t${key}`, term));
    }
    lastIndex = start + token.length;
    const k = `${keyPrefix}-${key++}`;

    if (token.startsWith('**') || token.startsWith('__')) {
      nodes.push(<strong key={k}>{plain(token.slice(2, -2), `${k}-t`, term)}</strong>);
    } else if (token.startsWith('`')) {
      nodes.push(<code key={k}>{token.slice(1, -1)}</code>);
    } else if (token.startsWith('[')) {
      const split = token.indexOf('](');
      const label = token.slice(1, split);
      const href = safeHref(token.slice(split + 2, -1));
      nodes.push(
        href ? (
          <a key={k} href={href} target="_blank" rel="noopener noreferrer">
            {plain(label, `${k}-t`, term)}
          </a>
        ) : (
          <Fragment key={k}>{plain(label, `${k}-t`, term)}</Fragment>
        ),
      );
    } else {
      nodes.push(<em key={k}>{plain(token.slice(1, -1), `${k}-t`, term)}</em>);
    }
  }

  if (lastIndex < text.length) {
    nodes.push(plain(text.slice(lastIndex), `${keyPrefix}-t${key}`, term));
  }
  return nodes;
}

/** A `| a | b |` row, split into trimmed cells. */
function splitRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((cell) => cell.trim());
}

/** The `| --- | :---: |` line that turns the row above it into a table header. */
function isTableSeparator(line: string | undefined): boolean {
  // Requiring a pipe keeps a `---` rule under a `|` line from becoming a table.
  return line !== undefined && line.includes('|') && /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$/.test(line);
}

type Table = { header: string[]; rows: string[][] };

function renderTable(table: Table, key: string, term: string): ReactNode {
  const width = table.header.length;
  return (
    <div className="table-scroll" key={key}>
      <table>
        <thead>
          <tr>
            {table.header.map((cell, i) => (
              <th key={i} scope="col">
                {renderInline(cell, `${key}-h${i}`, term)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, r) => (
            <tr key={r}>
              {Array.from({ length: width }, (_, c) => (
                <td key={c}>{renderInline(row[c] ?? '', `${key}-${r}-${c}`, term)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function renderList(items: Inline[], ordered: boolean, key: string, term: string): ReactNode {
  const children = items.map((item) => (
    <li key={item.key}>{renderInline(item.text, `${key}-${item.key}`, term)}</li>
  ));
  return ordered ? <ol key={key}>{children}</ol> : <ul key={key}>{children}</ul>;
}

export default function Markdown({ content, highlight = '' }: { content: string; highlight?: string }) {
  const term = highlight.trim();
  const lines = content.replace(/\r\n/g, '\n').split('\n');
  const blocks: ReactNode[] = [];

  let listItems: Inline[] = [];
  let listOrdered = false;
  let paragraph: string[] = [];
  let codeLines: string[] | null = null;
  let inMarkdownFence = false;
  let table: Table | null = null;
  let separatorIndex = -1;

  const flushList = (index: number) => {
    if (listItems.length === 0) return;
    blocks.push(renderList(listItems, listOrdered, `list-${index}`, term));
    listItems = [];
  };

  const flushParagraph = (index: number) => {
    if (paragraph.length === 0) return;
    const text = paragraph.join(' ');
    blocks.push(<p key={`p-${index}`}>{renderInline(text, `p-${index}`, term)}</p>);
    paragraph = [];
  };

  const flushTable = (index: number) => {
    if (table === null) return;
    blocks.push(renderTable(table, `table-${index}`, term));
    table = null;
  };

  lines.forEach((rawLine, index) => {
    const line = rawLine.trimEnd();
    if (index === separatorIndex) return;

    // Table rows continue until the first line that is not a `|` row.
    if (table !== null) {
      if (line.trim().startsWith('|')) {
        table.rows.push(splitRow(line));
        return;
      }
      flushTable(index);
    }

    // Fenced code blocks are passed through verbatim, except a ```markdown
    // fence: some summaries come back wrapped in one, and their content is
    // the summary itself, so only the fence lines are dropped.
    const fence = /^\s*```\s*([\w-]*)/.exec(line);
    if (fence) {
      if (codeLines === null && inMarkdownFence && !fence[1]) {
        flushParagraph(index);
        flushList(index);
        inMarkdownFence = false;
      } else if (codeLines === null && /^(markdown|md)$/i.test(fence[1])) {
        flushParagraph(index);
        flushList(index);
        inMarkdownFence = true;
      } else if (codeLines === null) {
        flushParagraph(index);
        flushList(index);
        codeLines = [];
      } else {
        blocks.push(
          <pre key={`code-${index}`}>
            <code>{codeLines.join('\n')}</code>
          </pre>,
        );
        codeLines = null;
      }
      return;
    }
    if (codeLines !== null) {
      codeLines.push(rawLine);
      return;
    }

    if (line.trim() === '') {
      flushParagraph(index);
      flushList(index);
      return;
    }

    if (line.trim().startsWith('|') && isTableSeparator(lines[index + 1])) {
      flushParagraph(index);
      flushList(index);
      table = { header: splitRow(line), rows: [] };
      separatorIndex = index + 1;
      return;
    }

    const heading = /^(#{1,6})\s+(.*)$/.exec(line);
    if (heading) {
      flushParagraph(index);
      flushList(index);
      const level = Math.min(heading[1].length, 3);
      const Tag = `h${level}` as 'h1' | 'h2' | 'h3';
      blocks.push(<Tag key={`h-${index}`}>{renderInline(heading[2], `h-${index}`, term)}</Tag>);
      return;
    }

    if (/^\s*([-*_])\1{2,}\s*$/.test(line)) {
      flushParagraph(index);
      flushList(index);
      blocks.push(<hr key={`hr-${index}`} />);
      return;
    }

    const bullet = /^\s*[-*+]\s+(.*)$/.exec(line);
    const numbered = /^\s*\d+[.)]\s+(.*)$/.exec(line);
    if (bullet || numbered) {
      flushParagraph(index);
      const ordered = Boolean(numbered);
      if (listItems.length > 0 && ordered !== listOrdered) {
        flushList(index);
      }
      listOrdered = ordered;
      listItems.push({ text: (bullet ?? numbered)![1], key: index });
      return;
    }

    const quote = /^\s*>\s?(.*)$/.exec(line);
    if (quote) {
      flushParagraph(index);
      flushList(index);
      blocks.push(
        <blockquote key={`q-${index}`}>{renderInline(quote[1], `q-${index}`, term)}</blockquote>,
      );
      return;
    }

    flushList(index);
    paragraph.push(line.trim());
  });

  flushParagraph(lines.length);
  flushList(lines.length);
  flushTable(lines.length);
  // An unterminated fence still gets rendered rather than dropped. (TypeScript
  // cannot see the assignments made inside the loop's closure, hence the cast.)
  const trailingCode = codeLines as string[] | null;
  if (trailingCode && trailingCode.length > 0) {
    blocks.push(
      <pre key="code-tail">
        <code>{trailingCode.join('\n')}</code>
      </pre>,
    );
  }

  return <div className="markdown-body">{blocks}</div>;
}
