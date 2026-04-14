---
name: write-resume
description: Rewrite and tailor a resume or CV for a specific job description while maximizing ATS compatibility, preserving factual accuracy, and, when requested, preserving the original document layout and formatting. Use when the user asks to rewrite, tailor, optimize, target, adapt, or strengthen a resume for a role, job ad, application portal, or ATS workflow, especially when they want higher interview odds, stronger keyword alignment, a version tuned to Workday, Greenhouse, Lever, or similar systems, or a rewrite that keeps the original CV template unchanged.
---

# Write Resume

Use this skill when you have a current resume and a target job description. The goal is to produce a sharper, more relevant, ATS-friendly version that mirrors the job ad where truthful and stays human-sounding.

Read [references/ats-optimization-principles.md](references/ats-optimization-principles.md) for the distilled rules from the attached ATS PDF. Read [references/format-preservation-safeguards.md](references/format-preservation-safeguards.md) when the user wants the original CV format preserved. Read [references/rewrite-checklist.md](references/rewrite-checklist.md) for the delivery structure and final QA pass.

## Required Inputs

- the current resume or CV
- the target job description or job ad
- any explicit user constraints such as page count, tone, language, region, format, or achievements to emphasize
- the editable source file when the user wants the original layout preserved exactly

If the job description is missing, ask for it before tailoring. If the resume is missing, ask for it or state that you can only produce a generic ATS-ready template and targeting brief. If exact format preservation is required and the source is only a PDF or image, do not promise a pixel-faithful rewrite; ask for an editable source such as `.docx` or deliver content-only replacement text.

## Format-Locked Mode

If the user says the format, template, layout, styling, or original CV look must stay unchanged, treat the document as format-locked.

In format-locked mode:

- work on a copy of the original file, never the only original
- preserve the existing layout, margins, sections, fonts, colors, spacing, bullets, alignment, tables, headers, footers, logos, and visual hierarchy
- rewrite text in place instead of rebuilding the document from scratch
- keep the same section order unless the user explicitly allows structural edits
- prefer content tightening over layout changes when new wording starts to expand the document
- if the original template is not fully ATS-safe, preserve it anyway and clearly state the residual ATS risk instead of silently reformatting it
- after editing a `.docx`, run `python3 skills/write-resume/scripts/docx_format_guard.py original.docx revised.docx`
- if the guard fails, do not ship the edited file as final; retry with smaller in-place edits or provide text-only replacement content

## Workflow

1. Decide the operating mode first.
Determine whether the user wants a content rewrite only, a direct file rewrite, or a format-locked rewrite on top of the original template.

2. Build the targeting brief.
Identify the target job title, hard skills, tools, certifications, domain phrases, seniority, workplace mode, and explicit asks in the ad. Separate them into must-have, strongly preferred, and nice-to-have.

3. Map evidence before rewriting.
Match each important requirement to evidence already present in the resume. Do not invent missing experience, dates, tools, titles, certifications, or metrics. If a requirement is unsupported, reposition adjacent transferable evidence and call out the gap outside the resume draft.

4. Choose the rewrite scope.
If the user asks for a full rewrite, update headline or summary, core skills, experience bullets, projects, certifications, and section ordering. If they ask for partial help, only touch the requested sections.

5. Rewrite for ATS and humans at the same time.
Use exact job-description wording where truthful, especially for the target title, tools, platforms, certifications, and domain phrases. Place the most important terms in the summary, skills section, and recent relevant bullets. Keep the structure simple, single-column, and based on standard headings. Prefer quantified achievement bullets that show action plus outcome instead of vague responsibility lists.

6. Preserve the original file format when required.
If editing a format-locked source file, modify the copy in place, keep paragraph and list formatting stable, and validate the result with `docx_format_guard.py`. Treat any formatting drift as a blocker, not as a minor issue.

7. Keep the voice believable.
Remove repetitive AI-style phrasing, empty buzzwords, and stuffed keyword lists. Preserve a direct, competent tone that still sounds like the candidate.

8. Deliver the tailored result plus a short review.
Produce the rewritten resume content and include a compact note with matched priorities, any uncovered gaps, and any assumptions you had to make.

## Rewrite Rules

- Preserve factual integrity above all else.
- Prefer standard section headers such as `Summary`, `Skills`, `Professional Experience`, `Education`, and `Certifications`.
- Avoid tables, text boxes, multi-column layouts, graphics, icons, progress bars, and critical information in headers or footers.
- Mirror exact phrases from the job ad when they are true for the candidate, including full term plus acronym when useful.
- Use reverse-chronological ordering unless the user asks for a different structure.
- Bias toward achievements with metrics, scope, timeframes, scale, reliability, cost, performance, or revenue impact.
- If the ad and resume are in different languages, default to the language of the target job unless the user specifies otherwise.
- If the target market is not specified, default to a conservative ATS-safe format with no photo or personal data beyond standard contact details.
- If the user locks the original format, do not rebuild the document in a new template or restyle it to be more ATS-safe without explicit permission.
- If the user locks the original format and the existing template has ATS weaknesses, optimize the wording and tell the user what format-related risks remain.

## Output Pattern

When rewriting in chat, use this order unless the user asks for something else:

1. A brief targeting summary with the role and top matched themes.
2. The tailored resume draft or revised sections.
3. A short gap note listing anything the ad asks for that was not supported by the original resume.

If you are editing a resume file directly, apply the same logic but keep the finished document plain and parseable. In format-locked mode, also report whether the format guard passed and mention any remaining reflow warnings.

## Examples

- "Rewrite my CV for this cloud architect role and emphasize Azure landing zones, stakeholder work, and migration experience."
- "Tailor my resume for this Workday application and keep it under two pages."
- "Use the job ad to rewrite only my summary and experience bullets so it is more ATS-friendly."
- "Compare my resume to this JD, tell me the missing keywords, then produce a revised version."
- "Rewrite this DOCX for the job ad, but do not alter the original CV formatting."
- "Tailor the content to the role and keep the same layout, fonts, spacing, and template."

## Notes

- Prefer precision automation over generic mass-application language. Tailoring quality matters more than volume.
- If the user mentions a specific ATS or region, use the platform and regional notes in the reference file to adjust the rewrite.
- If the user asks for unsupported claims to be inserted, refuse that part and explain the risk to ATS screening and later interviews.
- If preserving the original format conflicts with ideal ATS cleanup, keep the format only when the user asked for it and explain the tradeoff clearly.
