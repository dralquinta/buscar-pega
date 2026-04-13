---
name: search-job-openings
description: Search LinkedIn job openings from a natural-language request and summarize the best matches. Use when the user asks to look for jobs, openings, or roles on LinkedIn with prompts like "look for cloud architect jobs", "find remote platform engineer roles in Santiago", or "search for senior data engineer openings posted this week".
---

# Search Job Openings

Use the bundled script to turn a free-form job-search request into a LinkedIn public jobs search, fetch the current results, and summarize the strongest matches.

## Quick Start

Run the script with the user's request as-is:

```bash
python3 skills/search-job-openings/scripts/search_linkedin_jobs.py "look for cloud architect jobs"
```

The script:
- extracts the role keywords from the prompt
- detects location, workplace mode, job type, and recency filters when present
- defaults the location to `Chile` when the prompt does not mention one
- prints the LinkedIn search URL plus the top matching job cards with direct links

## Workflow

1. Run `search_linkedin_jobs.py` with the user's request exactly as written.
2. Review the parsed assumptions the script prints before the results.
3. Summarize the best matches with title, company, location, posted age, and direct URL.
4. If the results are too narrow or too broad, refine once by adjusting location, removing excess qualifiers, or increasing the limit.
5. Mention when the default location was used so the user can redirect the search if needed.

## Useful Commands

Search with the default location:

```bash
python3 skills/search-job-openings/scripts/search_linkedin_jobs.py "look for cloud architect jobs"
```

Force a specific location:

```bash
python3 skills/search-job-openings/scripts/search_linkedin_jobs.py \
  "find remote platform engineer jobs" \
  --location "Santiago, Chile"
```

Search globally instead of using the default location:

```bash
python3 skills/search-job-openings/scripts/search_linkedin_jobs.py \
  "search for cloud architect jobs" \
  --no-default-location
```

Return machine-readable output:

```bash
python3 skills/search-job-openings/scripts/search_linkedin_jobs.py \
  "look for cloud architect jobs in Chile posted this week" \
  --json
```

## Notes

- Prefer the direct job links from the script output over the noisy tracked links in copied HTML.
- Use `--location` when the prompt is ambiguous or when you want to override the default `Chile` fallback.
- Treat the LinkedIn guest endpoint as best-effort. If LinkedIn changes its markup or blocks requests, report that clearly instead of guessing.
