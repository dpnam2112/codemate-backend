import json
import time
import csv
import argparse
from pathlib import Path
from typing import List, Dict

from .judge0_api import submit_batch_and_get_results
from .metrics import MetricsCalculator

# Constants
MAX_WAIT_SECONDS = 20


def validate_testcases(input_json: Path, output_csv: Path, batch_size: int = 5):
    # Load dataset
    with open(input_json, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    metrics = MetricsCalculator()
    rows = []
    submissions = []
    submission_metadata = []  # To track which submission belongs to which problem/testcase

    # Prepare all submissions
    for problem_idx, problem in enumerate(dataset):
        problem_desc = problem["problem_description"]
        solutions = problem["solutions"]
        testcases = problem["generated_testcases"]

        if not solutions:
            print(f"⚠️ Skipping problem {problem_idx} (no solution)")
            continue

        solution = solutions[0]
        language_id = solution["language_id"]
        code_solution = solution["code_solution"]

        for testcase_idx, testcase in enumerate(testcases):
            input_data = testcase["input"]
            expected_output = testcase["expected_output"]

            submissions.append({
                "source_code": code_solution,
                "language_id": language_id,
                "stdin": input_data,
                "expected_output": expected_output,
                "cpu_time_limit": 5,
                "memory_limit": 128000
            })
            submission_metadata.append((problem_idx, language_id, testcase_idx))

    print(f"✅ Prepared {len(submissions)} submissions.")

    # Batch submit and process results
    all_results = submit_batch_and_get_results(submissions, batch_size=batch_size)

    for meta, result in zip(submission_metadata, all_results):
        problem_idx, language_id, testcase_idx = meta
        status_description = result.get("status", {}).get("description", "Unknown")
        time_taken = result.get("time")  # May be None
        memory = result.get("memory")  # May be None

        if status_description == "Accepted":
            outcome = "Pass"
        elif "Time Limit" in status_description:
            outcome = "Timeout"
        elif "Runtime Error" in status_description:
            outcome = "Runtime Error"
        else:
            outcome = "Fail"

        metrics.update(outcome)

        rows.append({
            "problem_idx": problem_idx,
            "language_id": language_id,
            "testcase_idx": testcase_idx,
            "stdout": result.get("stdout", "").strip() if result.get("stdout") else "",
            "result": outcome,
            "runtime": time_taken,
            "memory": memory,
            "status": status_description
        })

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    metrics.print_summary()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate solutions with generated testcases.")
    parser.add_argument("--input_json", type=Path, required=True, help="Input JSON file path")
    parser.add_argument("--output_csv", type=Path, required=True, help="Output CSV report path")

    args = parser.parse_args()

    validate_testcases(input_json=args.input_json, output_csv=args.output_csv)

