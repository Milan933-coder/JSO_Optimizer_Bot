from __future__ import annotations

from typing import Any

import httpx

from coding_round.constants import DEFAULT_JUDGE0_BASE_URL, LANGUAGE_PRESETS, REQUEST_USER_AGENT


async def run_sample_case(
    *,
    source_code: str,
    language_slug: str,
    sample: dict[str, Any],
    sample_index: int,
    judge0_api_key: str | None = None,
    judge0_base_url: str | None = None,
) -> dict[str, Any]:
    execution = await _execute_code(
        source_code=source_code,
        language_slug=language_slug,
        stdin=sample.get("input", ""),
        judge0_api_key=judge0_api_key,
        judge0_base_url=judge0_base_url,
    )
    case_result = _build_case_result(sample, sample_index, execution)
    return {
        "mode": "run",
        "passed": case_result["passed"],
        "verdict": "Sample matched expected output." if case_result["passed"] else "Sample output did not match.",
        "status_summary": case_result["judge0_status"],
        "passed_samples": 1 if case_result["passed"] else 0,
        "total_samples": 1,
        "sample_results": [case_result],
    }


async def submit_against_samples(
    *,
    source_code: str,
    language_slug: str,
    samples: list[dict[str, Any]],
    judge0_api_key: str | None = None,
    judge0_base_url: str | None = None,
) -> dict[str, Any]:
    if not samples:
        raise ValueError("No sample cases are available for this coding round.")

    results: list[dict[str, Any]] = []
    passed_samples = 0

    for sample_index, sample in enumerate(samples):
        execution = await _execute_code(
            source_code=source_code,
            language_slug=language_slug,
            stdin=sample.get("input", ""),
            judge0_api_key=judge0_api_key,
            judge0_base_url=judge0_base_url,
        )
        case_result = _build_case_result(sample, sample_index, execution)
        results.append(case_result)

        if case_result["passed"]:
            passed_samples += 1
            continue

        return {
            "mode": "submit",
            "passed": False,
            "verdict": f"Stopped at sample {sample_index + 1}.",
            "status_summary": case_result["judge0_status"],
            "passed_samples": passed_samples,
            "total_samples": len(samples),
            "sample_results": results,
        }

    return {
        "mode": "submit",
        "passed": True,
        "verdict": "Passed all retrieved sample checks.",
        "status_summary": "Accepted",
        "passed_samples": passed_samples,
        "total_samples": len(samples),
        "sample_results": results,
    }


async def _execute_code(
    *,
    source_code: str,
    language_slug: str,
    stdin: str,
    judge0_api_key: str | None = None,
    judge0_base_url: str | None = None,
) -> dict[str, Any]:
    language = LANGUAGE_PRESETS.get(language_slug)
    if language is None:
        raise ValueError(f"Unsupported coding language '{language_slug}'.")

    base_url = (judge0_base_url or DEFAULT_JUDGE0_BASE_URL).rstrip("/")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": REQUEST_USER_AGENT,
    }
    if judge0_api_key:
        headers["X-Auth-Token"] = judge0_api_key.strip()

    payload = {
        "source_code": source_code,
        "language_id": int(language["judge0_language_id"]),
        "stdin": stdin,
    }

    async with httpx.AsyncClient(timeout=45.0, follow_redirects=True) as client:
        response = await client.post(f"{base_url}/submissions/?wait=true", json=payload, headers=headers)
        response.raise_for_status()

    return response.json()


def _build_case_result(sample: dict[str, Any], sample_index: int, execution: dict[str, Any]) -> dict[str, Any]:
    stdout = execution.get("stdout")
    stderr = execution.get("stderr")
    compile_output = execution.get("compile_output")
    message = execution.get("message")
    status = execution.get("status") or {}
    expected_output = sample.get("output", "")
    actual_output = stdout or ""

    passed = (
        status.get("id") == 3
        and _normalize_output(actual_output) == _normalize_output(expected_output)
    )

    return {
        "sample_index": sample_index,
        "input": sample.get("input", ""),
        "expected_output": expected_output,
        "actual_output": actual_output,
        "passed": passed,
        "judge0_status": status.get("description", "Unknown"),
        "judge0_status_id": status.get("id"),
        "stdout": stdout,
        "stderr": stderr,
        "compile_output": compile_output,
        "message": message,
        "time": execution.get("time"),
        "memory": execution.get("memory"),
    }


def _normalize_output(text: str) -> str:
    normalized = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    return "\n".join(line.rstrip() for line in normalized.split("\n")).strip()

