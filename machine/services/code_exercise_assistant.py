from typing import Optional, Tuple
from litellm import acompletion
from core.judge0 import get_language_name
from pydantic import BaseModel
from machine.schemas.programming_submission import LLMEvaluation
from core.llm import LLMModelConfig
from core.settings import settings as env_settings
from core.logger import syslog

class SolutionResponse(BaseModel):
    solution: str
    explanation: str

default_config = LLMModelConfig(model_name="gemini/gemini-2.0-flash", api_key=env_settings.GEMINI_API_KEY)

class CodeExerciseAssistantService:
    def __init__(
        self,
        llm_cfg: LLMModelConfig = default_config
    ):
        self.llm_cfg = llm_cfg

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

        # Construct the prompt
        prompt = f"""You are an expert programming assistant. Please help solve this programming problem.

Problem Description:
{problem_description}

Initial Code:
```{language_name.lower()}
{initial_code}
```

Please provide:
1. A complete solution that satisfies the requirements
2. A brief explanation of the solution approach

Requirements:
- Write the solution in {language_name}
- Maintain the same function signature and input/output types
- Include comments for clarity
- Ensure the code is production-ready and follows best practices 
- Keep the explanation concise but informative

Solution:"""

        

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
        
        return parsed_result.solution, parsed_result.explanation

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
                temperature=self.llm_cfg.temperature,
                max_tokens=self.llm_cfg.max_tokens,
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

