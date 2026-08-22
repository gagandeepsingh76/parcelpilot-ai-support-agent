import { ReactNode } from "react";

/*
 * Minimal markdown renderer for assistant messages.
 * Supports: **bold**, *italic*, `inline code`, fenced code blocks,
 * unordered/ordered lists, ###-headings, paragraphs.
 * Builds React nodes directly - no HTML injection surface.
 */

function renderInline(text: string, keyBase: string): ReactNode[] {
  const out: ReactNode[] = [];
  const pattern = /(\*\*([^*]+)\*\*)|(`([^`]+)`)|(\*([^*\n]+)\*)/g;
  let last = 0;
  let match: RegExpExecArray | null;
  let n = 0;
  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last) out.push(text.slice(last, match.index));
    const k = `${keyBase}-i${n++}`;
    if (match[2] !== undefined) {
      out.push(<strong key={k}>{match[2]}</strong>);
    } else if (match[4] !== undefined) {
      out.push(<code key={k}>{match[4]}</code>);
    } else if (match[6] !== undefined) {
      out.push(<em key={k}>{match[6]}</em>);
    }
    last = match.index + match[0].length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export default function Markdown({ text }: { text: string }) {
  const lines = text.replace(/\r\n/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let para: string[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;
  let code: { lang: string; lines: string[] } | null = null;
  let bn = 0;

  const flushPara = () => {
    if (para.length === 0) return;
    const joined = para.join("\n");
    blocks.push(<p key={`p${bn++}`}>{renderInline(joined, `p${bn}`)}</p>);
    para = [];
  };

  const flushList = () => {
    if (!list) return;
    const items = list.items.map((item, i) => (
      <li key={i}>{renderInline(item, `li${bn}-${i}`)}</li>
    ));
    blocks.push(
      list.ordered ? <ol key={`l${bn++}`}>{items}</ol> : <ul key={`l${bn++}`}>{items}</ul>,
    );
    list = null;
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (line.trimStart().startsWith("```")) {
      if (code) {
        blocks.push(
          <pre key={`c${bn++}`}>
            <code>{code.lines.join("\n")}</code>
          </pre>,
        );
        code = null;
      } else {
        flushPara();
        flushList();
        code = { lang: line.trim().slice(3), lines: [] };
      }
      continue;
    }
    if (code) {
      code.lines.push(line);
      continue;
    }

    const heading = line.match(/^(#{1,4})\s+(.*)$/);
    if (heading) {
      flushPara();
      flushList();
      blocks.push(<strong key={`h${bn++}`}>{renderInline(heading[2], `h${bn}`)}</strong>);
      continue;
    }

    const unordered = line.match(/^\s*[-*]\s+(.*)$/);
    const ordered = line.match(/^\s*(\d+)[.)]\s+(.*)$/);
    if (unordered || ordered) {
      flushPara();
      const orderedList = Boolean(ordered);
      if (!list || list.ordered !== orderedList) {
        flushList();
        list = { ordered: orderedList, items: [] };
      }
      list.items.push((unordered ? unordered[1] : ordered![2]).trim());
      continue;
    }

    if (line.trim() === "") {
      flushPara();
      flushList();
      continue;
    }

    if (list) {
      // continuation line of a list item
      list.items[list.items.length - 1] += ` ${line.trim()}`;
      continue;
    }
    para.push(line);
  }

  if (code) {
    blocks.push(
      <pre key={`c${bn++}`}>
        <code>{code.lines.join("\n")}</code>
      </pre>,
    );
  }
  flushPara();
  flushList();

  return <div className="md">{blocks}</div>;
}
