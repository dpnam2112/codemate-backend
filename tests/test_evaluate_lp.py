import pytest
import json
import csv
from pathlib import Path
from typing import List

from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.dataset import EvaluationDataset
from deepeval.models.base_model import DeepEvalBaseLLM

from tests.utils import build_course_context, build_llm_learning_path_output
from tests.model_factory import get_model_for_experiment
from .metrics import (
    get_goal_alignment_metric,
    get_explanation_quality_metric,
    get_ordering_logic_metric,
    get_module_appropriateness_metric,
)

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

@pytest.mark.asyncio
async def test_evaluate_all_models_batch():
    input_file = "evaluation/data/learning_paths_evaluation_20250426_1.json"
    output_file = "results_learning_path_eval_all_models.csv"

    model_names = ["gpt-4o-mini", "gpt-4.1-nano"]
    paths = load_learning_paths(input_file)
    test_cases = [build_test_case(p) for p in paths]

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["path_id", "goal", "model", "metric", "score", "reason"])
        writer.writeheader()

        for model_name in model_names:
            model = get_model_for_experiment(model_name)
            metrics = get_all_metrics(model)

            dataset = EvaluationDataset(test_cases=test_cases)
            results = dataset.evaluate(metrics=metrics)

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

    print(f"✅ All model results saved to {output_file}")

