# md2email

Convert Markdown to email-safe HTML with inline styles.

Email clients strip `<style>` blocks, so every element needs inline CSS. This tool does that automatically.

**Pure Python, zero dependencies.**

## Usage

```bash
# Convert file
python3 md2email.py input.md -o email.html

# Preview in browser
python3 md2email.py input.md --preview

# Read from stdin
echo "# Hello **world**" | python3 md2email.py -

# Dark theme
python3 md2email.py input.md --theme dark

# Body HTML only (for embedding)
python3 md2email.py input.md --body-only
```

## Supported Markdown

- **Headers** (h1-h6) with styled borders
- **Bold**, *italic*, ~~strikethrough~~, ***bold italic***
- `inline code` and fenced code blocks
- [Links](https://example.com) and images
- Ordered and unordered lists
- Tables with header styling
- Blockquotes
- Horizontal rules

## Themes

- `light` (default) — clean, professional
- `dark` — dark background, light text

## Renders In

Gmail, Outlook, Apple Mail, Yahoo Mail, Thunderbird — tested with all inline styles.

## License

MIT
