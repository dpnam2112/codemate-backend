import re

from typing import Optional, Tuple, List
from litellm import acompletion
from core.judge0 import get_language_name
from pydantic import BaseModel
from core.llm import LLMModelConfig
from core.settings import settings as env_settings
from core.logger import syslog
from machine.schemas.llm_issue_analysis import IssueAnalysisResponse
import json
import litellm

class SolutionResponse(BaseModel):
    """
    Schema for programming solution.
    """
    solution: str
    explanation: str

class EvaluationCriteria(BaseModel):
    name: str
    score: float
    comment: str

class LLMEvaluation(BaseModel):
    """
    Schema for Submission evaluation.
    """
    score: float
    max_score: float
    summary: str
    criteria: List[EvaluationCriteria]
    improvement_suggestions: List[str]

default_config = LLMModelConfig(model_name="gemini/gemini-2.0-flash", api_key=env_settings.GEMINI_API_KEY)

def strip_code_blocks(text: str) -> str:
    text = re.sub(r"```[\w+-]*\s*", "", text)  # handles ```python3, ```c++, etc.
    text = re.sub(r"```", "", text)            # in case closing ``` is still there
    return text.strip()

class CodeExerciseAssistantService:
    def __init__(
        self,
        llm_cfg: LLMModelConfig = default_config
    ):
        self.llm_cfg = llm_cfg
        self.api_key = llm_cfg.api_key

    async def generate_solution(
        self,
        initial_code: str,
        problem_description: str,
        language_id: int
    ) -> tuple[str, Optional[str]]:
        """
        Generate a solution for a coding exercise using LLM.
        
        Args:
            initial_code (str): The initial/boilerplate code
            problem_description (str): The problem description/requirements
            language_id (int): The Judge0 language ID
            
        Returns:
            tuple[str, Optional[str]]: A tuple containing the solution code and optional explanation
        """
        language_name = get_language_name(language_id)

        prompt = f"""You are a professional programming assistant helping students solve coding problems.

        Below is the problem statement, the programming language to be used, and the initial code scaffold. Your task is to complete the solution and explain your approach.

        ---

        **Your Task:**
        1. Complete the code so it solves the problem.
        2. Provide a brief explanation of your approach.
        3. Provide a brief explanation of your approach. Add helpful inline comments that explain the logic step-by-step, so that students can easily follow and learn from the code.

        **Guidelines:**
        - Keep the same function signature and input/output types.
        - Add clear and helpful comments in the code.
        - Follow best practices and ensure the code is clean and production-ready.
        - Keep the explanation short but informative.
        - DO NOT use code blocks (e.g., do *not* start with ```python3, ```java, ``cpp, .etc).
        - Assume you're writing inside a regular code editor without syntax highlighting.
        - Follow language-specific conventions. For example, in Java, the solution should include a `Main` class if required.
        - Use only {language_name}.
        - You MUST ADD educational and detailed comments that explain why certain steps are taken, not just what is being done. Explain clearly so that students can easily understand your solution.

        ---

        **Problem Description:**
        {problem_description}

        **Programming Language:** {language_name}

        **Initial Code:**
        ```{language_name.lower()}
        {initial_code}
        ```

        **Solution:**"""

        # Call the LLM with structured response
        response = await acompletion(
            model=self.llm_cfg.model_name,
            messages=[
                {
                    "role": "system",
                    "content": ""
                },
                {"role": "user", "content": prompt}
            ],
            temperature=self.llm_cfg.temperature,
            max_tokens=self.llm_cfg.max_tokens,
            api_key=self.llm_cfg.api_key,
            response_format=SolutionResponse
        )
        
        # Parse the structured response
        result = response.choices[0].message.content
        parsed_result = SolutionResponse.model_validate_json(result)
        cleaned_solution = strip_code_blocks(parsed_result.solution)
        
        return cleaned_solution, parsed_result.explanation

    async def analyze_learning_issues(
        self,
        code: str,
        course_title: str,
        course_objectives: str,
        exercise_title: str,
        exercise_description: str,
        current_issues: List[dict]
    ) -> Optional[IssueAnalysisResponse]:
        """Analyze learning issues from a code submission."""
        prompt_template = """
        You are an expert programming instructor tasked with analyzing a student's code submission to uncover conceptual or learning-related issues.

        ### Course Information
        - **Course Title**: {course_title}
        - **Learning Objectives**: {course_objectives}

        ### Exercise Details
        - **Exercise Title**: {exercise_title}
        - **Exercise Description**: {exercise_description}

        ### Student Submission
        ```{code}```

        ### Known Learning Issues (if any)
        {current_issues}

        ---

        ### Your Task

        Carefully review the student’s code and identify **new learning issues** that may indicate gaps in understanding. For each issue found, provide:

        1. **Issue Type**: Choose from categories such as `knowledge_gap`, `concept_misunderstanding`, `incomplete_application`, `logical_confusion`, or `syntax_dependency`.
        2. **Issue Description**: Clearly explain the problem and how it reflects a misunderstanding of specific programming concepts or course material.

        ---

        ### Evaluation Guidelines
        Follow these principles strictly when analyzing the student's code:
          - Review the existing learning issues. If in your analysis, students still have the same learning issues, just return EXACTLY those learning issues (both type and description) and your new analysis.
          - Focus on Conceptual Understanding: Judge how well the student understands the underlying concepts, such as loops, functions, data structures, algorithmic thinking, or language-specific paradigms.
          - Limit your analysis to what is **relevant to the course objectives**. If a concept is not taught or expected at this stage, do not raise it as an issue.
          - Only flag issues that are **demonstrably present** in the code. Avoid hypothetical or speculative problems.
          - Do not evaluate correctness, performance, or elegance of the code. Your job is to assess **learning**, not output.
          If the student uses an unconventional but valid approach, do not assume misunderstanding unless it clearly violates the intent of the exercise or shows conceptual flaws.
          - Frame your explanation in a way that would help the student grow—avoid harsh language. Emphasize **learning opportunities** over critique.
          - Limit to Learning-Relevant Issues: Do not comment on naming conventions, formatting, or best practices unless they explicitly reveal conceptual misunderstanding (e.g., misunderstanding function scope due to naming reuse).
        """

        response = await acompletion(
            model=self.llm_cfg.model_name,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert programming instructor analyzing student code submissions. Identify learning issues based on the submission evaluation and context."
                },
                {
                    "role": "user",
                    "content": prompt_template.format(
                        course_title=course_title,
                        course_objectives=course_objectives,
                        exercise_title=exercise_title,
                        exercise_description=exercise_description,
                        code=code,
                        current_issues=json.dumps(current_issues, indent=2)
                    )
                }
            ],
            api_key=self.api_key,
            response_format=IssueAnalysisResponse
        )
        
        analysis = response.choices[0].message.content
        return IssueAnalysisResponse.model_validate_json(analysis)

    async def evaluate_submission(
        self,
        code: str,
        problem_description: str,
        language_id: int,
        test_results: list[dict]
    ) -> Optional[LLMEvaluation]:
        """
        Evaluate a code submission using LLM.
        
        Args:
            code (str): The submitted code
            problem_description (str): The problem description
            language_id (int): The Judge0 language ID
            test_results (list[dict]): List of test case results
            
        Returns:
            Optional[LLMEvaluation]: The evaluation result
        """
        language_name = get_language_name(language_id)
        
        # Construct the evaluation prompt
        prompt = f"""You are an expert programming instructor. Please evaluate this student's code submission.

Problem Description:
{problem_description}

Submitted Code:
```{language_name.lower()}
{code}
```

Test Results:
{self._format_test_results(test_results)}

Please evaluate the code based on the following criteria (using a 10-point scale):
1. Code Correctness (3 points): Does the code solve the problem correctly?
2. Code Quality (2 points): Is the code well-structured, readable, and maintainable?
3. Algorithm Efficiency (2 points): Is the solution efficient in terms of time and space complexity?
4. Best Practices (2 points): Does the code follow language-specific best practices?
5. Error Handling (1 point): Does the code handle edge cases and potential errors?

Provide:
1. A numerical score (0-10)
2. A detailed evaluation for each criterion
3. Specific improvement suggestions
4. A summary of the overall evaluation

Format your response as a JSON object matching this schema:
{{
    "score": float,
    "max_score": 10.0,
    "summary": str,
    "criteria": [
        {{
            "name": str,
            "score": float,
            "comment": str
        }}
    ],
    "improvement_suggestions": [str]
}}"""

        try:
            # Call the LLM with structured response
            response = await acompletion(
                model=self.llm_cfg.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an AI assistant that evaluates programming submissions. Ensure the output strictly adheres to the specified JSON schema."
                    },
                    {"role": "user", "content": prompt}
                ],
                api_key=self.llm_cfg.api_key,
                response_format=LLMEvaluation
            )
            
            # Parse the structured response
            result = response.choices[0].message.content
            return LLMEvaluation.model_validate_json(result)
            
        except Exception as e:
            # Log the error and return None
            print(f"Error evaluating submission: {str(e)}")
            return None

    def _format_test_results(self, test_results: list[dict]) -> str:
        """Format test results for the prompt."""
        formatted = []
        for i, result in enumerate(test_results, 1):
            formatted.append(f"Test Case {i}:")
            formatted.append(f"  Status: {result['status']}")
            if result.get('stdout'):
                formatted.append(f"  Output: {result['stdout']}")
            if result.get('stderr'):
                formatted.append(f"  Error: {result['stderr']}")
            formatted.append("")
        return "\n".join(formatted)

