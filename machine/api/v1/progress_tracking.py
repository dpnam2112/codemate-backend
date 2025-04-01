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
    Hello! You are an education assessment expert, and I need your help to evaluate a student’s learning progress in a detailed, systematic way based on a Rubric standard. I’d like you to create an assessment based on the information I provide below. This student has a specific learning goal and is working through a series of lessons. Your task is to analyze this data using up to three criteria: **Theoretical Knowledge**, **Coding Skills** (if applicable), and **Effort**, then provide a concise summary in English, formatted as a JSON object following a specific structure. I’ll provide a rubric for you to evaluate each section, and I also require a **Progress Review** (Strengths, Areas to Note) and **Advice** for the student. Let’s go through this step by step!

    ### Student Information:
    - **Name**: {student.fullname}
    - **Email**: {student.email}

    ### Learning Goal:
    "{student_goal}"  
    This is the target they need to achieve before the midterm exam.

    ### Lesson Data:
    {json.dumps(lessons, indent=2, ensure_ascii=False)}

    ### Analysis Criteria:
    Evaluate the student based on the following criteria, adapting to the course context using the lesson data (progress, time_spent, explain, status, objectives in modules, etc.):
    1. **Theoretical Knowledge**: Assess their understanding of theory based on progress in lessons related to theoretical concepts (e.g., algorithm complexity, software testing principles).
    2. **Coding Skills**: Only apply this criterion if the course involves coding exercises (e.g., implementing algorithms). If not applicable (e.g., a course like 'Testing Software'), replace it with a relevant practical skill (e.g., 'Practical Testing Skills') based on the goal and lesson objectives.
    3. **Effort**: Assess their dedication based on time spent (time_spent), the number of lessons started (status), and overall progress.

    ### Rubric for Each Section:
    #### 1. Situation:
    - **Excellent**: Fully and vividly describe the student’s learning context, including their name, course, and connection to the learning goal.
    - **Good**: Describe the context clearly, mentioning the course but lacking some personal details or vividness.
    - **Average**: Provide a vague description of the context, only generally mentioning learning without specifics.
    - **Poor**: Fail to describe or inaccurately describe the learning context.

    #### 2. Task:
    - **Excellent**: Restate the goal accurately and clearly, emphasizing the importance of achieving it before the midterm (e.g., 70% accuracy if specified).
    - **Good**: Restate the goal accurately but lack emphasis or midterm context.
    - **Average**: Restate the goal unclearly or with minor omissions.
    - **Poor**: Misstate or omit the goal.

    #### 3. Action:
    - **Excellent**: List actions in detail for each applicable criterion (Theoretical Knowledge, Coding Skills or alternative practical skill, Effort), based on lesson data (progress, time_spent, objectives), with specific examples (e.g., “Completed 82% of a lesson on testing principles”).
    - **Good**: List main actions per criterion but lack details like lesson titles or specific figures.
    - **Average**: Mention actions vaguely, without clear analysis per criterion.
    - **Poor**: Fail to mention or misdescribe actions.

    #### 4. Result:
    - **Excellent**: Accurately assess overall progress against the goal (e.g., 70% if specified), based on data and analyzed by applicable criteria, with a clear judgment (on track/needs effort/at risk) and reference to the current date (3/31/2025).
    - **Good**: Assess progress correctly but lack detail per criterion or time reference.
    - **Average**: Provide a vague assessment, not clearly tied to data or the goal.
    - **Poor**: Assess incorrectly or fail to provide a clear result.

    ### Implementation Guidelines:
    - **Situation**: Describe the learning context of {student.fullname}, e.g., “{student.fullname} is taking a course on software testing to prepare for the midterm” or “...on data structures and algorithms.”
    - **Task**: Restate the goal, e.g., “The task of {student.fullname} is to master software testing principles before the midterm” or “...to implement sorting algorithms with 70% accuracy.”
    - **Action**: Analyze actions per criterion, splitting them into separate fields:
      - **Theoretical Knowledge**: Based on progress in theory lessons (e.g., testing concepts or algorithm complexity).
      - **Coding Skills (or Alternative)**: If coding applies, evaluate it; if not, assess a practical skill like applying testing methods, based on objectives.
      - **Effort**: Based on time_spent and lessons started.
    - **Result**: Evaluate overall progress, e.g., “With X% progress as of 3/31/2025, {student.fullname} is on track for theoretical knowledge but needs effort in practical skills.”

    ### Additional Requirements:
    - **Progress Review**:
      - **Strengths**: Highlight standout points from the data (e.g., “The student excels in theoretical lessons”).
      - **Areas to Note**: Point out weaknesses or risks (e.g., “Limited progress in practical lessons”).
    - **Advice**: Provide specific suggestions split by criterion:
      - **Theoretical Knowledge**: Advice for theory improvement.
      - **Coding Skills (or Alternative)**: Advice for coding or practical skill improvement.
      - **Effort**: Advice for enhancing dedication.

    ### JSON Output Format:
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
          "situation": "string",
          "task": "string",
          "action": {{
            "theoretical_knowledge": "string",
            "coding_skills": "string (or practical skill if no coding)",
            "effort": "string"
          }},
          "result": "string"
        }},
        "progress_review": {{
          "strengths": "string",
          "areas_to_note": "string"
        }},
        "advice": {{
          "theoretical_knowledge": "string",
          "coding_skills": "string (or practical skill if no coding)",
          "effort": "string"
        }}
      }}
    }}
    Key Requirements:
    - Write all sections in English, concise yet detailed per the rubric.
    - Output the result as a valid JSON object matching the structure above.
    - Ensure no truncation and all fields are filled appropriately, adapting 'coding_skills' to a practical skill if coding isn’t required.
    Are you ready? Let’s start and give me a detailed, specific assessment tailored to the course context in the required JSON format!
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