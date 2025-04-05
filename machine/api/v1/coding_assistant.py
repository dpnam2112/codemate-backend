# Create coding session

# Problem: I'm building a LLM-powered programming teaching assistant that supports the learners to
# learn programming. in the UI there is a code editor (like leetcode, a problem statement, .etc)
#
# Two features that I want to implement:
# - give hints
# - fix codes
# 
# The assistant must not give the student a clear answer. Instead, guide them to achieve the final
# answer. design a prompt for that. 
# Design and implement FastAPI endpoints so that the client can call the AI agent.

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import openai
import json

from core.response.api_response import Ok
from core.settings import settings as env_settings

class HintRequest(BaseModel):
    problem_statement: str
    code_context: str

class FixCodeRequest(BaseModel):
    problem_statement: str
    code_context: str
    error_message: str

class LineHint(BaseModel):
    line: int
    hint: str

# Output Schemas
class HintOutput(BaseModel):
    global_hint: str
    line_hints: Optional[List[LineHint]] = None

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
{code_context}

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

    response = openai_client.beta.chat.completions.parse(
        model="gpt-4o-mini",  # Replace with your desired model
        messages=[{"role": "system", "content": prompt}],
        temperature=0.7,
        response_format=HintOutput
    )

    parsed = response.choices[0].message.parsed
    return Ok(data=parsed)

@router.post("/fix", response_model=Ok[FixOutput])
async def fix_code(request: FixCodeRequest):
    prompt = generate_prompt_for_fix(
        request.problem_statement,
        request.code_context,
        request.error_message
    )

    response = openai_client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": prompt}],
        temperature=0.7,
        response_format=FixOutput
    )
    parsed = response.choices[0].message.parsed
    return Ok(data=parsed)

