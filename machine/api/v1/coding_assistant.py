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
    optimize: bool = False

class FixCodeRequest(BaseModel):
    problem_statement: str
    code_context: str
    error_message: str

class LineHint(BaseModel):
    """
    Hint for a specific line in the code snippet.
    """
    line: int = Field(..., description="The line number in the code snippet.")
    hint: str = Field(..., description="The hint or suggestion for the specific line. start with HINT or SUGGESTION.")

# Output Schemas
class HintOutput(BaseModel):
    global_hint: str = Field(..., description="A general hint for the problem.")
    line_hints: list[LineHint] = Field(..., description="Hints for specific lines of code. Hints MUST be concise.")

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

Please think through the following steps (chain‑of‑thought), but do not include your full reasoning in the final output—only use it to arrive at your suggestions:

1. **Restate the Goal:**  In your own words, what is the code supposed to achieve?
2. **Identify Inputs & Outputs:**  What are the key inputs, expected outputs, and constraints?
3. **Step‑by‑Step Walkthrough:**  Go through the provided code logic line by line, noting any deviations from the intended behavior or potential edge‐cases.
4. **Pinpoint Logic Errors:**  Highlight specific locations where the code’s logic is incorrect or incomplete.
5. **Formulate Next Steps:**  Based on the above, decide on concrete, actionable steps the student can take to correct their logic and progress toward a working solution.

INSTRUCTIONS:
    - You MUST START your answers with 'HINT'.
    - Guide students with QUESTIONS. What do they need to do? What do they need to do next? What cases that they need to handle? .etc. 
    - Only give hints on functions/methods marked with TODO, or code section that students need to implement. Do not give hints on code sections that are part of starter code, e.g: main() function in C/C++, __main__ section in Python.
    - Guide them ONE STEP AT A TIME PER METHODS/FUNCTIONS. Give them time to think. DO NOT show them what to do all at once.
    - If there are hints in a function/method that students haven't resolved yet, do not give hints in that method/function.
    - If students are on the right track, just don't give hint to the code that the students are on the right track. Only give hints on section that they are in wrong track.


Once you have completed your internal reasoning, output **only** a valid JSON object in the provided format.
    """
    return prompt.strip()

def generate_prompt_for_optimization(
    code_context: str,
    problem_description: Optional[str] = None,
    inputs_description: Optional[str] = None,
    focus_lines: Optional[str] = None
) -> str:
    """
    Build a prompt that guides the model to reason step‑by‑step about performance,
    readability, and maintainability, then output only a JSON with analysis and optimizations.
    """
    pd_section = f"\n\nProblem description:\n{problem_description}" if problem_description else ""
    inp_section = f"\n\nTypical inputs:\n{inputs_description}" if inputs_description else ""
    lines_section = f"\n\nFocus on these lines:\n{focus_lines}" if focus_lines else ""
    
    prompt = f"""
You are an expert programming teaching assistant focused on code performance and quality. A student has written the following code:

{code_context}{pd_section}{inp_section}{lines_section}

Internally, think through these phases in order, but do **not** include your full reasoning in the output—use it to arrive at your recommendations:

1. **Clarify Goals & Constraints:**  
   - What is the code’s intended functionality?  
   - What are the performance goals (e.g., time complexity, memory usage)?  
2. **Analyze Algorithmic Complexity:**  
   - Identify the big‑O time and space complexity of key blocks.  
3. **Spot Hotspots & Bottlenecks:**  
   - Find loops, recursion, or data‑structure usage that could be optimized.  
4. **Assess Readability & Maintainability:**  
   - Note any code smells, duplication, or unclear abstractions.  
5. **Recommend Concrete Optimizations:**  
   - Propose algorithmic changes, data‑structure swaps, refactorings, or language‑specific improvements.

RULES:
    - Start your answer with SUGGESTION.
    - Only give suggestions on parts that need to be improved. E.g: If users haven't done anything,
      then you shouldn't give any answers.
    - Only give suggestions on functions/methods marked with TODO, or things that students need to implement. Do not give any suggestions on starter code.
    - If there is nothing needed to improve, just return nothing.

After your internal analysis, output **only** a valid JSON object in the provided schema.
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
async def get_hint(
    request: HintRequest
):
    if not request.optimize:
        prompt = generate_prompt_for_hint(
            request.problem_statement,
            request.code_context
        )
    else:
        prompt = generate_prompt_for_optimization(
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
    return Ok(data=HintOutput.model_validate_json(json_string))

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
