import csv
import json
import argparse
from pathlib import Path
from tqdm import tqdm


def load_problems_from_csv(csv_path: Path) -> list[dict]:
    problems = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            problems.append(row)
    return problems


def prepare_raw_dataset(problems: list[dict], num_problems: int = None) -> list[dict]:
    dataset = []
    selected = problems[:num_problems] if num_problems else problems

    for p in tqdm(selected, desc="Preparing problems"):
        problem_description = p.get("content") or p.get("description") or p.get("title")
        if not problem_description:
            continue  # Skip nếu không có đề bài

        dataset.append({
            "problem_description": problem_description.strip(),
            "solutions": [],
            "generated_testcases": []
        })

    return dataset


def save_json(dataset: list[dict], output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert LeetCode CSV dataset to raw JSON format (no solutions, no testcases).")
    parser.add_argument("--input_csv", type=Path, required=True, help="Input CSV file path")
    parser.add_argument("--output_json", type=Path, required=True, help="Output JSON file path")
    parser.add_argument("--num_problems", type=int, default=None, help="Number of problems to select")

    args = parser.parse_args()

    problems = load_problems_from_csv(args.input_csv)
    dataset = prepare_raw_dataset(problems, num_problems=args.num_problems)
    save_json(dataset, args.output_json)

    print(f"✅ Converted {len(dataset)} problems to {args.output_json}")

