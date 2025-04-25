from typing import List
from core.response import Ok
from machine.models import *
from fastapi import APIRouter, Depends
from machine.controllers import *
from machine.providers import InternalProvider
from machine.schemas.requests.llm_code import *
from machine.schemas.responses.llm_code import *
from core.utils.auth_utils import verify_token
from fastapi.security import OAuth2PasswordBearer
from core.exceptions import NotFoundException, BadRequestException
from machine.services.workflows.ai_tool_provider import AIToolProvider, LLMModelName
import json
import re
import logging

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
router = APIRouter(prefix="/llm", tags=["llm"])
@router.post("/explain_code", response_model=Ok[List[CodeExplanation]])
async def explain_code(
    analysis_request: CodeAnalysisRequest,
    token: str = Depends(oauth2_scheme),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
):
    """
    API endpoint to analyze code and return results as an array with line, code and explanation.
    """
    # User authentication
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    
    user = await student_controller.student_repository.first(where_=[Student.id == user_id])
    if not user:
        user = await professor_controller.professor_repository.first(where_=[Professor.id == user_id])
        if not user:
            raise NotFoundException(message="You don't have permission to use this feature.")
    
    try:
        # Fixed temperature and max_tokens
        temperature = 0.2
        max_tokens = 2000
        
        # Split the input code into lines and keep track of line numbers
        code_lines = analysis_request.code.split('\n')
        total_lines = len(code_lines)
        
        # Create prompt in English with language parameter
        prompt = f"""Explain each line of the following {analysis_request.language} code and return the result as JSON with each line of code and its corresponding explanation.

```{analysis_request.language}
{analysis_request.code}
```

Requirements: Analyze each line of the above code and return the result EXACTLY in the following JSON format:
{{
  "explanations": [
    {{
      "line": 1,
      "code": "corresponding line of code",
      "explanation": "Detailed explanation of the line"
    }},
    ... and continue for ALL lines in the code
  ]
}}

IMPORTANT: Include ALL {total_lines} lines from the code in your response, even if they are empty lines or have no explanation needed. For lines that don't need explanation (like empty lines), include them with an empty explanation string.

Return ONLY the requested JSON structure, without any additional text."""

        question = QuestionRequest(
            content=prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Use AIToolProvider to create the LLM model
        ai_tool_provider = AIToolProvider()
        llm = ai_tool_provider.chat_model_factory(LLMModelName.GEMINI_PRO)
        
        # Set fixed parameters
        llm.temperature = temperature
        llm.max_output_tokens = max_tokens
        
        response = llm.invoke(question.content)
        raw_content = response.content
        
        # Initialize result with empty explanations for all lines
        formatted_result = []
        for i, line in enumerate(code_lines):
            formatted_result.append(CodeExplanation(
                line=i+1,
                code=line,
                explanation=""
            ))
        
        # Try to extract JSON from code blocks first
        json_pattern = r'```json\s*(.*?)\s*```'
        json_match = re.search(json_pattern, raw_content, re.DOTALL)
        
        parsed_data = None
        if json_match:
            json_str = json_match.group(1)
            try:
                parsed_data = json.loads(json_str)
            except json.JSONDecodeError:
                # Try another method
                pass
        
        # If regex extraction failed, try direct parsing
        if not parsed_data:
            try:
                # Remove non-JSON characters
                potential_json = raw_content.strip()
                parsed_data = json.loads(potential_json)
            except json.JSONDecodeError:
                # Try one more method with relaxed parsing
                try:
                    # Find all matches with format "line": number, "code": "...", "explanation": "..."
                    pattern = r'"line":\s*(\d+).*?"code":\s*"([^"]*)".*?"explanation":\s*"([^"]*)"'
                    matches = re.findall(pattern, raw_content, re.DOTALL)
                    
                    if matches:
                        explanation_dict = {}
                        for match in matches:
                            line_num, code, explanation = match
                            explanation_dict[int(line_num)] = {"code": code, "explanation": explanation}
                        
                        # Create a pseudo-parsed data structure
                        parsed_data = {"explanations": []}
                        for line_num in range(1, total_lines + 1):
                            if line_num in explanation_dict:
                                parsed_data["explanations"].append({
                                    "line": line_num,
                                    "code": explanation_dict[line_num]["code"],
                                    "explanation": explanation_dict[line_num]["explanation"]
                                })
                            else:
                                parsed_data["explanations"].append({
                                    "line": line_num,
                                    "code": code_lines[line_num - 1],
                                    "explanation": ""
                                })
                except Exception as ex:
                    logging.error(f"Manual extraction error: {str(ex)}")
                    parsed_data = None
        
        # Update the formatted result with explanations if we have parsed data
        if parsed_data and "explanations" in parsed_data:
            # Create a lookup of line numbers to explanations
            explanation_lookup = {}
            for item in parsed_data["explanations"]:
                line_num = item.get("line")
                if isinstance(line_num, int) and 1 <= line_num <= total_lines:
                    explanation_lookup[line_num] = item.get("explanation", "")
            
            # Update our formatted result with explanations where they exist
            for i in range(total_lines):
                line_num = i + 1
                if line_num in explanation_lookup:
                    formatted_result[i].explanation = explanation_lookup[line_num]
            
            return Ok(
                data=formatted_result,
                message="Code analysis completed successfully.",
                isSuccess=True
            )
        
        # If we couldn't parse the data properly, return our default result with empty explanations
        return Ok(
            data=formatted_result,
            message="Code analysis completed with partial results.",
            isSuccess=True
        )
    
    except Exception as e:
        logging.error(f"Code explanation error: {str(e)}")
        raise BadRequestException(message=f"Error in explain_code endpoint: {str(e)}")
