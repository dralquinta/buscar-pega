# buscar-pega

Codex skill repository for job hunting and resume tailoring.

## Current functionality

This repository currently implements two skills:

### `search-job-openings`

Search LinkedIn public job openings from a natural-language prompt.

- Accepts prompts like `look for cloud architect jobs`
- Extracts role keywords, location, workplace mode, job type, and recency filters
- Defaults the location to `Chile` when the prompt does not provide one
- Returns direct LinkedIn job links and can also return JSON output

Example:

```bash
python3 skills/search-job-openings/scripts/search_linkedin_jobs.py "look for cloud architect jobs"
```

### `write-resume`

Rewrite and tailor a resume or CV for a specific job description with ATS-safe structure and stronger keyword alignment.

- Uses the ATS guidance distilled from `hars/ATS-Friendly Resume Optimization Strategy.pdf`
- Rewrites summaries, skills, and experience bullets around the target role
- Keeps the resume factual and avoids inventing tools, metrics, titles, or certifications
- Applies ATS-friendly rules such as single-column structure, standard headings, exact terminology alignment, and quantified achievements
- Includes platform-aware and region-aware guidance for systems such as Workday, Greenhouse, and Lever

Typical usage:

```text
Use $write-resume to tailor my resume to this Cloud Architect job description and keep it ATS-friendly.
```

## Repository structure

- `skills/search-job-openings/`: LinkedIn job search skill and helper script
- `skills/write-resume/`: ATS-focused resume rewriting skill and references
- `hars/`: research and supporting material used to ground the resume skill

## Current scope

The implemented scope today is:

- searching for job openings on LinkedIn
- rewriting resumes for specific job ads to improve ATS compatibility and interview chances

Automated job application submission is not implemented in this repository at the moment.
