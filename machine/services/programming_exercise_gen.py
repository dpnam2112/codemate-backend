import json
from typing import Optional
from pydantic import BaseModel, ValidationError

from pydantic import BaseModel, Field
from core.settings import settings as env_settings
from litellm import completion

class TestCaseSchema(BaseModel):
    """
    Schema for test cases.
    'input' is the input of the program from stdin.
    'expected_output' is the expected output of the program, which is printed to stdout.
    """
    input: str = Field(
        ...,
        description="Input string provided to the program (from stdin).",
        examples=["([{}])"]
    )
    expected_output: str = Field(
        ...,
        description="Expected output string from the program (to stdout).",
        examples=["True"]
    )

class ProgrammingExerciseSchema(BaseModel):
    """
    Schema for a programming exercise.
    Contains problem description in HTML and a list of test cases.
    """
    problem_description: str = Field(
        ...,
        description="Content describing the programming problem. Do not include <html> or <body> tags.",
        examples=["<h3><strong>Problem: Valid Parentheses Checker</strong></h3><p>Check if brackets are valid.</p>"]
    )
    test_cases: list[TestCaseSchema] = Field(
        ...,
        description="List of test cases with input and expected output.",
        examples=[
            {"input": "([{}])", "expected_output": "True"},
            {"input": "([)]", "expected_output": "False"}
        ]
    )
    boilerplate_code: list["BoilerplateSchema"] = Field(
        ...,
        description="List of boilerplate code for different programming languages."
    )

class BoilerplateSchema(BaseModel):
    """
    Schema for boilerplate code for a given language.
    """
    judge0_lang_id: int = Field(
        ...,
        description=(
            "Language ID according to Judge0 enumeration:\n"
            "- 50: C\n"
            "- 54: C++\n"
            "- 62: Java\n"
            "- 71: Python 3\n"
        ),
    )
    code: str = Field(
        ...,
        description=(
            "Boilerplate code string for the given programming language. "
            "The program must contain a 'main' function to take input from stdin and print output to stdout."
        ),
        examples=[
            '''def is_valid_parentheses(s: str) -> bool:
    stack = []
    mapping = {")": "(", "}": "{", "]": "["}
    for char in s:
        if char in mapping:
            top_element = stack.pop() if stack else '#'
            if mapping[char] != top_element:
                return False
        else:
            stack.append(char)
    return not stack

def main():
    import sys
    # Read input from stdin
    s = sys.stdin.read().strip()
    print(is_valid_parentheses(s))

if __name__ == "__main__":
    main()'''
        ]
    )

class ProgrammingExerciseGenService:
    def __init__(
        self, llm_model_name: Optional[str] = None, api_key: Optional[str] = None
    ):
        """
        Initialize the service with the specified LLM model name.

        :param llm_model_name: Name of the LLM model to be used for generating programming
        exercises. This parameter is then passed into `litellm`.
        :param api_key: API key for the LLM model. This is used to authenticate requests.
        """
        self.llm_model_name = llm_model_name or "gemini/gemini-2.0-flash"
        self.api_key = api_key or env_settings.GEMINI_API_KEY

    def generate_programming_exercise(
        self, module_title: str, objectives: list[str]
    ) -> ProgrammingExerciseSchema:
        """
        Generate a programming exercise based on the module title and objectives.
        The response is structured according to the ProgrammingExerciseSchema.
        """
        # Construct the prompt
        prompt = (
            f"Create a programming exercise for the module titled '{module_title}'. "
            f"The exercise should help learners achieve the following objectives:\n"
        )
        for idx, obj in enumerate(objectives, start=1):
            prompt += f"{idx}. {obj}\n"
        prompt += (
            "\nProvide the problem description in HTML format and include a list of test cases. "
            "Each test case should have an 'input' and the corresponding 'expected_output'."
        )

        # Prepare messages for the chat completion
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an AI assistant that generates programming exercises. "
                    "Ensure the output strictly adheres to the specified JSON schema."
                ),
            },
            {"role": "user", "content": prompt},
        ]

        # Make the completion request with structured output
        response = completion(
            model=self.llm_model_name,
            messages=messages,
            api_key=self.api_key,
            response_format=ProgrammingExerciseSchema,
        )
        
        json_string = response.choices[0].message.content
        print(json_string)
        parsed_json = json.loads(json_string)
        return ProgrammingExerciseSchema.model_validate(parsed_json)

if __name__ == "__main__":
    # Sample inputs
    module_title = "Data Structures - Stacks"
    objectives = [
        "Understand stack operations (push, pop, peek)",
        "Implement a basic stack using arrays or lists",
        "Apply stack to solve real-world problems like balancing parentheses"
    ]

    # Initialize the service (uses GEMINI_API_KEY from env or fallback)
    service = ProgrammingExerciseGenService()

    print(f"Generating exercise for module: '{module_title}'\nObjectives:")
    for obj in objectives:
        print(f"- {obj}")
    print("\n--- Generating Programming Exercise ---\n")

    try:
        result: ProgrammingExerciseSchema = service.generate_programming_exercise(
            module_title, objectives
        )

        print("✅ Exercise generated successfully!\n")
        print(result.model_dump())

    except ValidationError as ve:
        print("❌ Validation Error:")
        print(ve.json(indent=2))
    except Exception as e:
        print("❌ Unexpected Error:")
        print(str(e))

