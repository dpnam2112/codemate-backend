import json
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Optional
import openai
import litellm

from core.response.api_response import Ok
from core.settings import settings as env_settings

LLM_MODEL_NAME = "gemini/gemini-2.0-flash"

class HintRequest(BaseModel):
    problem_statement: str = Field(description="The problem statement that the user/student is trying to solve.")
    code_context: str = Field(description="The current solution code or code snippet the user/student is working on.")

class FixCodeRequest(BaseModel):
    problem_statement: str
    code_context: str
    error_message: str

class LineHint(BaseModel):
    """
    Hint for a specific line in the code snippet.
    """
    line: int = Field(..., description="The line number in the code snippet.")
    hint: str = Field(..., description="The hint or suggestion for the specific line.")

# Output Schemas
class HintOutput(BaseModel):
    global_hint: str = Field(..., description="A general hint for the problem.")
    line_hints: list[LineHint] = Field(..., description="Hints for specific lines of code.")

class FixOutput(BaseModel):
    fix_hint: str
    # Optionally, specific hints mapped by line number as string
    line_fix_hints: Optional[LineHint] = None

# Initialize the OpenAI client
openai_client = openai.OpenAI(api_key=env_settings.OPENAI_API_KEY)

def generate_prompt_for_hint(problem_statement: str, code_context: str, lines: Optional[str] = None) -> str:
    # If specific lines are provided, include that information in the prompt.
    prompt = f"""
You are an assistant for learning programming. A student is working on the following problem:
{problem_statement}

The student's current code is:
{code_context}

Based on the code, please suggest the next steps for the student to move toward a solution.
Please provide your answer as a JSON object with the provided format.
Ensure that the JSON is valid and that no additional text is included.
    """
    return prompt.strip()

def generate_prompt_for_fix(problem_statement: str, code_context: str, error_message: str) -> str:
    prompt = f"""
You are an assistant for learning programming. A student is working on the following problem:
{problem_statement}

The student's current code is:
{code_context}education

The code produced the following error:
{error_message}

Please provide your answer as a JSON object with the provided format.
Ensure that the JSON is valid and that no additional text is included.
    """
    return prompt.strip()

router = APIRouter(prefix="/coding-assistant", tags=["Coding assistants"])

@router.post("/hint", response_model=Ok[HintOutput])
async def get_hint(request: HintRequest):
    prompt = generate_prompt_for_hint(
        request.problem_statement,
        request.code_context
    )

    response = await litellm.acompletion(
        model=LLM_MODEL_NAME,
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": "help me"}],
        api_key=env_settings.GEMINI_API_KEY,
        response_format=HintOutput
    )
    json_string = response.choices[0].message.content
    parsed_json = json.loads(json_string)
    return Ok(data=HintOutput.model_validate(parsed_json))

@router.post("/fix", response_model=Ok[FixOutput])
async def fix_code(request: FixCodeRequest):
    prompt = generate_prompt_for_fix(
        request.problem_statement,
        request.code_context,
        request.error_message
    )

    response = await litellm.acompletion(
        model=LLM_MODEL_NAME,
        messages=[{"role": "system", "content": prompt}, {"role": "user"}],
        api_key=env_settings.GEMINI_API_KEY,
        response_format=FixOutput
    )

    json_string = response.choices[0].message.content
    parsed_json = json.loads(json_string)
    return Ok(data=FixOutput.model_validate(parsed_json))
