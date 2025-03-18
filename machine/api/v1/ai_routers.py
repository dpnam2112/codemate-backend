import json
import os
import time
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends
from core.response import Ok
from core.exceptions import *
from machine.models import *
from machine.controllers import *
from machine.providers.internal import InternalProvider
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer
from uuid import UUID
from core.utils.auth_utils import verify_token
from ...schemas.requests.ai import GenerateLearningPathRequest
from dotenv import load_dotenv
from utils.chunk_manager import ChunkingManager
load_dotenv()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
router = APIRouter(prefix="/ai", tags=["ai"])

@router.post("/generate-learning-path")
async def generate_learning_path(
    request: GenerateLearningPathRequest,
    token: str = Depends(oauth2_scheme),
    courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    learning_path_controller: LearningPathsController = Depends(InternalProvider().get_learningpaths_controller),
    modules_controller: ModulesController = Depends(InternalProvider().get_modules_controller),
    recommend_lessons_controller: RecommendLessonsController = Depends(InternalProvider().get_recommendlessons_controller),
    documents_controller: DocumentsController = Depends(InternalProvider().get_documents_controller),
    extracted_text_controller: ExtractedTextController = Depends(InternalProvider().get_extracted_text_controller),
    lessons_controller: LessonsController = Depends(InternalProvider().get_lessons_controller),
):
    """
    Generate a personalized learning path for a student based on their goals and course content.
    
    Args:
        request: Contains course_id and student's learning goal
        Other parameters: Controllers for different database models
        
    Returns:
        Dict containing the generated learning path details
    """
    # Verify token
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    
    student = await student_controller.student_repository.first(where_=[Student.id == user_id])
    if not student:
        raise NotFoundException(message="Your account is not allowed to access this feature.")
    
    if not request.goal or not request.course_id:
        raise BadRequestException(message="Please provide course_id and goal.")
    
    # Fetch course details
    course = await courses_controller.courses_repository.first(where_=[Courses.id == request.course_id])
    if not course:
        raise NotFoundException(message="Course not found.")
    
    # Fetch professor information
    professor = await professor_controller.professor_repository.first(where_=[Professor.id == course.professor_id])
    if not professor:
        raise NotFoundException(message="Professor information not found.")
    
    # Fetch all lessons for the course
    lessons = await lessons_controller.lessons_repository.get_many(where_=[Lessons.course_id == request.course_id])
    if not lessons:
        raise NotFoundException(message="No lessons found for this course.")
    
    # Prepare data structure for all lessons with their documents and extracted text
    lessons_data = []
    for lesson in lessons:
        # Get documents for this lesson
        documents = await documents_controller.documents_repository.get_many(where_=[Documents.lesson_id == lesson.id])
        
        documents_data = []
        for document in documents:
            # Get extracted text for each document
            extracted = await extracted_text_controller.extracted_text_repository.first(
                where_=[ExtractedText.document_id == document.id]
            )
            
            # Only include documents with extracted text
            if extracted and extracted.extracted_content:
                documents_data.append({
                    "name": document.name,
                    "type": document.type,
                    "description": document.description,
                    "extracted_content": extracted.extracted_content
                })
        
        lessons_data.append({
            "id": str(lesson.id),
            "title": lesson.title,
            "description": lesson.description,
            "order": lesson.order,
            "learning_outcomes": lesson.learning_outcomes if lesson.learning_outcomes else [],
            "documents": documents_data
        })
    
    # Sort lessons by their order
    lessons_data.sort(key=lambda x: x["order"])
    
    # Calculate approximate timeframe for the learning path
    start_date = datetime.now()
    end_date = course.end_date if course.end_date else (start_date + timedelta(days=90))
    
    # Get API key from environment variables
    gemini_api_key = os.getenv("GOOGLE_GENAI_API_KEY")
    
    # Define the function to generate prompts for chunks
    def generate_chunk_prompt(lessons_chunk, chunk_index, total_chunks):
        # Add context about chunking to help the model understand
        chunk_context = f""" 
        # Learning Path Generation Task - Chunk {chunk_index + 1} of {total_chunks}
        
        ## Chunking Context
        You are analyzing a subset of lessons ({len(lessons_chunk)} out of total lessons) for a course. 
        This is chunk {chunk_index + 1} of {total_chunks} being processed separately due to size limitations.
        Focus only on the lessons provided in this chunk when making recommendations.
        """
        
        # Precompute values to simplify nested expressions
        start_date_str = course.start_date.isoformat() if course.start_date else start_date.isoformat()
        end_date_str = course.end_date.isoformat() if course.end_date else end_date.isoformat()
        learning_outcomes_str = json.dumps(course.learning_outcomes if course.learning_outcomes else [])
        lessons_chunk_str = json.dumps(lessons_chunk, indent=2)
        
        # Precompute deeply nested values
        student_name = student.name
        course_name = course.name
        student_mssv = student.mssv
        course_id = course.courseID
        professor_name = professor.fullname
        student_goal = request.goal
        lessons_chunk_count = len(lessons_chunk)
        lessons_chunk_details = json.dumps(lessons_chunk, indent=2)
        
        prompt = f"""
        {chunk_context}
        
        ## Student Information
        - Student Name: {student_name}
        - Student ID: {student_mssv}
        - Course: {course_name} (ID: {course_id})
        - Professor: {professor_name}
        - Student's Learning Goal: "{student_goal}"
        
        ## Course Information
        - Start Date: {start_date_str}
        - End Date: {end_date_str}
        - Learning Outcomes: {learning_outcomes_str}
        
        ## Available Lessons in This Chunk
        This chunk contains {lessons_chunk_count} lessons. Here is detailed information about each lesson:
        {lessons_chunk_details}
        
        ## Task Requirements
        Please analyze ONLY these lessons and recommend any that will help the student achieve their stated goal. 
        For each recommended lesson, provide:
        1. Recommended content that explains what to focus on
        2. An explanation of why this content is important for the student's goal
        3. 2-3 modules per lesson that break down the key concepts to master
        
        ## Timeline Estimation Task (REQUIRED)
        You MUST estimate and include a realistic start date, end date, and duration notes for each recommended lesson.
        
        Base your estimation on:
        1. The complexity of the recommended lessons
        2. The student's learning goal
        3. The overall course timeline ({start_date_str} to {end_date_str})
        4. The number and complexity of recommended lessons
        
        The timeline should:
        - Allow reasonable time for learning and practice
        - Consider the complexity of the material
        - Fit within the course's overall timeline
        - Be realistic for a student to achieve their goal
        - Consider the estimated hours needed for each lesson
        
        ## Output Format
        Your response MUST be in the following JSON format and MUST include all fields shown below:
        {{
        "learning_path_start_date": "{start_date_str}",
        "learning_path_end_date": "{end_date_str}",
        "learning_path_objective": "Brief description of the learning path objective based on the student's goal of {student_goal}",
        "learning_path_progress": 0,
        "student_id": "{student_mssv}",
        "course_id": "{course_id}",
        "recommend_lessons": [
            {{
            "lesson_id": "Lesson ID",
            "recommended_content": "Detailed explanation of what to focus on in this lesson...",
            "explain": "Explanation of why this content is important for the student's goal...",
            "status": "new",
            "progress": 0,
            "bookmark": false,
            "start_date": "YYYY-MM-DD", 
            "end_date": "YYYY-MM-DD",
            "duration_notes": "Brief explanation of how this timeline was determined based on lesson complexity",
            "number_of_modules": 2
            }}
        ],
        "modules": [
            {{
            "title": "Module Title",
            "objectives": ["Learning objective 1", "Learning objective 2", "Learning objective 3"],
            }}
        ]
        }}
        
        IMPORTANT: 
        1. The JSON MUST include ALL fields in the format above. 
        2. Each recommended lesson should have 2-3 corresponding modules in the modules array.
        3. The "lesson_id" in recommend_lessons array should match the original lesson id.
        4. Initial status should be "new" and progress should be 0 for all lessons.
        5. The learning path should include a meaningful objective based on the student's goal.
        """
        
        return prompt
    
    # Define function to extract results from response
    def extract_results(response):
        """
        Extract learning path data from the AI response.
        
        Args:
            response: The AI model response (dictionary or string)
            
        Returns:
            A dictionary with the learning path data structure
        """
        if isinstance(response, str):
            try:
                if "```json" in response:
                    json_content = response.split("```json")[1].split("```")[0].strip()
                    response_json = json.loads(json_content)
                else:
                    response_json = json.loads(response)
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON: {e}")
                return {}  # Return empty dict to allow merging
        else:
            response_json = response
        
        required_keys = ["learning_path_start_date", "learning_path_end_date", 
                        "learning_path_objective", "recommend_lessons", "modules"]
        
        for key in required_keys:
            if key not in response_json:
                print(f"Missing required key in response: {key}")
                return {}  # Return empty dict if structure is invalid
        
        return {
            "learning_path_start_date": response_json["learning_path_start_date"],
            "learning_path_end_date": response_json["learning_path_end_date"],
            "learning_path_objective": response_json["learning_path_objective"],
            "learning_path_progress": response_json.get("learning_path_progress", 0),
            "student_id": str(student.id),
            "course_id": str(request.course_id),
            "recommend_lessons": response_json.get("recommend_lessons", []),
            "modules": response_json.get("modules", [])
        }
    # Then modify how you process the results after chunking
    chunking_manager = ChunkingManager(
    provider="gemini",
    gemini_model_name="gemini-2.0-flash-lite",
    max_tokens_per_chunk=25000,
    temperature=0.7,
    max_output_tokens=4000
)
        # Process data in chunks
    chunked_results = chunking_manager.process_in_chunks(
            data=lessons_data,
            prompt_generator=generate_chunk_prompt,
            result_extractor=extract_results,
            token_estimation_field="documents",  # Use this field for token estimation
            system_message="You are an expert educational AI assistant that creates personalized learning paths for students."
        )

    if chunked_results:
        
        # If chunked_results is a string, try to parse it as JSON
        if isinstance(chunked_results, str):
            try:
                chunked_results = json.loads(chunked_results)
            except json.JSONDecodeError:
                raise ApplicationException(message="Failed to parse chunked_results as JSON.")
        
        learning_path_attributes = {
            "start_date": datetime.strptime(chunked_results["learning_path_start_date"], '%Y-%m-%d').date(),
            "end_date": datetime.strptime(chunked_results["learning_path_end_date"], '%Y-%m-%d').date(),
            "objective": request.goal,
            "student_id": str(student.id),
            "course_id": str(request.course_id),
            "llm_response": chunked_results
        }

        # Create learning path
        add_learning_path = await learning_path_controller.learning_paths_repository.create(attributes=learning_path_attributes, commit=True)

        if add_learning_path:
            recommend_lesson_attributes_list = []
            
            # First, validate the data structure and prepare recommend_lesson attributes
            for recommend_lesson in chunked_results["recommend_lessons"]:
                # If recommend_lesson is a string, try to parse it as JSON
                if isinstance(recommend_lesson, str):
                    try:
                        recommend_lesson = json.loads(recommend_lesson)
                    except json.JSONDecodeError:
                        raise ApplicationException(message=f"Failed to parse recommend_lesson {recommend_lesson['lesson_id']} as JSON.")

                recommend_lesson_attributes = {
                    "learning_path_id": add_learning_path.id,
                    "lesson_id": str(recommend_lesson["lesson_id"]),
                    "recommended_content": recommend_lesson["recommended_content"],
                    "explain": recommend_lesson["explain"],
                    "start_date":recommend_lesson["start_date"],
                    "end_date": recommend_lesson["end_date"],
                    "duration_notes": recommend_lesson["duration_notes"]
                }
                recommend_lesson_attributes_list.append(recommend_lesson_attributes)

            # Create all recommend lessons in bulk
            created_recommend_lessons = await recommend_lessons_controller.recommend_lessons_repository.create_many(
                attributes_list=recommend_lesson_attributes_list, commit=True
            )

            # Ensure that we successfully created the recommend lessons
            if not created_recommend_lessons:
                raise ApplicationException(message="Failed to create recommend lessons.")

            module_attributes_list = assign_recommend_lesson_id(chunked_results["modules"], chunked_results["recommend_lessons"], created_recommend_lessons)
            

            # Create all modules in bulk
            created_modules = await modules_controller.modules_repository.create_many(
                attributes_list=module_attributes_list, commit=True
            )
            
            if created_modules:
                created_recommend_lessons_response = [
                    {
                        "lesson_id": str(recommend_lesson.lesson_id),
                        "recommended_content": recommend_lesson.recommended_content,
                        "explain": recommend_lesson.explain,
                        "status": recommend_lesson.status,
                        "progress": recommend_lesson.progress,
                        "bookmark": recommend_lesson.bookmark,
                        "start_date": str(recommend_lesson.start_date),
                        "end_date": str(recommend_lesson.end_date),
                        "duration_notes": recommend_lesson.duration_notes,
                    }
                    for recommend_lesson in created_recommend_lessons
                ]
                
                created_modules_response = [
                    {
                        "recommend_lesson_id": str(module.recommend_lesson_id),
                        "title": module.title,
                        "objectives": module.objectives,
                        "last_accessed": module.last_accessed
                    }
                    for module in created_modules
                ]
                
                create_response = {
                    "learning_path_id": str(add_learning_path.id),
                    "learning_path_start_date": str(add_learning_path.start_date),
                    "learning_path_end_date": str(add_learning_path.end_date),
                    "learning_path_objective": add_learning_path.objective,
                    "learning_path_progress": add_learning_path.progress,
                    "student_id": str(add_learning_path.student_id),
                    "course_id": str(add_learning_path.course_id),
                    "recommend_lessons": created_recommend_lessons_response,
                    "modules": created_modules_response
                }
                return Ok(create_response, message="Learning path generated successfully")
        return Ok(chunked_results)
    else:
        raise ApplicationException(message="Failed to generate recommendations")

# Helper function 

def assign_recommend_lesson_id(modules, recommend_lessons, created_recommend_lessons):
    current_lesson_index = 0 
    created_lesson_index = 0 
    modules_processed = 0  

    for module in modules:
        recommend_lesson = recommend_lessons[current_lesson_index]
        number_of_modules = recommend_lesson["number_of_modules"]

        module["recommend_lesson_id"] = created_recommend_lessons[created_lesson_index].id

        modules_processed += 1

        if modules_processed >= number_of_modules:
            current_lesson_index += 1
            created_lesson_index += 1
            modules_processed = 0 

    return modules


@router.get("/generate-student-goals/{course_id}")
async def generate_student_goals(
    course_id: UUID,
    token: str = Depends(oauth2_scheme),
    courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    lessons_controller: LessonsController = Depends(InternalProvider().get_lessons_controller),
    documents_controller: DocumentsController = Depends(InternalProvider().get_documents_controller),
    extracted_text_controller: ExtractedTextController = Depends(InternalProvider().get_extracted_text_controller),
):
    """
    Generate potential learning goals for a student based on course content.
    
    Args:
        request: Contains course_id
        Other parameters: Controllers for different database models
        
    Returns:
        Dict containing suggested learning goals
    """
    # Verify token
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    
    student = await student_controller.student_repository.first(where_=[Student.id == user_id])
    if not student:
        raise NotFoundException(message="Your account is not allowed to access this feature.")
    
    if not course_id:
        raise BadRequestException(message="Please provide course_id.")
    
    # Fetch course details
    course = await courses_controller.courses_repository.first(where_=[Courses.id == course_id])
    if not course:
        raise NotFoundException(message="Course not found.")
    
    # Fetch professor information
    professor = await professor_controller.professor_repository.first(where_=[Professor.id == course.professor_id])
    if not professor:
        raise NotFoundException(message="Professor information not found.")
    
    # Fetch all lessons for the course (just a sample to understand the course scope)
    lessons = await lessons_controller.lessons_repository.get_many(where_=[Lessons.course_id == course_id])
    if not lessons:
        raise NotFoundException(message="No lessons found for this course.")
    
    # Prepare data structure for course overview
    course_data = {
        "id": str(course.id),
        "name": course.name,
        "courseID": course.courseID,
        "learning_outcomes": course.learning_outcomes if course.learning_outcomes else [],
        "lessons": []
    }
    
    # Add just lesson titles and descriptions (not full content)
    for lesson in lessons:
        course_data["lessons"].append({
            "title": lesson.title,
            "description": lesson.description,
            "learning_outcomes": lesson.learning_outcomes if lesson.learning_outcomes else []
        })
    
    # Initialize the ChunkingManager (for consistency, though we may not need chunking here)
    chunking_manager = ChunkingManager(
        provider="gemini",
        gemini_model_name="gemini-1.5-pro",
        temperature=0.7,
        max_output_tokens=4000
    )
    
    # Create a prompt for goal generation
    
    prompt = f"""
        # Student Goal Generation Task

        ## Student Information
        - Student Name: {student.name}
        - Course: {course.name} (ID: {course.courseID})
        - Professor: {professor.fullname}

        ## Course Information
        - Learning Outcomes: {json.dumps(course.learning_outcomes if course.learning_outcomes else [])}

        ## Course Lessons Overview
        {json.dumps(course_data["lessons"], indent=2)}

        ## Task Requirements
        Based on the course information, lessons overview, and the student's proficiency level (Struggling, Average, Advanced):

        1. Generate personalized learning goals for EACH proficiency level (Struggling, Average, Advanced).
        2. Create at least 2 goals and maximum 3 goals for each proficiency level.
        3. The final output should have at least 6 goals and maximum 9 goals total across all proficiency levels.
        4. Each goal should be specific, measurable, achievable, relevant, and time-bound (SMART).
        5. IMPORTANT: Each goal statement MUST be less than 200 letters in length.
        6. Consider the student's proficiency level when generating goals:
        - **Struggling Students:** Goals should focus on building foundational knowledge, improving basic skills, and increasing confidence.
        - **Average Students:** Goals should aim to deepen understanding, enhance critical thinking, and refine existing skills.
        - **Advanced Students:** Goals should focus on advanced applications, pushing boundaries, and mastering complex concepts.
        7. Include a brief explanation of how achieving this goal would benefit the student.
        8. Consider both practical applications and academic growth when suggesting goals.
        9. For each goal, list the key lesson titles that relate to that goal.

        ## Output Format
        Provide your response in the following JSON format (REQUIRED!! YOU MUST FOLLOW THIS FORMAT):

        {{
        "suggested_goals": [
            {{
            "proficiency_level": "Struggling",
            "goal": "Specific learning goal statement (MUST BE UNDER 200 LETTERS)",
            "explanation": "Brief explanation of why this goal is valuable",
            "key_lessons": ["Lesson 1 title", "Lesson 2 title"]
            }},
            {{
            "proficiency_level": "Struggling",
            "goal": "Different learning goal statement (MUST BE UNDER 200 LETTERS)",
            "explanation": "Brief explanation of why this goal is valuable",
            "key_lessons": ["Lesson 1 title", "Lesson 2 title"]
            }},
            {{
            "proficiency_level": "Average",
            "goal": "Specific learning goal statement (MUST BE UNDER 200 LETTERS)",
            "explanation": "Brief explanation of why this goal is valuable",
            "key_lessons": ["Lesson 1 title", "Lesson 2 title"]
            }},
            {{
            "proficiency_level": "Average",
            "goal": "Different learning goal statement (MUST BE UNDER 200 LETTERS)",
            "explanation": "Brief explanation of why this goal is valuable",
            "key_lessons": ["Lesson 1 title", "Lesson 2 title"]
            }},
            {{
            "proficiency_level": "Advanced",
            "goal": "Specific learning goal statement (MUST BE UNDER 200 LETTERS)",
            "explanation": "Brief explanation of why this goal is valuable",
            "key_lessons": ["Lesson 1 title", "Lesson 2 title"]
            }},
            {{
            "proficiency_level": "Advanced",
            "goal": "Different learning goal statement (MUST BE UNDER 200 LETTERS)",
            "explanation": "Brief explanation of why this goal is valuable",
            "key_lessons": ["Lesson 1 title", "Lesson 2 title"]
            }}
        ]
        }}
        """
    
    system_message = "You are an expert educational AI assistant that helps students define effective learning goals."
    
    try:
        # Call the LLM API (no chunking needed for this simpler request)
        response = chunking_manager.call_llm_api(prompt, system_message, override_provider="gemini")
        
        # Extract and validate the response
        if isinstance(response, dict) and "suggested_goals" in response:
            return Ok(response)
        else:
            raise ApplicationException(message="Failed to generate valid student goals")
            
    except Exception as e:
        print(f"Error generating student goals: {str(e)}")
        raise ApplicationException(message=f"Failed to generate student goals: {str(e)}")