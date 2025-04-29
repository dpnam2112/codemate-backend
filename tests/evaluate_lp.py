import argparse
import litellm

from datetime import datetime
import json
import csv
from pathlib import Path
from typing import List

import asyncio
from deepeval import evaluate
from deepeval.test_case import LLMTestCase
from deepeval.models.base_model import DeepEvalBaseLLM

from tests.utils import build_course_context, build_llm_learning_path_output
from tests.model_factory import get_model_for_experiment
from .metrics import (
    get_goal_alignment_metric,
    get_explanation_quality_metric,
    get_ordering_logic_metric,
    get_module_appropriateness_metric,
)

# Default models to be used as judges, in the cases that models aren't specified in the CLI
DEFAULT_MODEL_NAMES = [
    "gpt-4o-mini",
    "gpt-4.1-nano",
    "gpt-4.1-mini"
#    "gemini/gemini-2.0-flash"
]

def load_learning_paths(filepath: str) -> List[dict]:
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["learning_paths"]

def build_test_case(path: dict) -> LLMTestCase:
    goal = path["metadata"]["objective"]
    course_context = build_course_context(path)
    actual_output = build_llm_learning_path_output(path)

    return LLMTestCase(
        input=goal,
        actual_output=actual_output,
        context=[course_context],
        additional_metadata={
            "goal": goal,
            "path_id": path["id"]
        }
    )

def get_all_metrics(model: DeepEvalBaseLLM):
    return [
        get_goal_alignment_metric(model),
        get_explanation_quality_metric(model),
        get_ordering_logic_metric(model),
        get_module_appropriateness_metric(model),
    ]

def sanitize_filename(name: str) -> str:
    return name.replace("/", "_").replace("\\", "_").replace(" ", "_")

async def evaluate_all_models(
    input_file: str,
    output_dir: str,
    model_names: List[str]
):
    timestamp = datetime.now().strftime("%Y%m%d-%H%M")
    output_filename = f"learning_path_eval_{timestamp}.csv"
    output_path = Path(output_dir) / sanitize_filename(output_filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    paths = load_learning_paths(input_file)
    test_cases = [build_test_case(p) for p in paths]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["path_id", "goal", "model", "metric", "score", "reason"])
        writer.writeheader()

        for model_name in model_names:
            print(f"Evaluating with model: {model_name}")
            model = get_model_for_experiment(model_name)
            metrics = get_all_metrics(model)

            # Avoid rate limit when calling API providers
            if "gemini" in model_name:
                # Google VertexAI
                max_concurrent = 5
            elif "together" in model_name:
                max_concurrent = 2
            else:
                max_concurrent = 60

            results = evaluate(test_cases=test_cases, metrics=metrics, max_concurrent=max_concurrent)
            test_results = results.test_results

            for result in test_results:
                tc_metadata = result.additional_metadata or {}
                for m in result.metrics_data or []:
                    row = {
                        "path_id": tc_metadata.get("path_id", ""),
                        "goal": tc_metadata.get("goal", ""),
                        "model": model_name,
                        "metric": m.name,
                        "score": m.score,
                        "reason": m.reason,
                    }
                    writer.writerow(row)

    print(f"All model results saved to {output_path}")

def parse_args():
    parser = argparse.ArgumentParser(description="Batch evaluate learning paths across multiple models.")
    parser.add_argument("--input", "-i", required=True, help="Input JSON file containing learning paths")
    parser.add_argument("--output-dir", "-o", default="results", help="Directory to save the evaluation results")
    parser.add_argument("--models", "-m", nargs="+", default=DEFAULT_MODEL_NAMES,
                        help="List of model names to evaluate (default: built-in list)")
    return parser.parse_args()

def main():
    args = parse_args()
    asyncio.run(evaluate_all_models(
        input_file=args.input,
        output_dir=args.output_dir,
        model_names=args.models
    ))

if __name__ == "__main__":
    main()

