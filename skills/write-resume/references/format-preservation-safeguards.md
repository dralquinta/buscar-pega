# Format Preservation Safeguards

Use this file when the user wants the original CV format, template, or visual layout preserved.

## Core Rule

When the document is format-locked, change the wording, not the template.

That means:

- edit a copy of the original file
- preserve the current layout and styling
- do not rebuild the resume in a fresh document
- fail closed if you cannot keep the format intact

## What Must Stay Unchanged

- page size and margins
- fonts, font sizes, bolding, colors, and typography hierarchy
- section order unless the user explicitly allows structural edits
- paragraph spacing, indentation, tabs, alignment, and bullet style
- tables, columns, logos, icons, shapes, and images
- headers, footers, page numbering, and contact block placement
- existing hyperlink placement and visual style unless the user asks to change a link itself

## What May Change

- wording inside existing paragraphs and bullets
- summary phrasing
- skill names and keyword placement
- achievement phrasing and metric ordering
- section content emphasis, as long as the surrounding layout stays intact

## Fail-Closed Policy

If preserving the format is a hard requirement:

- do not generate a new `.docx` from scratch
- do not silently simplify or restyle the template
- do not ship a reformatted file just because the wording is better
- if the layout drifts, stop and either retry with smaller edits or provide content-only replacement text

## DOCX Workflow

1. Create a working copy of the original `.docx`.
2. Edit text in place on the copy.
3. Keep paragraph and list structure as stable as practical.
4. Run the format guard:

```bash
python3 skills/write-resume/scripts/docx_format_guard.py original.docx revised.docx
```

5. If the guard fails, do not treat the revised file as final.
6. If the guard passes with warnings about paragraph expansion, review the document for visual spillover or page growth before delivering it.

## ATS Tradeoff Handling

Sometimes the original CV format is not ideal for ATS.

When that happens:

- preserve the format if the user explicitly asked for that
- optimize the text anyway
- tell the user which ATS risks remain because the layout was locked
- ask before making any design or structure changes

## Non-DOCX Sources

If the source is only a PDF or an image:

- do not promise exact format preservation
- ask for an editable source if exact layout preservation matters
- otherwise provide replacement text mapped to the original sections

## Typical Safe Response

When delivering a format-locked rewrite, include:

1. the revised file or revised text
2. whether the format guard passed
3. any residual layout or ATS risks
