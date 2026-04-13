#!/usr/bin/env python3
"""Search LinkedIn public job openings from a natural-language prompt."""

from __future__ import annotations

import argparse
import html
import json
import math
import os
import re
import sys
from dataclasses import asdict, dataclass
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

GUEST_SEARCH_ENDPOINT = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
SEARCH_PAGE_BASE = "https://www.linkedin.com/jobs/search/"
DEFAULT_LOCATION_ENV = "SEARCH_JOB_OPENINGS_DEFAULT_LOCATION"
DEFAULT_LOCATION = "Chile"
PAGE_SIZE = 10
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

CARD_RE = re.compile(r"<li\b.*?</li>", re.IGNORECASE | re.DOTALL)
TITLE_RE = re.compile(
    r'<h3 class="base-search-card__title">\s*(.*?)\s*</h3>',
    re.IGNORECASE | re.DOTALL,
)
COMPANY_RE = re.compile(
    r'<h4 class="base-search-card__subtitle">\s*(.*?)\s*</h4>',
    re.IGNORECASE | re.DOTALL,
)
LOCATION_RE = re.compile(
    r'<span class="job-search-card__location">\s*(.*?)\s*</span>',
    re.IGNORECASE | re.DOTALL,
)
LINK_RE = re.compile(
    r'class="base-card__full-link[^"]*"[^>]*href="([^"]+)"',
    re.IGNORECASE | re.DOTALL,
)
DATE_RE = re.compile(
    r'<time class="job-search-card__listdate[^"]*" datetime="([^"]+)">\s*(.*?)\s*</time>',
    re.IGNORECASE | re.DOTALL,
)
BENEFITS_RE = re.compile(
    r'<span class="job-posting-benefits__text">\s*(.*?)\s*</span>',
    re.IGNORECASE | re.DOTALL,
)

LOCATION_PATTERNS = [
    re.compile(
        r"\b(?:in|en|near|around|within|from)\s+([A-Za-z0-9][A-Za-z0-9 .,&'/-]+?)"
        r"(?=\s+(?:on\s+linkedin|linkedin|jobs?\b|job openings?\b|roles?\b|openings?\b|"
        r"positions?\b|vacancies\b|vacantes\b|remote\b|remoto\b|hybrid\b|hibrido\b|"
        r"hibrido\b|on[- ]?site\b|onsite\b|presencial\b|full[- ]?time\b|part[- ]?time\b|"
        r"contract\b|temporary\b|intern(ship)?\b|today\b|last\b|this\b|posted\b)|$)",
        re.IGNORECASE,
    ),
]

STARTER_PATTERNS = [
    re.compile(r"\blook\s+for\b", re.IGNORECASE),
    re.compile(r"\bsearch\s+for\b", re.IGNORECASE),
    re.compile(r"\bsearch\b", re.IGNORECASE),
    re.compile(r"\bfind\b", re.IGNORECASE),
    re.compile(r"\bshow\s+me\b", re.IGNORECASE),
    re.compile(r"\blook\s+up\b", re.IGNORECASE),
    re.compile(r"\bbusca(?:r)?\b", re.IGNORECASE),
    re.compile(r"\bencuentra\b", re.IGNORECASE),
    re.compile(r"\bmu[eé]strame\b", re.IGNORECASE),
    re.compile(r"\bquiero\b", re.IGNORECASE),
    re.compile(r"\bnecesito\b", re.IGNORECASE),
]

GENERIC_PATTERNS = [
    re.compile(r"\bon\s+linkedin\b", re.IGNORECASE),
    re.compile(r"\bin\s+linkedin\b", re.IGNORECASE),
    re.compile(r"\ben\s+linkedin\b", re.IGNORECASE),
    re.compile(r"\blinkedin\b", re.IGNORECASE),
    re.compile(r"\bjob openings?\b", re.IGNORECASE),
    re.compile(r"\bjobs?\b", re.IGNORECASE),
    re.compile(r"\bopenings?\b", re.IGNORECASE),
    re.compile(r"\broles?\b", re.IGNORECASE),
    re.compile(r"\bpositions?\b", re.IGNORECASE),
    re.compile(r"\bvacancies\b", re.IGNORECASE),
    re.compile(r"\bvacantes\b", re.IGNORECASE),
    re.compile(r"\btrabajos?\b", re.IGNORECASE),
    re.compile(r"\boportunidades\b", re.IGNORECASE),
    re.compile(r"\bpega\b", re.IGNORECASE),
    re.compile(r"\bposted\b", re.IGNORECASE),
    re.compile(r"\brecent\b", re.IGNORECASE),
    re.compile(r"\blatest\b", re.IGNORECASE),
]

WORKPLACE_PATTERNS = {
    "remote": [
        re.compile(r"\bremote\b", re.IGNORECASE),
        re.compile(r"\bremoto\b", re.IGNORECASE),
        re.compile(r"\bwork\s+from\s+home\b", re.IGNORECASE),
        re.compile(r"\bwfh\b", re.IGNORECASE),
    ],
    "hybrid": [
        re.compile(r"\bhybrid\b", re.IGNORECASE),
        re.compile(r"\bh[íi]brido\b", re.IGNORECASE),
        re.compile(r"\bmixto\b", re.IGNORECASE),
    ],
    "onsite": [
        re.compile(r"\bon[- ]?site\b", re.IGNORECASE),
        re.compile(r"\bonsite\b", re.IGNORECASE),
        re.compile(r"\bpresencial\b", re.IGNORECASE),
    ],
}

WORKPLACE_QUERY_VALUES = {
    "onsite": "1",
    "remote": "2",
    "hybrid": "3",
}

JOB_TYPE_PATTERNS = {
    "full-time": [
        re.compile(r"\bfull[- ]?time\b", re.IGNORECASE),
        re.compile(r"\btiempo\s+completo\b", re.IGNORECASE),
    ],
    "part-time": [
        re.compile(r"\bpart[- ]?time\b", re.IGNORECASE),
        re.compile(r"\bmedio\s+tiempo\b", re.IGNORECASE),
    ],
    "contract": [
        re.compile(r"\bcontract\b", re.IGNORECASE),
        re.compile(r"\bcontractor\b", re.IGNORECASE),
        re.compile(r"\bfreelance\b", re.IGNORECASE),
    ],
    "temporary": [
        re.compile(r"\btemporary\b", re.IGNORECASE),
        re.compile(r"\btemp\b", re.IGNORECASE),
    ],
    "internship": [
        re.compile(r"\bintern(ship)?\b", re.IGNORECASE),
        re.compile(r"\bpractica\b", re.IGNORECASE),
        re.compile(r"\bpracticante\b", re.IGNORECASE),
    ],
}

JOB_TYPE_QUERY_VALUES = {
    "full-time": "F",
    "part-time": "P",
    "contract": "C",
    "temporary": "T",
    "internship": "I",
}

POSTED_PATTERNS = [
    (
        86400,
        [
            re.compile(r"\btoday\b", re.IGNORECASE),
            re.compile(r"\b24h\b", re.IGNORECASE),
            re.compile(r"\b24\s+hours\b", re.IGNORECASE),
            re.compile(r"\blast\s+24\s+hours\b", re.IGNORECASE),
            re.compile(r"\bultimas?\s+24\s+horas\b", re.IGNORECASE),
        ],
    ),
    (
        604800,
        [
            re.compile(r"\bthis\s+week\b", re.IGNORECASE),
            re.compile(r"\blast\s+week\b", re.IGNORECASE),
            re.compile(r"\b7\s+days\b", re.IGNORECASE),
            re.compile(r"\besta\s+semana\b", re.IGNORECASE),
            re.compile(r"\bultim[ao]s?\s+7\s+d[ií]as\b", re.IGNORECASE),
        ],
    ),
    (
        2592000,
        [
            re.compile(r"\bthis\s+month\b", re.IGNORECASE),
            re.compile(r"\blast\s+month\b", re.IGNORECASE),
            re.compile(r"\b30\s+days\b", re.IGNORECASE),
            re.compile(r"\beste\s+mes\b", re.IGNORECASE),
            re.compile(r"\bultim[ao]s?\s+30\s+d[ií]as\b", re.IGNORECASE),
        ],
    ),
]

TOKEN_STOPWORDS = {
    "a",
    "an",
    "any",
    "for",
    "me",
    "please",
    "por",
    "favor",
    "some",
    "the",
    "un",
    "una",
}


@dataclass
class SearchFilters:
    prompt: str
    keywords: str
    location: str | None
    location_source: str
    workplace: str | None
    job_type: str | None
    posted_within_seconds: int | None
    search_url: str
    api_url: str


@dataclass
class JobOpening:
    title: str
    company: str
    location: str
    posted_at: str | None
    posted_relative: str | None
    benefits: str | None
    url: str


def normalize_space(value: str) -> str:
    return " ".join(value.split())


def clean_fragment(value: str | None) -> str:
    if not value:
        return ""
    no_tags = re.sub(r"<[^>]+>", " ", value)
    return normalize_space(html.unescape(no_tags))


def canonicalize_job_url(url: str) -> str:
    raw_url = html.unescape(url)
    parts = urlsplit(raw_url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def detect_first(pattern_map: dict[str, Iterable[re.Pattern[str]]], prompt: str) -> str | None:
    for name, patterns in pattern_map.items():
        for pattern in patterns:
            if pattern.search(prompt):
                return name
    return None


def detect_posted_within(prompt: str) -> int | None:
    for seconds, patterns in POSTED_PATTERNS:
        for pattern in patterns:
            if pattern.search(prompt):
                return seconds
    return None


def detect_location(prompt: str) -> str | None:
    for pattern in LOCATION_PATTERNS:
        match = pattern.search(prompt)
        if match:
            location = normalize_space(match.group(1).strip(" ,.;:"))
            if location:
                return location
    return None


def remove_detected_location(text: str, location: str | None) -> str:
    if not location:
        return text
    escaped = re.escape(location)
    location_expr = re.compile(
        rf"\b(?:in|en|near|around|within|from)\s+{escaped}\b",
        re.IGNORECASE,
    )
    return location_expr.sub(" ", text)


def extract_keywords(prompt: str, detected_location: str | None) -> str:
    text = prompt

    for pattern in STARTER_PATTERNS:
        text = pattern.sub(" ", text)

    text = remove_detected_location(text, detected_location)

    for pattern in GENERIC_PATTERNS:
        text = pattern.sub(" ", text)

    for pattern_group in WORKPLACE_PATTERNS.values():
        for pattern in pattern_group:
            text = pattern.sub(" ", text)

    for pattern_group in JOB_TYPE_PATTERNS.values():
        for pattern in pattern_group:
            text = pattern.sub(" ", text)

    for _, pattern_group in POSTED_PATTERNS:
        for pattern in pattern_group:
            text = pattern.sub(" ", text)

    text = re.sub(r"[^A-Za-z0-9+#./-]+", " ", text)
    tokens = [token for token in text.split() if token.lower() not in TOKEN_STOPWORDS]
    keywords = normalize_space(" ".join(tokens)).strip("-/. ")
    if keywords:
        return keywords

    fallback = re.sub(r"[^A-Za-z0-9+#./-]+", " ", prompt)
    return normalize_space(fallback).strip("-/. ")


def build_query_params(filters: SearchFilters, start: int | None = None) -> dict[str, str]:
    params = {"keywords": filters.keywords}
    if filters.location:
        params["location"] = filters.location
    if filters.workplace:
        params["f_WT"] = WORKPLACE_QUERY_VALUES[filters.workplace]
    if filters.job_type:
        params["f_JT"] = JOB_TYPE_QUERY_VALUES[filters.job_type]
    if filters.posted_within_seconds:
        params["f_TPR"] = f"r{filters.posted_within_seconds}"
    if start is not None:
        params["start"] = str(start)
    return params


def build_search_url(filters: SearchFilters) -> str:
    return f"{SEARCH_PAGE_BASE}?{urlencode(build_query_params(filters))}"


def build_api_url(filters: SearchFilters, start: int = 0) -> str:
    return f"{GUEST_SEARCH_ENDPOINT}?{urlencode(build_query_params(filters, start=start))}"


def parse_prompt(
    prompt: str,
    location_override: str | None,
    default_location: str | None,
    use_default_location: bool,
) -> SearchFilters:
    normalized_prompt = normalize_space(prompt)
    workplace = detect_first(WORKPLACE_PATTERNS, normalized_prompt)
    job_type = detect_first(JOB_TYPE_PATTERNS, normalized_prompt)
    posted_within = detect_posted_within(normalized_prompt)

    if location_override:
        location = normalize_space(location_override)
        location_source = "override"
        detected_location = location
    else:
        detected_location = detect_location(normalized_prompt)
        if detected_location:
            location = detected_location
            location_source = "prompt"
        elif use_default_location and default_location:
            location = normalize_space(default_location)
            location_source = "default"
        else:
            location = None
            location_source = "none"

    keywords = extract_keywords(normalized_prompt, detected_location)
    if not keywords:
        raise ValueError("Could not extract role keywords from the prompt.")

    filters = SearchFilters(
        prompt=normalized_prompt,
        keywords=keywords,
        location=location,
        location_source=location_source,
        workplace=workplace,
        job_type=job_type,
        posted_within_seconds=posted_within,
        search_url="",
        api_url="",
    )
    filters.search_url = build_search_url(filters)
    filters.api_url = build_api_url(filters)
    return filters


def fetch_search_page(filters: SearchFilters, start: int) -> str:
    request = Request(
        build_api_url(filters, start=start),
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": filters.search_url,
        },
    )
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", errors="replace")


def extract_first(pattern: re.Pattern[str], text: str) -> tuple[str, ...] | None:
    match = pattern.search(text)
    if not match:
        return None
    return match.groups()


def parse_cards(markup: str) -> list[JobOpening]:
    jobs: list[JobOpening] = []
    seen_urls: set[str] = set()

    for card in CARD_RE.findall(markup):
        link_groups = extract_first(LINK_RE, card)
        title_groups = extract_first(TITLE_RE, card)
        if not link_groups or not title_groups:
            continue

        url = canonicalize_job_url(link_groups[0])
        if url in seen_urls:
            continue

        company_groups = extract_first(COMPANY_RE, card)
        location_groups = extract_first(LOCATION_RE, card)
        date_groups = extract_first(DATE_RE, card)
        benefits_groups = extract_first(BENEFITS_RE, card)

        posted_at = None
        posted_relative = None
        if date_groups:
            posted_at = clean_fragment(date_groups[0]) or None
            posted_relative = clean_fragment(date_groups[1]) or None

        job = JobOpening(
            title=clean_fragment(title_groups[0]),
            company=clean_fragment(company_groups[0]) if company_groups else "",
            location=clean_fragment(location_groups[0]) if location_groups else "",
            posted_at=posted_at,
            posted_relative=posted_relative,
            benefits=clean_fragment(benefits_groups[0]) if benefits_groups else None,
            url=url,
        )
        if not job.title:
            continue

        seen_urls.add(url)
        jobs.append(job)

    return jobs


def collect_results(filters: SearchFilters, limit: int) -> list[JobOpening]:
    jobs: list[JobOpening] = []
    seen_urls: set[str] = set()
    pages = max(1, math.ceil(limit / PAGE_SIZE))

    for page_index in range(pages):
        markup = fetch_search_page(filters, start=page_index * PAGE_SIZE)
        page_jobs = parse_cards(markup)
        if not page_jobs:
            break

        new_count = 0
        for job in page_jobs:
            if job.url in seen_urls:
                continue
            seen_urls.add(job.url)
            jobs.append(job)
            new_count += 1
            if len(jobs) >= limit:
                return jobs

        if new_count == 0:
            break

    return jobs


def format_location_line(filters: SearchFilters) -> str:
    if not filters.location:
        return "Location: global search"
    if filters.location_source == "default":
        return f"Location: {filters.location} (default)"
    return f"Location: {filters.location}"


def format_filter_line(filters: SearchFilters) -> str:
    parts: list[str] = []
    if filters.workplace:
        parts.append(f"workplace={filters.workplace}")
    if filters.job_type:
        parts.append(f"job_type={filters.job_type}")
    if filters.posted_within_seconds:
        parts.append(f"posted_within={filters.posted_within_seconds}s")
    return "Filters: " + (", ".join(parts) if parts else "none")


def print_text(filters: SearchFilters, jobs: list[JobOpening]) -> None:
    print(f"Prompt: {filters.prompt}")
    print(f"Keywords: {filters.keywords}")
    print(format_location_line(filters))
    print(format_filter_line(filters))
    print(f"Search URL: {filters.search_url}")
    print("")

    if not jobs:
        print("No LinkedIn openings matched this query.")
        return

    for index, job in enumerate(jobs, start=1):
        headline = f"{index}. {job.title}"
        meta_parts = [part for part in [job.company, job.location, job.posted_relative] if part]
        print(headline)
        if meta_parts:
            print(f"   {' | '.join(meta_parts)}")
        if job.benefits:
            print(f"   {job.benefits}")
        print(f"   {job.url}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search LinkedIn public job openings from a natural-language prompt."
    )
    parser.add_argument("prompt", help="Natural-language request, for example: look for cloud architect jobs")
    parser.add_argument(
        "--location",
        help="Force a specific location instead of relying on the prompt or default fallback.",
    )
    parser.add_argument(
        "--no-default-location",
        action="store_true",
        help="Skip the default location fallback and search globally when the prompt has no location.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of jobs to return. Default: 10.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print structured JSON instead of a text summary.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.limit < 1:
        print("--limit must be at least 1.", file=sys.stderr)
        return 2

    default_location = os.environ.get(DEFAULT_LOCATION_ENV, DEFAULT_LOCATION)

    try:
        filters = parse_prompt(
            prompt=args.prompt,
            location_override=args.location,
            default_location=default_location,
            use_default_location=not args.no_default_location,
        )
        jobs = collect_results(filters, limit=args.limit)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except HTTPError as exc:
        print(f"LinkedIn returned HTTP {exc.code}: {exc.reason}", file=sys.stderr)
        return 1
    except URLError as exc:
        print(f"Network error while contacting LinkedIn: {exc.reason}", file=sys.stderr)
        return 1

    if args.json:
        payload = {
            "filters": asdict(filters),
            "results": [asdict(job) for job in jobs],
        }
        print(json.dumps(payload, indent=2))
        return 0

    print_text(filters, jobs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
