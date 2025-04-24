#!snippets/judge0_api.py
from typing import Any
import httpx
from core.settings import settings as env_settings
from core.logger import syslog
from contextlib import asynccontextmanager
from typing import AsyncGenerator

@asynccontextmanager
async def judge0_httpx_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    default_headers = {
        "x-rapidapi-host": env_settings.RAPIDAPI_HOST,
        "x-rapidapi-key": env_settings.RAPIDAPI_KEY
    },

    api_base_url = env_settings.JUDGE0_URL
    
    async with httpx.AsyncClient(
        base_url=api_base_url, headers=default_headers
    ) as client:
        yield client

async def evaluate_test_cases(
    source_code: str, language_id: int, test_cases: list[dict[str, str]]
) -> list[dict[str, Any]]:
    """Evaluate test cases using Judge0 batch API.

    Args:
        source_code (str): User's source code.
        language_id (int): Judge0 language ID.
        test_cases (list[dict[str, str]]): Test cases with 'input' and 'expected' keys.

    Returns:
        list[dict[str, Any]]: Evaluation results per test case.
    """
    results: list[dict[str, Any]] = []

    submissions_payload = [
        {
            "source_code": source_code,
            "language_id": language_id,
            "stdin": case["input"],
            "expected_output": case["expected"],
        }
        for case in test_cases
    ]

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            submit_response = await client.post(
                f"{env_settings.JUDGE0_URL}/submissions/batch",
                json={"submissions": submissions_payload},
                headers={
                    "x-rapidapi-host": env_settings.RAPIDAPI_HOST,
                    "x-rapidapi-key": env_settings.RAPIDAPI_KEY,
                },
                params={"base64_encoded": False},
            )
            submit_response.raise_for_status()
            tokens_response = submit_response.json()
        except httpx.HTTPError as exc:
            syslog.error(f"Judge0 batch submission failed: {exc}")
            raise

    tokens = [entry.get("token") for entry in tokens_response if "token" in entry]
    if not tokens:
        raise ValueError("No valid submission tokens returned from Judge0.")

    return await get_submission_results(tokens, test_cases)


async def get_submission_results(
    tokens: list[str], test_cases: list[dict[str, str]]
) -> list[dict[str, Any]]:
    """Retrieve results for a batch of Judge0 tokens.

    Args:
        tokens (list[str]): List of submission tokens.
        test_cases (list[dict[str, str]]): Corresponding test cases.

    Returns:
        list[dict[str, Any]]: Detailed results per submission.
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            tokens_str = ",".join(tokens)
            result_response = await client.get(
                f"{env_settings.JUDGE0_URL}/submissions/batch",
                headers={
                    "x-rapidapi-host": env_settings.RAPIDAPI_HOST,
                    "x-rapidapi-key": env_settings.RAPIDAPI_KEY,
                },
                params={"tokens": tokens_str, "base64_encoded": False},
            )
            result_response.raise_for_status()
            result_data = result_response.json()
        except httpx.HTTPError as exc:
            syslog.error(f"Failed to retrieve Judge0 results: {exc}")
            raise

    judge0_submissions = result_data.get("submissions", [])
    results: list[dict[str, Any]] = []

    for i, result in enumerate(judge0_submissions):
        passed = result.get("status", {}).get("id") == 3
        results.append(
            {
                "test_case": i + 1,
                "token": result.get("token"),
                "input": test_cases[i]["input"],
                "expected": test_cases[i]["expected"],
                "stdout": result.get("stdout"),
                "stderr": result.get("stderr"),
                "status": result.get("status", {}).get("description"),
                "passed": passed,
            }
        )

    return results

