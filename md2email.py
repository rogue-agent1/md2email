#!/usr/bin/env python3
"""
md2email: Convert Markdown to clean, email-safe HTML.
Produces inline-styled HTML that renders correctly in Gmail, Outlook, Apple Mail, etc.
Pure Python, zero dependencies.

Usage:
    python3 md2email.py input.md                    # Output to stdout
    python3 md2email.py input.md -o output.html     # Output to file
    python3 md2email.py input.md --preview           # Open in browser
    echo "# Hello" | python3 md2email.py -           # Read from stdin
    python3 md2email.py input.md --theme dark        # Dark theme
"""

import argparse
import html
import os
import re
import sys
import tempfile
import webbrowser
from pathlib import Path

# Email-safe inline styles (no CSS classes — email clients strip <style> blocks)
THEMES = {
    "light": {
        "body": "font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; font-size: 16px; line-height: 1.6; color: #1a1a1a; max-width: 600px; margin: 0 auto; padding: 20px;",
        "h1": "font-size: 28px; font-weight: 700; color: #111; margin: 32px 0 16px 0; padding-bottom: 8px; border-bottom: 2px solid #e5e5e5;",
        "h2": "font-size: 22px; font-weight: 600; color: #222; margin: 28px 0 12px 0;",
        "h3": "font-size: 18px; font-weight: 600; color: #333; margin: 24px 0 8px 0;",
        "p": "margin: 0 0 16px 0;",
        "a": "color: #0066cc; text-decoration: underline;",
        "code": "font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace; font-size: 14px; background: #f4f4f4; padding: 2px 6px; border-radius: 3px;",
        "pre": "font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace; font-size: 13px; background: #f8f8f8; padding: 16px; border-radius: 6px; border: 1px solid #e0e0e0; overflow-x: auto; line-height: 1.4; margin: 0 0 16px 0;",
        "blockquote": "border-left: 4px solid #ddd; margin: 0 0 16px 0; padding: 8px 16px; color: #555; background: #fafafa;",
        "ul": "margin: 0 0 16px 0; padding-left: 24px;",
        "ol": "margin: 0 0 16px 0; padding-left: 24px;",
        "li": "margin: 0 0 4px 0;",
        "hr": "border: none; border-top: 1px solid #e5e5e5; margin: 24px 0;",
        "img": "max-width: 100%; height: auto; border-radius: 4px;",
        "table": "border-collapse: collapse; width: 100%; margin: 0 0 16px 0;",
        "th": "border: 1px solid #ddd; padding: 8px 12px; background: #f0f0f0; text-align: left; font-weight: 600;",
        "td": "border: 1px solid #ddd; padding: 8px 12px;",
        "strong": "font-weight: 700;",
        "em": "font-style: italic;",
    },
    "dark": {
        "body": "font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; font-size: 16px; line-height: 1.6; color: #e0e0e0; max-width: 600px; margin: 0 auto; padding: 20px; background: #1a1a2e;",
        "h1": "font-size: 28px; font-weight: 700; color: #fff; margin: 32px 0 16px 0; padding-bottom: 8px; border-bottom: 2px solid #333;",
        "h2": "font-size: 22px; font-weight: 600; color: #f0f0f0; margin: 28px 0 12px 0;",
        "h3": "font-size: 18px; font-weight: 600; color: #ddd; margin: 24px 0 8px 0;",
        "p": "margin: 0 0 16px 0;",
        "a": "color: #6db3f2; text-decoration: underline;",
        "code": "font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace; font-size: 14px; background: #2a2a3e; padding: 2px 6px; border-radius: 3px; color: #e0e0e0;",
        "pre": "font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace; font-size: 13px; background: #16213e; padding: 16px; border-radius: 6px; border: 1px solid #333; overflow-x: auto; line-height: 1.4; margin: 0 0 16px 0; color: #e0e0e0;",
        "blockquote": "border-left: 4px solid #444; margin: 0 0 16px 0; padding: 8px 16px; color: #aaa; background: #222;",
        "ul": "margin: 0 0 16px 0; padding-left: 24px;",
        "ol": "margin: 0 0 16px 0; padding-left: 24px;",
        "li": "margin: 0 0 4px 0;",
        "hr": "border: none; border-top: 1px solid #444; margin: 24px 0;",
        "img": "max-width: 100%; height: auto; border-radius: 4px;",
        "table": "border-collapse: collapse; width: 100%; margin: 0 0 16px 0;",
        "th": "border: 1px solid #444; padding: 8px 12px; background: #2a2a3e; text-align: left; font-weight: 600;",
        "td": "border: 1px solid #444; padding: 8px 12px;",
        "strong": "font-weight: 700;",
        "em": "font-style: italic;",
    },
}


def md_to_email_html(markdown: str, theme: str = "light") -> str:
    """Convert Markdown to email-safe HTML with inline styles."""
    styles = THEMES.get(theme, THEMES["light"])
    lines = markdown.split("\n")
    out = []
    in_code_block = False
    code_block_lines = []
    in_list = None  # 'ul' or 'ol'
    list_items = []
    in_table = False
    table_rows = []
    in_blockquote = False
    bq_lines = []

    def flush_list():
        nonlocal in_list, list_items
        if not list_items:
            return
        tag = in_list
        items_html = "".join(f'<li style="{styles["li"]}">{process_inline(item)}</li>' for item in list_items)
        out.append(f'<{tag} style="{styles[tag]}">{items_html}</{tag}>')
        list_items = []
        in_list = None

    def flush_blockquote():
        nonlocal in_blockquote, bq_lines
        if not bq_lines:
            return
        content = "<br>".join(process_inline(l) for l in bq_lines)
        out.append(f'<blockquote style="{styles["blockquote"]}">{content}</blockquote>')
        bq_lines = []
        in_blockquote = False

    def flush_table():
        nonlocal in_table, table_rows
        if not table_rows:
            return
        html_rows = []
        for i, row in enumerate(table_rows):
            cells = [c.strip() for c in row.split("|")[1:-1]]
            if i == 0:
                cells_html = "".join(f'<th style="{styles["th"]}">{process_inline(c)}</th>' for c in cells)
            elif i == 1 and all(set(c.strip()) <= set("-: ") for c in cells):
                table_rows  # skip separator
                continue
            else:
                cells_html = "".join(f'<td style="{styles["td"]}">{process_inline(c)}</td>' for c in cells)
            html_rows.append(f"<tr>{cells_html}</tr>")
        out.append(f'<table style="{styles["table"]}">{"".join(html_rows)}</table>')
        table_rows = []
        in_table = False

    def process_inline(text: str) -> str:
        """Process inline Markdown: bold, italic, code, links, images."""
        # Escape HTML first (but preserve already-processed HTML)
        # Images: ![alt](url)
        text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)',
                       lambda m: f'<img src="{html.escape(m.group(2))}" alt="{html.escape(m.group(1))}" style="{styles["img"]}">', text)
        # Links: [text](url)
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)',
                       lambda m: f'<a href="{html.escape(m.group(2))}" style="{styles["a"]}">{m.group(1)}</a>', text)
        # Bold+italic: ***text***
        text = re.sub(r'\*\*\*(.+?)\*\*\*',
                       lambda m: f'<strong style="{styles["strong"]}"><em style="{styles["em"]}">{m.group(1)}</em></strong>', text)
        # Bold: **text**
        text = re.sub(r'\*\*(.+?)\*\*',
                       lambda m: f'<strong style="{styles["strong"]}">{m.group(1)}</strong>', text)
        # Italic: *text*
        text = re.sub(r'\*(.+?)\*',
                       lambda m: f'<em style="{styles["em"]}">{m.group(1)}</em>', text)
        # Inline code: `text`
        text = re.sub(r'`([^`]+)`',
                       lambda m: f'<code style="{styles["code"]}">{html.escape(m.group(1))}</code>', text)
        # Strikethrough: ~~text~~
        text = re.sub(r'~~(.+?)~~', r'<del>\1</del>', text)
        return text

    i = 0
    while i < len(lines):
        line = lines[i]

        # Code blocks
        if line.strip().startswith("```"):
            if in_code_block:
                code_content = html.escape("\n".join(code_block_lines))
                out.append(f'<pre style="{styles["pre"]}"><code>{code_content}</code></pre>')
                code_block_lines = []
                in_code_block = False
            else:
                flush_list()
                flush_blockquote()
                flush_table()
                in_code_block = True
            i += 1
            continue

        if in_code_block:
            code_block_lines.append(line)
            i += 1
            continue

        # Table rows
        if "|" in line and line.strip().startswith("|"):
            if not in_table:
                flush_list()
                flush_blockquote()
                in_table = True
            table_rows.append(line)
            i += 1
            continue
        elif in_table:
            flush_table()

        # Blockquote
        if line.strip().startswith("> "):
            if not in_blockquote:
                flush_list()
                in_blockquote = True
            bq_lines.append(line.strip()[2:])
            i += 1
            continue
        elif in_blockquote:
            flush_blockquote()

        # Headings
        m = re.match(r'^(#{1,6})\s+(.+)$', line)
        if m:
            flush_list()
            level = len(m.group(1))
            tag = f"h{level}"
            style = styles.get(tag, styles.get("h3", ""))
            text = process_inline(m.group(2))
            out.append(f'<{tag} style="{style}">{text}</{tag}>')
            i += 1
            continue

        # Horizontal rule
        if re.match(r'^[-*_]{3,}\s*$', line.strip()):
            flush_list()
            out.append(f'<hr style="{styles["hr"]}">')
            i += 1
            continue

        # Unordered list
        m = re.match(r'^[\s]*[-*+]\s+(.+)$', line)
        if m:
            if in_list == "ol":
                flush_list()
            in_list = "ul"
            list_items.append(m.group(1))
            i += 1
            continue

        # Ordered list
        m = re.match(r'^[\s]*\d+[.)]\s+(.+)$', line)
        if m:
            if in_list == "ul":
                flush_list()
            in_list = "ol"
            list_items.append(m.group(1))
            i += 1
            continue

        if in_list:
            flush_list()

        # Empty line
        if not line.strip():
            i += 1
            continue

        # Paragraph
        out.append(f'<p style="{styles["p"]}">{process_inline(line)}</p>')
        i += 1

    # Flush remaining
    flush_list()
    flush_blockquote()
    flush_table()
    if in_code_block and code_block_lines:
        code_content = html.escape("\n".join(code_block_lines))
        out.append(f'<pre style="{styles["pre"]}"><code>{code_content}</code></pre>')

    body = "\n".join(out)
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="{styles['body']}">
{body}
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(prog="md2email", description="Convert Markdown to email-safe HTML")
    parser.add_argument("input", help="Markdown file (or - for stdin)")
    parser.add_argument("-o", "--output", help="Output HTML file")
    parser.add_argument("--preview", action="store_true", help="Open in browser")
    parser.add_argument("--theme", choices=["light", "dark"], default="light")
    parser.add_argument("--body-only", action="store_true", help="Output body HTML only (no wrapper)")
    args = parser.parse_args()

    if args.input == "-":
        md = sys.stdin.read()
    else:
        md = Path(args.input).read_text()

    result = md_to_email_html(md, args.theme)

    if args.body_only:
        # Extract just the body content
        m = re.search(r'<body[^>]*>(.*)</body>', result, re.DOTALL)
        if m:
            result = m.group(1).strip()

    if args.output:
        Path(args.output).write_text(result)
        print(f"✅ Written to {args.output}")
    elif args.preview:
        with tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w") as f:
            f.write(result)
            webbrowser.open(f"file://{f.name}")
            print(f"📧 Preview opened: {f.name}")
    else:
        print(result)


if __name__ == "__main__":
    main()
