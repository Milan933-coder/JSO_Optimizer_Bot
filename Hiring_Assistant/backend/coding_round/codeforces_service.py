from __future__ import annotations

import html
import random
import re
import time
from typing import Any

import httpx
from bs4 import BeautifulSoup, NavigableString, Tag

from coding_round.constants import (
    CODEFORCES_MAX_RATING,
    CODEFORCES_MIN_RATING,
    REQUEST_USER_AGENT,
)


CODEFORCES_API_URL = "https://codeforces.com/api/problemset.problems"
CODEFORCES_MIRROR_URL = "https://mirror.codeforces.com/problemset/problem/{contest_id}/{index}"
CODEFORCES_PUBLIC_URL = "https://codeforces.com/problemset/problem/{contest_id}/{index}"
CATALOG_CACHE_TTL_SECONDS = 600

_catalog_cache: dict[str, Any] = {"fetched_at": 0.0, "problems": []}


async def fetch_random_medium_problem() -> dict[str, Any]:
    candidates = await _load_problem_catalog()
    if not candidates:
        raise RuntimeError("No Codeforces problems matched the configured medium range.")

    random.shuffle(candidates)
    last_error: Exception | None = None

    for candidate in candidates[:30]:
        try:
            return await _hydrate_problem(candidate)
        except Exception as exc:  # pragma: no cover - external HTML can be inconsistent
            last_error = exc

    raise RuntimeError("Unable to retrieve a usable Codeforces problem statement right now.") from last_error


async def _load_problem_catalog() -> list[dict[str, Any]]:
    now = time.time()
    cached = _catalog_cache.get("problems", [])
    if cached and (now - float(_catalog_cache.get("fetched_at", 0.0))) < CATALOG_CACHE_TTL_SECONDS:
        return list(cached)

    async with httpx.AsyncClient(
        timeout=25.0,
        headers={"User-Agent": REQUEST_USER_AGENT},
        follow_redirects=True,
    ) as client:
        response = await client.get(CODEFORCES_API_URL)
        response.raise_for_status()

    payload = response.json()
    result = payload.get("result", {})
    problems = result.get("problems", [])
    problem_stats = result.get("problemStatistics", [])
    solved_lookup = {
        (item.get("contestId"), item.get("index")): item.get("solvedCount")
        for item in problem_stats
    }

    filtered: list[dict[str, Any]] = []
    for problem in problems:
        rating = problem.get("rating")
        contest_id = problem.get("contestId")
        index = problem.get("index")
        tags = problem.get("tags", [])

        if not isinstance(rating, int):
            continue
        if not isinstance(contest_id, int) or not index:
            continue
        if not (CODEFORCES_MIN_RATING <= rating <= CODEFORCES_MAX_RATING):
            continue
        if problem.get("type") != "PROGRAMMING":
            continue
        if "interactive" in tags or "*special" in tags:
            continue

        filtered.append(
            {
                "contest_id": contest_id,
                "index": index,
                "title": problem.get("name", "Untitled Problem"),
                "rating": rating,
                "tags": tags,
                "solved_count": solved_lookup.get((contest_id, index)),
            }
        )

    _catalog_cache["fetched_at"] = now
    _catalog_cache["problems"] = list(filtered)
    return filtered


async def _hydrate_problem(problem: dict[str, Any]) -> dict[str, Any]:
    contest_id = problem["contest_id"]
    index = problem["index"]
    mirror_url = CODEFORCES_MIRROR_URL.format(contest_id=contest_id, index=index)
    public_url = CODEFORCES_PUBLIC_URL.format(contest_id=contest_id, index=index)

    async with httpx.AsyncClient(
        timeout=25.0,
        headers={"User-Agent": REQUEST_USER_AGENT},
        follow_redirects=True,
    ) as client:
        response = await client.get(mirror_url)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    root = soup.select_one(".problem-statement")
    if root is None:
        raise RuntimeError(f"Problem statement not found for {contest_id}{index}.")

    header_title = root.select_one(".header .title")
    time_limit_node = root.select_one(".time-limit")
    memory_limit_node = root.select_one(".memory-limit")
    statement_node = next((child for child in root.find_all("div", recursive=False) if not child.get("class")), None)
    input_spec_node = root.select_one(".input-specification")
    output_spec_node = root.select_one(".output-specification")
    note_node = root.select_one(".note")

    sample_inputs = root.select(".sample-tests .input pre")
    sample_outputs = root.select(".sample-tests .output pre")
    samples = []
    for idx, (sample_in, sample_out) in enumerate(zip(sample_inputs, sample_outputs), start=1):
        samples.append(
            {
                "index": idx - 1,
                "title": f"Sample {idx}",
                "input": _extract_pre_text(sample_in),
                "output": _extract_pre_text(sample_out),
            }
        )

    if not samples:
        raise RuntimeError(f"No sample tests found for {contest_id}{index}.")

    return {
        "source": "Codeforces",
        "source_url": public_url,
        "mirror_url": mirror_url,
        "title": _clean_text(header_title.get_text(" ", strip=True) if header_title else problem["title"]),
        "codeforces_id": f"{contest_id}{index}",
        "contest_id": contest_id,
        "index": index,
        "rating": int(problem["rating"]),
        "solved_count": problem.get("solved_count"),
        "tags": list(problem.get("tags", [])),
        "statement": _extract_section_text(statement_node),
        "input_spec": _extract_section_text(input_spec_node),
        "output_spec": _extract_section_text(output_spec_node),
        "notes": _extract_section_text(note_node) or None,
        "time_limit": _clean_limit(time_limit_node.get_text(" ", strip=True) if time_limit_node else "Unknown"),
        "memory_limit": _clean_limit(memory_limit_node.get_text(" ", strip=True) if memory_limit_node else "Unknown"),
        "samples": samples,
    }


def _extract_section_text(node: Any) -> str:
    if node is None:
        return ""

    section = BeautifulSoup(str(node), "html.parser")
    section_title = section.select_one(".section-title")
    if section_title is not None:
        section_title.decompose()

    text = _render_html_text(section)
    text = html.unescape(text)
    return _clean_text(text)


def _extract_pre_text(node: Any) -> str:
    if node is None:
        return ""

    sample = BeautifulSoup(str(node), "html.parser")
    for break_tag in sample.find_all("br"):
        break_tag.replace_with("\n")

    text = sample.get_text("\n", strip=False)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = html.unescape(text)
    return text.strip("\n")


def _clean_limit(text: str) -> str:
    return _clean_text(text.replace("time limit per test", "").replace("memory limit per test", ""))


def _render_html_text(node: Any) -> str:
    if isinstance(node, NavigableString):
        return str(node)

    if not isinstance(node, Tag):
        return ""

    if node.name in {"script", "style"}:
        return ""

    if node.name == "br":
        return "\n"

    if "tex-span" in node.get("class", []):
        return _render_math_span(node)

    if node.name == "sup":
        value = _clean_inline_text("".join(_render_html_text(child) for child in node.children))
        return f"^{value}" if value else ""

    if node.name == "sub":
        value = _clean_inline_text("".join(_render_html_text(child) for child in node.children))
        return f"_{value}" if value else ""

    children_text = "".join(_render_html_text(child) for child in node.children)

    if node.name == "li":
        return f"- {_clean_inline_text(children_text)}\n"

    if node.name in {"p", "div"}:
        stripped = children_text.strip()
        return f"{stripped}\n\n" if stripped else ""

    if node.name in {"ul", "ol"}:
        stripped = children_text.strip()
        return f"{stripped}\n\n" if stripped else ""

    return children_text


def _render_math_span(node: Tag) -> str:
    clone = BeautifulSoup(str(node), "html.parser")

    for sup_tag in clone.find_all("sup"):
        sup_text = _clean_inline_text(sup_tag.get_text("", strip=True))
        sup_tag.replace_with(f"^{sup_text}" if sup_text else "")

    for sub_tag in clone.find_all("sub"):
        sub_text = _clean_inline_text(sub_tag.get_text("", strip=True))
        sub_tag.replace_with(f"_{sub_text}" if sub_text else "")

    raw_text = clone.get_text(" ", strip=False)
    return _clean_inline_text(raw_text)


def _clean_inline_text(text: str) -> str:
    normalized = text.replace("\xa0", " ").replace("\u2009", " ").replace("\u202f", " ")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\s+([,.;:!?])", r"\1", normalized)
    normalized = re.sub(r"([([{])\s+", r"\1", normalized)
    normalized = re.sub(r"\s+([)\]}])", r"\1", normalized)
    normalized = re.sub(r"\s*\^\s*", "^", normalized)
    normalized = re.sub(r"\s*_\s*", "_", normalized)
    return normalized.strip()


def _clean_text(text: str) -> str:
    normalized = text.replace("\xa0", " ")
    normalized = normalized.replace("\u2009", " ").replace("\u202f", " ")
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+\n", "\n", normalized)
    normalized = re.sub(r"\n[ \t]+", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    normalized = re.sub(r"[ \t]{2,}", " ", normalized)
    return normalized.strip()
