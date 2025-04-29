# judge0_batch_api.py

import time
import requests
from core.settings import settings as env_settings
from typing import List, Dict

JUDGE0_BASE_URL = env_settings.JUDGE0_URL
SUBMISSIONS_URL = f"{JUDGE0_BASE_URL}/submissions"
BATCH_SUBMISSIONS_URL = f"{SUBMISSIONS_URL}/batch"
API_KEY = env_settings.RAPIDAPI_KEY

HEADERS = {
    "x-rapidapi-host": "judge0-ce.p.rapidapi.com",
    "x-rapidapi-key": API_KEY,
    "content-type": "application/json"
}

MAX_WAIT_SECONDS = 20


def submit_batch_and_get_results(submissions: List[Dict], batch_size: int = 10, wait_seconds: int = MAX_WAIT_SECONDS) -> List[Dict]:
    """
    Submits a batch of code submissions and retrieves their results.
    :param submissions: List of submission dicts {source_code, language_id, stdin, expected_output}
    :param batch_size: Max number of submissions per batch (default 10)
    :param wait_seconds: Max time to wait for Judge0 to return results
    :return: List of Judge0 results for each submission
    """
    all_results = []

    # Split submissions into batches
    for i in range(0, len(submissions), batch_size):
        batch = submissions[i:i + batch_size]

        # Submit batch
        payload = {"submissions": batch}
        response = requests.post(BATCH_SUBMISSIONS_URL, json=payload, headers=HEADERS)
        response.raise_for_status()

        tokens = [item["token"] for item in response.json()]

        # Poll tokens
        total_wait = 0
        while total_wait < wait_seconds:
            tokens_str = ",".join(tokens)
            poll_url = f"{BATCH_SUBMISSIONS_URL}?tokens={tokens_str}"
            poll_response = requests.get(poll_url, headers=HEADERS)
            poll_response.raise_for_status()

            results = poll_response.json().get("submissions", [])

            # Check if all finished
            if all(r.get("status", {}).get("id") in [3, 4, 5, 6, 7, 8, 9, 10] for r in results):
                all_results.extend(results)
                break

            time.sleep(1)
            total_wait += 1
        else:
            raise TimeoutError("Judge0 API batch timeout exceeded.")

    return all_results
