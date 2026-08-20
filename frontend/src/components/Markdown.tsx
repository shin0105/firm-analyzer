import { Fragment, type ReactNode } from 'react';

/**
 * Minimal Markdown renderer for the summaries the backend writes as
 * `summary.md`. It builds React elements directly — never `innerHTML` — so
 * model-generated summary text cannot inject markup.
 *
 * Supported: ATX headings, `-`/`*`/`1.` lists, `---` rules, blockquotes,
 * fenced and inline code, bold, italic and links.
 */

type Inline = { text: string; key: number };

const INLINE_PATTERN =
  /(\*\*[^*]+\*\*|__[^_]+__|\*[^*\n]+\*|_[^_\n]+_|`[^`]+`|\[[^\]]+\]\([^)\s]+\))/g;

/** Only allow link targets that are safe to hand to the browser. */
function safeHref(href: string): string | null {
  const trimmed = href.trim();
  return /^(https?:\/\/|mailto:)/i.test(trimmed) ? trimmed : null;
}

function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let lastIndex = 0;
  let key = 0;

  for (const match of text.matchAll(INLINE_PATTERN)) {
    const token = match[0];
    const start = match.index ?? 0;

    if (start > lastIndex) {
      nodes.push(text.slice(lastIndex, start));
    }
    lastIndex = start + token.length;
    const k = `${keyPrefix}-${key++}`;

    if (token.startsWith('**') || token.startsWith('__')) {
      nodes.push(<strong key={k}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith('`')) {
      nodes.push(<code key={k}>{token.slice(1, -1)}</code>);
    } else if (token.startsWith('[')) {
      const split = token.indexOf('](');
      const label = token.slice(1, split);
      const href = safeHref(token.slice(split + 2, -1));
      nodes.push(
        href ? (
          <a key={k} href={href} target="_blank" rel="noopener noreferrer">
            {label}
          </a>
        ) : (
          <Fragment key={k}>{label}</Fragment>
        ),
      );
    } else {
      nodes.push(<em key={k}>{token.slice(1, -1)}</em>);
    }
  }

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }
  return nodes;
}

function renderList(items: Inline[], ordered: boolean, key: string): ReactNode {
  const children = items.map((item) => (
    <li key={item.key}>{renderInline(item.text, `${key}-${item.key}`)}</li>
  ));
  return ordered ? <ol key={key}>{children}</ol> : <ul key={key}>{children}</ul>;
}

export default function Markdown({ content }: { content: string }) {
  const lines = content.replace(/\r\n/g, '\n').split('\n');
  const blocks: ReactNode[] = [];

  let listItems: Inline[] = [];
  let listOrdered = false;
  let paragraph: string[] = [];
  let codeLines: string[] | null = null;

  const flushList = (index: number) => {
    if (listItems.length === 0) return;
    blocks.push(renderList(listItems, listOrdered, `list-${index}`));
    listItems = [];
  };

  const flushParagraph = (index: number) => {
    if (paragraph.length === 0) return;
    const text = paragraph.join(' ');
    blocks.push(<p key={`p-${index}`}>{renderInline(text, `p-${index}`)}</p>);
    paragraph = [];
  };

  lines.forEach((rawLine, index) => {
    const line = rawLine.trimEnd();

    // Fenced code blocks are passed through verbatim.
    if (/^\s*```/.test(line)) {
      if (codeLines === null) {
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

    const heading = /^(#{1,6})\s+(.*)$/.exec(line);
    if (heading) {
      flushParagraph(index);
      flushList(index);
      const level = Math.min(heading[1].length, 3);
      const Tag = `h${level}` as 'h1' | 'h2' | 'h3';
      blocks.push(<Tag key={`h-${index}`}>{renderInline(heading[2], `h-${index}`)}</Tag>);
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
        <blockquote key={`q-${index}`}>{renderInline(quote[1], `q-${index}`)}</blockquote>,
      );
      return;
    }

    flushList(index);
    paragraph.push(line.trim());
  });

  flushParagraph(lines.length);
  flushList(lines.length);
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
