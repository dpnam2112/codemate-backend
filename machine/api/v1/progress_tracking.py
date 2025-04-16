import os
from data.constant import *
from fastapi import APIRouter, Depends, Request, HTTPException
from dotenv import load_dotenv
from fastapi.security import OAuth2PasswordBearer
from machine.controllers import *
from machine.providers import InternalProvider
from core.utils.auth_utils import verify_token
from core.exceptions import *
from machine.models import *
from sqlalchemy.sql import func, and_, or_
from core.response import Ok
from typing import Dict, List
from utils.chunk_manager import ChunkingManager
import json
from datetime import timedelta
import re
from pydantic import BaseModel, Field
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


class AssessmentRequest(BaseModel):
    student_goal: str = Field(..., description="Learning goal of the student")
    lessons: List[Dict] = Field(..., description="List of lessons with progress data")
    
router = APIRouter(prefix="/progress_tracking", tags=["progress_tracking"])
# Initialize ChunkingManager with Gemini as the provider
chunking_manager = ChunkingManager(
        provider="gemini",
        gemini_model_name="gemini-2.0-flash-lite",
        max_tokens_per_chunk=15000,
        temperature=0.7,
        max_output_tokens=8000
    )
 
def generate_standard_prompt(student: Student, student_goal: str, lessons: list) -> str:
    """
    Generate a verbose, conversational prompt for the LLM to create a Rubric-Based Standard assessment in English,
    analyzing based on specific criteria (Theoretical Knowledge, Coding Skills if applicable, Effort), adaptable to courses with or without coding exercises,
    and formatted according to a specific JSON structure.
    """
    prompt = f"""
        Hello! You are an education assessment expert. I need your help evaluating a student's learning progress. 

        ### Student Information:
        - **Name**: {student.fullname}
        - **Email**: {student.email}

        ### Learning Goal:
        "{student_goal}"  
        This is the target they need to achieve before the midterm exam.

        ### Lesson Data:
        {json.dumps(lessons, indent=2, ensure_ascii=False)}

        ### FORMATTING REQUIREMENTS:
        - Present all content in list format with bullet points or numbering
        - Never use paragraphs - always use lists, bullets, or numbered points
        - Keep individual list items concise (1-2 sentences max)
        - Use hierarchical structure for clarity
        - Include bullet points (•) at the start of list items
        - Use numbered lists (1., 2., etc.) for sequential information

        ### Analysis Criteria:
        Evaluate the student based on these criteria:
        1. **Theoretical Knowledge**: Present assessment as bullet points
        2. **Coding Skills** (if applicable): Structure as a list of capabilities
        3. **Effort**: Break down into measurable bullet points

        ### Output Format
        The response must follow this structure (in English):
        ```json
        {{
        "student_assessment": {{
            "student_info": {{
            "name": "{student.fullname}",
            "email": "{student.email}"
            }},
            "learning_goal": "{student_goal}",
            "assessment_date": "2025-03-31",
            "assessment_summary": {{
            "situation": "• Context point 1\\n• Context point 2",
            "task": "• Goal point 1\\n• Goal point 2",
            "action": {{
                "theoretical_knowledge": "• Action 1\\n• Action 2\\n• Action 3",
                "coding_skills": "• Skill 1\\n• Skill 2\\n• Skill 3",
                "effort": "• Effort point 1\\n• Effort point 2\\n• Effort point 3"
            }},
            "result": "• Result 1\\n• Result 2\\n• Result 3"
            }},
            "progress_review": {{
            "strengths": "• Strength 1\\n• Strength 2\\n• Strength 3",
            "areas_to_note": "• Area 1\\n• Area 2\\n• Area 3"
            }},
            "advice": {{
            "theoretical_knowledge": "• Advice 1\\n• Advice 2\\n• Advice 3",
            "coding_skills": "• Coding advice 1\\n• Coding advice 2\\n• Coding advice 3",
            "effort": "• Effort advice 1\\n• Effort advice 2\\n• Effort advice 3"
            }}
        }}
        }}
        """
    return prompt


@router.post("/student/{courseId}/assessment")
async def get_assessment(
    courseId: str,
    request: AssessmentRequest,
    token: str = Depends(oauth2_scheme),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    course_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
):
    print("Logging", request)
    # Verify token and extract user_id
    payload = verify_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise UnauthorizedException("Invalid token")
    
    # Fetch student
    student = await student_controller.student_repository.first(where_=[Student.id == user_id])
    if not student:
        raise NotFoundException("Student not found")
    
    # Fetch course
    course = await course_controller.courses_repository.first(where_=[Courses.id == courseId])
    if not course:
        raise NotFoundException("Course not found")

    
    # Extract student_goal and lessons
    student_goal = request.student_goal
    lessons = request.lessons
    
    if not student_goal or not lessons:
        raise HTTPException(status_code=400, detail="Missing student_goal or lessons in request body")
    
    # Generate prompt for LLM
    prompt = generate_standard_prompt(student, student_goal, lessons)
    
    # Call LLM API to get STAR assessment
    try:
        system_message = "You are a helpful AI assistant tasked with assessing student progress."
        assessment = chunking_manager.call_llm_api(prompt, system_message)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate assessment: {str(e)}")
    
    return Ok(
        data=assessment,
        message="Student learning assessment generated successfully"
    )
    
class UpdateTimeSpentRequest(BaseModel):
    time_spent: str = Field(..., description="Time spent on the lesson in HH:MM:SS format")

# This should be a regular function, not async
def parse_time_spent(new_time_spent_str):
    """
    Parse a string in HH:MM:SS format to a timedelta
    
    Args:
        new_time_spent_str: String in HH:MM:SS format
    
    Returns:
        timedelta object
    """
    hours, minutes, seconds = map(int, new_time_spent_str.split(':'))
    
    return timedelta(hours=hours, minutes=minutes, seconds=seconds)

def add_time_spent(existing_time_spent, new_time_spent_str):
    """
    Add a new time spent value (in HH:MM:SS format) to an existing timedelta
    
    Args:
        existing_time_spent: Existing timedelta object or None
        new_time_spent_str: String in HH:MM:SS format
    
    Returns:
        Updated timedelta
    """
    if existing_time_spent is None:
        existing_time_spent = timedelta(0)
    
    new_time_delta = parse_time_spent(new_time_spent_str)
    
    return existing_time_spent + new_time_delta

@router.post("/student/recommend_lessons/{recommend_lesson_id}/time_spent")
async def update_time_spent(
    recommend_lesson_id: str,
    request: UpdateTimeSpentRequest,
    token: str = Depends(oauth2_scheme),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    recommend_lesson_controller: RecommendLessonsController = Depends(InternalProvider().get_recommendlessons_controller),
):
    payload = verify_token(token)
    user_id = payload.get("sub")
    
    if not user_id:
        raise UnauthorizedException("Invalid token")
        
    student = await student_controller.student_repository.first(where_=[Student.id == user_id])
    if not student:
        raise NotFoundException("Student not found")
        
    time_spent_str = request.time_spent
    if not time_spent_str:
        raise HTTPException(status_code=400, detail="Missing time_spent in request body")
    
    try:
        lesson = await recommend_lesson_controller.recommend_lessons_repository.first(
            where_=[RecommendLessons.id == recommend_lesson_id]
        )
        if not lesson:
            raise NotFoundException("Lesson not found")
                
        updated_time_spent = add_time_spent(lesson.time_spent, time_spent_str)
        
        await recommend_lesson_controller.recommend_lessons_repository.update(
            where_=[RecommendLessons.id == recommend_lesson_id],
            attributes={
                "time_spent": updated_time_spent  
            },
            commit=True
        )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update time spent: {str(e)}")
        
    return Ok( data={
        "recommend_lesson_id": recommend_lesson_id,
        "updated_time_spent": str(updated_time_spent) 
    },
        message="Time spent updated successfully"
    )