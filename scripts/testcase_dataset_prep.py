# generate_testcases_from_json.py

import json
import asyncio
import argparse
from pathlib import Path
from tqdm import tqdm

from machine.services.programming_exercise_gen import ProgrammingExerciseGenService, TestCaseSchema
from core.settings import settings as env_settings

async def generate_testcase_for_problem(problem: dict, service: ProgrammingExerciseGenService, semaphore: asyncio.Semaphore):
    problem_desc = problem.get("problem_description")
    if not problem_desc:
        return None

    async with semaphore:
        try:
            testcases: list[TestCaseSchema] = await service.generate_testcases_only(problem_desc)
            generated_testcases = [
                {"input": tc.input, "expected_output": tc.expected_output}
                for tc in testcases
            ]

            # Merge back into problem
            return {
                "problem_description": problem_desc.strip(),
                "solutions": problem.get("solutions", []),
                "generated_testcases": generated_testcases
            }

        except Exception as e:
            print(f"Failed to generate testcases for a problem: {e}")
            return None

async def main(input_json: Path, output_json: Path, num_problems: int = None, batch_size: int = 5, llm_model_name: str = "gpt-4o-mini"):
    # Load JSON problems
    with open(input_json, "r", encoding="utf-8") as f:
        problems = json.load(f)

    if num_problems:
        problems = problems[:num_problems]

    if "gpt" in llm_model_name or "openai" in llm_model_name:
        service = ProgrammingExerciseGenService(llm_model_name=llm_model_name, api_key=env_settings.OPENAI_API_KEY)
    elif "gemini" in llm_model_name or "vertex" in llm_model_name:
        service = ProgrammingExerciseGenService(llm_model_name=llm_model_name, api_key=env_settings.GEMINI_API_KEY)
    else:
        raise ValueError(f"{llm_model_name} is not supported.")

    semaphore = asyncio.Semaphore(batch_size)

    tasks = [generate_testcase_for_problem(problem, service, semaphore) for problem in problems]

    dataset = []
    for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Generating testcases"):
        result = await f
        if result:
            dataset.append(result)

    output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    print(f"✅ Finished generating dataset with {len(dataset)} problems.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate testcases from raw JSON problems via LLM.")
    parser.add_argument("--input_json", type=Path, required=True, help="Input JSON file path")
    parser.add_argument("--output_json", type=Path, required=True, help="Output JSON file path")
    parser.add_argument("--num_problems", type=int, default=None, help="Number of problems to process")
    parser.add_argument("--batch_size", type=int, default=5, help="Max number of concurrent tasks")
    parser.add_argument("--llm_model_name", type=str, default="gpt-4o-mini", help="LLM model name used to generate testcases")

    args = parser.parse_args()

    asyncio.run(main(
        input_json=args.input_json,
        output_json=args.output_json,
        num_problems=args.num_problems,
        batch_size=args.batch_size,
        llm_model_name=args.llm_model_name
    ))

