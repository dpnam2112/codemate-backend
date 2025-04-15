from typing import Optional
import litellm
from litellm import acompletion
from core.judge0 import get_language_name
from pydantic import BaseModel

class SolutionResponse(BaseModel):
    solution: str
    explanation: str

class CodeExerciseAssistantService:
    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        temperature: float = 0.7,
        max_tokens: int = 2000
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

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
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI assistant that generates programming solutions. Ensure the output strictly adheres to the specified JSON schema."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            response_format=SolutionResponse
        )
        
        # Parse the structured response
        result = response.choices[0].message.content
        parsed_result = SolutionResponse.model_validate_json(result)
        
        return parsed_result.solution, parsed_result.explanation
