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
from ...schemas.requests.ai import GenerateLearningPathRequest,GenerateQuizRequest
from machine.schemas.requests.llm_code import *
from machine.schemas.responses.llm_code import *
from dotenv import load_dotenv
from utils.chunk_manager import ChunkingManager
from machine.services.workflows.ai_tool_provider import AIToolProvider, LLMModelName
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
    student_courses_controller: StudentCoursesController = Depends(InternalProvider().get_studentcourses_controller),
    recommend_documents_controller: RecommendDocumentsController = Depends(InternalProvider().get_recommenddocuments_controller),
):
    """
    Generate a personalized learning path for a student based on their goals and course content,
    or regenerate it based on issues_summary if an existing path exists.
    
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
        documents = await documents_controller.documents_repository.get_many(where_=[Documents.lesson_id == lesson.id])
        documents_data = []
        for document in documents:
            extracted = await extracted_text_controller.extracted_text_repository.first(
                where_=[ExtractedText.document_id == document.id]
            )
            if extracted and extracted.extracted_content:
                documents_data.append({
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
    
    lessons_data.sort(key=lambda x: x["order"])
    
    # Calculate approximate timeframe for the learning path
    start_date = datetime.now()
    end_date = course.end_date if course.end_date else (start_date + timedelta(days=90))
    
    # Check if learning path exists for this student and course
    existing_learning_path = await learning_path_controller.learning_paths_repository.first(
        where_=[LearningPaths.student_id == student.id, LearningPaths.course_id == request.course_id]
    )
    
    # Fetch issues summary from student_courses table
    student_course = await student_courses_controller.student_courses_repository.first(
        where_=[StudentCourses.student_id == user_id, StudentCourses.course_id == request.course_id]
    )
    issues_summary = student_course.issues_summary if student_course and student_course.issues_summary else None
    
    # Define prompt generator based on whether we're regenerating or creating anew

    def generate_chunk_prompt(lessons_chunk, chunk_index, total_chunks, context):
        """
        Generate a prompt for a new learning path with context.
        """
        chunk_context = f"""
        # Learning Path Generation Task - Chunk {chunk_index + 1} of {total_chunks}
        
        ## Chunking Context
        You are analyzing a subset of lessons ({len(lessons_chunk)} out of total lessons) for a course.
        This is chunk {chunk_index + 1} of {total_chunks} being processed separately due to size limitations.
        Focus only on the lessons provided in this chunk when making recommendations, but ensure your recommendations align with the overall course timeline and the student's goal timeline.
        """
        
        prompt = f"""
        {chunk_context}
        
        ## Student Information
        - Student Name: {student.name}
        - Student ID: {student.mssv}
        - Course: {course.name} (ID: {course.courseID})
        - Professor: {professor.fullname}
        - Student's Learning Goal: "{context['goal']}"
        
        ## Course Information
        - Start Date: {context['course_start_date']}
        - End Date: {context['course_end_date']}
        - Learning Outcomes: {json.dumps(course.learning_outcomes if course.learning_outcomes else [])}
        
        ## Available Lessons in This Chunk
        This chunk contains {len(lessons_chunk)} lessons:
        {json.dumps(lessons_chunk, indent=2)}
        
        ## Task Requirements
        Analyze ONLY the lessons in this chunk and recommend those that will help the student achieve their stated goal ("{context['goal']}"). The goal may be short-term (e.g., "Master queue and stack in 2 weeks") or long-term (e.g., "Master Python and score 7+ by course end"). Your recommendations must:

        1. **Adapt to Goal Timeline:**
            - Identify the timeline implied by the student's goal (short-term or long-term).
            - If short-term, limit the number of recommended lessons to fit within the goal's timeline.
            - If long-term, ensure recommendations cover the full scope of the goal within the course timeline ({context['course_start_date']} to {context['course_end_date']}).
            - Only recommend lessons relevant to the goal's focus.

        2. **Ensure Sequential Order:**
            - Assign an "order" to each recommended lesson based on its importance and relevance to the goal.
            - Ensure "start_date" and "end_date" of recommended lessons are sequential:
                - The "end_date" of one lesson must be on or before the "start_date" of the next lesson in the sequence.
                - The sequence must fit within the goal timeline (if short-term) or course timeline (if long-term).

        3. **Provide Detailed Recommendations:**
            - For each recommended lesson:
                - "recommended_content": Explain what to focus on in this lesson to achieve the goal.
                - "explain": Justify why this lesson is critical for the goal.
                - Include 2-3 modules per lesson to break down key concepts.

        ## Timeline Estimation Task (REQUIRED)
        Estimate a realistic "start_date", "end_date", and "duration_notes" for each recommended lesson based on:
        1. The complexity of the lesson content.
        2. The student's goal timeline (short-term or long-term).
        3. The overall course timeline ({context['course_start_date']} to {context['course_end_date']}).
        4. The number and complexity of recommended lessons in this chunk.
        5. Sequential dependency: Ensure each lesson’s timeline follows the previous one’s "end_date".

        ## Reading Material Requirements
        For the "reading_material" field in each module:
        1. "theoryContent" must be comprehensive:
            - At least 3 detailed paragraphs in "description".
            - At least 2 examples with "codeSnippet" (if applicable) and explanations.
        2. "references" must include:
            - At least 3 valid, relevant sources (academic + practical mix).
        3. "practicalGuide" must include:
            - 4-5 detailed steps.
            - At least 3 common errors with solutions.

        ## Output Format
        Your response MUST be in the following JSON format and MUST include all fields shown below:
        {{
            "learning_path_start_date": "{start_date.isoformat()}",
            "learning_path_end_date": "{end_date.isoformat()}",
            "learning_path_objective": "Description of the learning path objective based on '{request.goal}'",
            "learning_path_progress": 0,
            "student_id": "{student.mssv}",
            "course_id": "{course.courseID}",
            "recommend_lessons": [
                {{
                    "lesson_id": "Lesson ID",
                    "recommended_content": "What to focus on in this lesson...",
                    "explain": "Why this lesson supports the goal...",
                    "status": "new",
                    "progress": 0,
                    "bookmark": false,
                    "start_date": "YYYY-MM-DD",
                    "end_date": "YYYY-MM-DD",
                    "duration_notes": "How timeline was determined based on complexity and goal...",
                    "number_of_modules": 2,
                    "order": "Integer (1, 2, 3...) based on importance/relevance to goal"
                }}
            ],
            "modules": [
                {{
                    "title": "Module Title",
                    "objectives": ["Objective 1", "Objective 2", "Objective 3"],
                    "reading_material": {{
                        "id": "Unique ID",
                        "name": "Reading material name",
                        "theoryContent": [
                            {{
                                "title": "Section title",
                                "prerequisites": ["Prerequisite 1", "Prerequisite 2"],
                                "description": [
                                    "Paragraph 1 - detailed",
                                    "Paragraph 2 - detailed",
                                    "Paragraph 3 - detailed"
                                ],
                                "examples": [
                                    {{
                                        "title": "Example 1",
                                        "codeSnippet": "// Code example\\nfunction example() {{ return 'sample'; }}",
                                        "explanation": "How this illustrates the concept"
                                    }},
                                    {{
                                        "title": "Example 2",
                                        "codeSnippet": null,
                                        "explanation": "Conceptual explanation"
                                    }}
                                ]
                            }}
                        ],
                        "practicalGuide": [
                            {{
                                "title": "Guide title",
                                "steps": [
                                    "Step 1 - detailed",
                                    "Step 2 - detailed",
                                    "Step 3 - detailed",
                                    "Step 4 - detailed",
                                    "Step 5 - detailed"
                                ],
                                "commonErrors": [
                                    "Error 1 - solution",
                                    "Error 2 - solution",
                                    "Error 3 - solution"
                                ]
                            }}
                        ],
                        "references": [
                            {{
                                "title": "Academic reference",
                                "link": "https://example.com/academic",
                                "description": "Relevance to topic"
                            }},
                            {{
                                "title": "Industry reference",
                                "link": "https://example.com/industry",
                                "description": "Practical relevance"
                            }},
                            {{
                                "title": "Practical reference",
                                "link": "https://example.com/practical",
                                "description": "Hands-on relevance"
                            }}
                        ],
                        "summaryAndReview": {{
                            "keyPoints": ["Point 1", "Point 2", "Point 3", "Point 4", "Point 5"],
                            "reviewQuestions": [
                                {{
                                    "id": "Q1",
                                    "question": "Review question 1",
                                    "answer": "Answer 1",
                                    "maxscore": 10,
                                    "score": null,
                                    "inputUser": null
                                }},
                                {{
                                    "id": "Q2",
                                    "question": "Review question 2",
                                    "answer": "Answer 2",
                                    "maxscore": 10,
                                    "score": null,
                                    "inputUser": null
                                }}
                            ]
                        }}
                    }}
                }}
            ]
        }}
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
                return {}
        else:
            response_json = response
        
        required_keys = ["learning_path_start_date", "learning_path_end_date", 
                        "learning_path_objective", "recommend_lessons", "modules"]
        
        for key in required_keys:
            if key not in response_json:
                print(f"Missing required key in response: {key}")
                return {}
        
        return {
            "learning_path_start_date": response_json["learning_path_start_date"],
            "learning_path_end_date": response_json["learning_path_end_date"],
            "learning_path_objective": response_json["learning_path_objective"],
            "learning_path_progress": response_json.get("learning_path_progress", 0),
            "student_id": str(student.id),
            "course_id": str(request.course_id),
            "recommend_lessons": response_json["recommend_lessons"],
            "modules": response_json["modules"]
        }
    
    chunking_manager = ChunkingManager(
        provider="gemini",
        gemini_model_name="gemini-2.0-flash-lite",
        max_tokens_per_chunk=15000,
        temperature=0.7,
        max_output_tokens=8000
    )

    context = {
        "goal": request.goal,
        "course_start_date": course.start_date.isoformat() if course.start_date else start_date.isoformat(),
        "course_end_date": course.end_date.isoformat() if course.end_date else end_date.isoformat()
    }

    chunked_results = chunking_manager.process_in_chunks(
        data=lessons_data,
        prompt_generator=lambda chunk, idx, total, ctx: generate_chunk_prompt(chunk, idx, total, ctx),
        result_extractor=extract_results,
        result_combiner=combine_learning_path_results,
        context=context,
        token_estimation_field="documents",
        system_message="You are an expert educational AI assistant that creates personalized learning paths."
    )
    
    if chunked_results:
        print(chunked_results)
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
            "llm_response": chunked_results,
        }
        
        add_learning_path = await learning_path_controller.learning_paths_repository.create(
            attributes=learning_path_attributes, commit=True
        )
        
        if add_learning_path:
            recommend_lesson_attributes_list = []
            for recommend_lesson in chunked_results["recommend_lessons"]:
                if isinstance(recommend_lesson, str):
                    try:
                        recommend_lesson = json.loads(recommend_lesson)
                    except json.JSONDecodeError:
                        raise ApplicationException(message=f"Failed to parse recommend_lesson {recommend_lesson.get('lesson_id', 'Unknown')} as JSON.")
                
                recommend_lesson_attributes = {
                    "learning_path_id": add_learning_path.id,
                    "lesson_id": str(recommend_lesson["lesson_id"]),
                    "recommended_content": recommend_lesson["recommended_content"],
                    "explain": recommend_lesson["explain"],
                    "start_date": recommend_lesson["start_date"],
                    "end_date": recommend_lesson["end_date"],
                    "duration_notes": recommend_lesson["duration_notes"],
                    "order": recommend_lesson["order"],
                }
                recommend_lesson_attributes_list.append(recommend_lesson_attributes)
            
            created_recommend_lessons = await recommend_lessons_controller.recommend_lessons_repository.create_many(
                attributes_list=recommend_lesson_attributes_list, commit=True
            )
            
            if not created_recommend_lessons:
                raise ApplicationException(message="Failed to create recommend lessons.")
            
            # Assuming assign_recommend_lesson_id is a helper function you have
            module_attributes_list = []
            recommend_documents_attributes_list = []

            for i, module_data in enumerate(chunked_results["modules"]):
                if isinstance(module_data, str):
                    try:
                        module_data = json.loads(module_data)
                    except json.JSONDecodeError:
                        raise ApplicationException(message=f"Failed to parse module {module_data.get('title', 'Unknown')} as JSON.")
                
                # Extract reading_material
                reading_material = module_data.pop("reading_material")  # Remove from module_data
                
                # Prepare module attributes without reading_material
                module_attr = {
                    "recommend_lesson_id": None,  # This will be assigned by assign_recommend_lesson_id
                    "title": module_data["title"],
                    "objectives": module_data["objectives"]
                    # Any other fields needed for the module
                }
                
                module_attributes_list.append(module_attr)
                if isinstance(reading_material, str):
                    try:
                        reading_material = json.loads(reading_material) 
                    except json.JSONDecodeError:
                        raise ApplicationException(message=f"Invalid JSON format for reading_material: {reading_material}")

                # Store reading_material for later
                recommend_documents_attributes_list.append({
                    "module_id": None,  # Will be filled in after modules are created
                    "content": reading_material
                })

            # Now assign recommend_lesson_id to the modules
            module_attributes_list = assign_recommend_lesson_id(
                module_attributes_list, chunked_results["recommend_lessons"], created_recommend_lessons
            )

            # Create modules without reading_material
            created_modules = await modules_controller.modules_repository.create_many(
                attributes_list=module_attributes_list, commit=True
            )

            if created_modules:
                # Now link the modules to the recommend_documents
                for i, module in enumerate(created_modules):
                    recommend_documents_attributes_list[i]["module_id"] = module.id
                
                created_recommend_documents = await recommend_documents_controller.recommend_documents_repository.create_many(
                    attributes_list=recommend_documents_attributes_list, commit=True
                )
                
                if not created_recommend_documents:
                    raise ApplicationException(message="Failed to create recommend documents.")
                
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
                
                created_recommend_documents_response = [
                    {
                        "id": str(doc.id),
                        "module_id": str(doc.module_id),
                        "content": doc.content if isinstance(doc.content, str) else json.dumps(doc.content)
                    }
                    for doc in created_recommend_documents
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
                    "modules": created_modules_response,
                    "recommend_documents": created_recommend_documents_response
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


def combine_learning_path_results(chunk_results: List[Dict]) -> Dict:
    combined_result = {
        "learning_path_start_date": None,
        "learning_path_end_date": None,
        "learning_path_objective": None,
        "learning_path_progress": 0,
        "student_id": None,
        "course_id": None,
        "recommend_lessons": [],
        "modules": []
    }
    
    for i, result in enumerate(chunk_results):
        if i == 0:
            for key in ["learning_path_start_date", "learning_path_end_date",
                       "learning_path_objective", "student_id", "course_id"]:
                combined_result[key] = result[key]
        
        combined_result["recommend_lessons"].extend(result["recommend_lessons"])
        combined_result["modules"].extend(result["modules"])
    
    combined_result["recommend_lessons"].sort(key=lambda x: x["order"])
    
    # Ensure consistent date type (use datetime.date)
    current_date = datetime.strptime(combined_result["learning_path_start_date"], '%Y-%m-%d').date()
    for lesson in combined_result["recommend_lessons"]:
        lesson_start = datetime.strptime(lesson["start_date"], "%Y-%m-%d").date()
        lesson_end = datetime.strptime(lesson["end_date"], "%Y-%m-%d").date()
        lesson["start_date"] = lesson_start.strftime("%Y-%m-%d")
        lesson["end_date"] = lesson_end.strftime("%Y-%m-%d")
        current_date = lesson_end + timedelta(days=1)
    
    end_date = datetime.strptime(combined_result["learning_path_end_date"], '%Y-%m-%d').date()
    if current_date > end_date:
        combined_result["learning_path_end_date"] = current_date.strftime("%Y-%m-%d")
    
    return combined_result
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
        - Student Name: {student.fullname}
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
    
@router.post("/generate-quiz")
async def generate_quiz(
    request: GenerateQuizRequest,
    token: str = Depends(oauth2_scheme),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    modules_controller: ModulesController = Depends(InternalProvider().get_modules_controller),
    recommend_lessons_controller: RecommendLessonsController = Depends(InternalProvider().get_recommendlessons_controller),
    lessons_controller: LessonsController = Depends(InternalProvider().get_lessons_controller),
    documents_controller: DocumentsController = Depends(InternalProvider().get_documents_controller),
    extracted_text_controller: ExtractedTextController = Depends(InternalProvider().get_extracted_text_controller),
    recommend_quizzes_controller: RecommendQuizzesController = Depends(InternalProvider().get_recommend_quizzes_controller),
    recommend_quiz_questions_controller: RecommendQuizQuestionController = Depends(InternalProvider().get_recommend_quiz_question_controller),
):
    """
    Generate a quiz based on a recommended lesson.
    
    Args:
        request: Contains recommend_lesson_id
        Other parameters: Controllers for different database models
        
    Returns:
        Dict containing the generated quiz details
    """
    # Verify token
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    
    student = await student_controller.student_repository.first(where_=[Student.id == user_id])
    if not student:
        raise NotFoundException(message="Your account is not allowed to access this feature.")
    
    if not request.module_id:
        raise BadRequestException(message="Please provide recommend_lesson_id.")
    
    # Fetch module details
    module = await modules_controller.modules_repository.first(where_=[Modules.id == request.module_id])
    if not module:
        raise NotFoundException(message="Module not found")
    
    # Fetch recommended lesson details
    recommend_lesson = await recommend_lessons_controller.recommend_lessons_repository.first(
        where_=[RecommendLessons.id == module.recommend_lesson_id]
    )
    if not recommend_lesson:
        raise NotFoundException(message="Recommended lesson not found.")
    
    # Fetch the original lesson
    lesson = await lessons_controller.lessons_repository.first(
        where_=[Lessons.id == recommend_lesson.lesson_id]
    )
    if not lesson:
        raise NotFoundException(message="Original lesson not found.")
    
    # Get documents for this lesson
    documents = await documents_controller.documents_repository.get_many(
        where_=[Documents.lesson_id == lesson.id]
    )
    if not documents:
        raise NotFoundException(message="No documents found for this lesson.")
    
    # Prepare data structure with lesson details and its documents and extracted text
    lesson_data = {
        "id": str(lesson.id),
        "title": lesson.title,
        "description": lesson.description,
        "order": lesson.order,
        "learning_outcomes": lesson.learning_outcomes if lesson.learning_outcomes else [],
        "documents": []
    }
    
    for document in documents:
        # Get extracted text for each document
        extracted = await extracted_text_controller.extracted_text_repository.first(
            where_=[ExtractedText.document_id == document.id]
        )
        
        # Only include documents with extracted text
        if extracted and extracted.extracted_content:
            lesson_data["documents"].append({
                "id": str(document.id),
                "name": document.name,
                "type": document.type,
                "description": document.description,
                "extracted_content": extracted.extracted_content
            })
    
    # Get recommended content for extra context
    recommended_content = recommend_lesson.recommended_content
    explanation = recommend_lesson.explain
    module_data = {
        "id": str(module.id),
        "title": module.title,
        "objectives": module.objectives if module.objectives else [],
    }
    # Get API key from environment variables
    gemini_api_key = os.getenv("GOOGLE_GENAI_API_KEY")
    
    # Define the prompt for quiz generation
    prompt = f"""
    ## Quiz Generation Task
    
    ## Student Information
    - Student is learning about: "{lesson.title}"
    - Recommended focus areas: "{recommended_content}"
    
    ## Module Information
    - Module Title: {module.title}
    - Module Objectives: {json.dumps(module.objectives if module.objectives else [])}
    
    ## Lesson Information
    - Lesson Title: {lesson.title}
    - Lesson Description: {lesson.description}
    - Learning Outcomes: {json.dumps(lesson.learning_outcomes if lesson.learning_outcomes else [])}
    
    ## Documents Content
    {json.dumps([doc for doc in lesson_data["documents"]], indent=2)}
    
    ## Task Requirements
    Generate a comprehensive quiz that primarily tests understanding of the module objectives. The quiz should:
    1. Focus specifically on assessing the module objectives first and foremost
    2. Align with the recommended content areas as a secondary priority
    3. Cover key concepts and important details from the lesson materials
    4. Include questions of varying difficulty levels (easy, medium, hard)
    5. Include clear explanations for each answer
    
    ## Output Format
    Your response MUST be in the following JSON format:
    {{
        "quiz_title": "Title based on the lesson content",
        "description": "Brief description of what this quiz covers",
        "estimated_completion_time": "Time in minutes it would take to complete type number(e.g., 10)",
        "max_score": 70,
        "questions": [
            {{
                "question_text": "The question text goes here?",
                "question_type": "single_choice", 
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct_answer": ["The correct option here"],
                "difficulty": "easy", 
                "explanation": "Detailed explanation of why this is the correct answer",
                "points": 10
            }},
            {{
                "question_text": "The question text goes here?",
                "question_type": "multiple_choice", 
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct_answer": "The correct option here",
                "difficulty": "hard", 
                "explanation": "Detailed explanation of why this is the correct answer",
                "points": 10
            }},
            {{
                "question_text": "True/False question text goes here?",
                "question_type": "true_false",
                "options": ["True", "False"],
                "correct_answer": "True or False",
                "difficulty": "medium", 
                "explanation": "Explanation of why this is true or false",
                "points": 5
            }}
        ]
    }}
    
    IMPORTANT REQUIREMENTS:
    1. Generate at least 10 but no more than 15 questions
    2. Include a mix of single_choice, multiple_choice, and true_false question types
    3. For single_choice questions have only one correct answer among the four provided options (A, B, C, D).
    4. For multiple_choice questions may have more than one correct answer, and the user must select all correct options from the four provided choices (A, B, C, D).
    5. For true/false questions, options should be exactly ["True", "False"]
    6. The sum of all question points should be 100
    7. Each question must have a detailed explanation for the correct answer
    8. Make sure correct_answer exactly matches one of the options
    9. Every question must have a difficulty level of "easy", "medium", or "hard"
    10. All correct_answer values must be provided as arrays, even for single answers
    11. The quiz content should primarily assess the module objectives
    12. Secondary focus should be on the recommended content areas
    13. Ensure each question clearly relates to at least one module objective
    """
    
    # Initialize Genai client and generate quiz
    try:
        question = QuestionRequest(
            content=prompt,
            temperature=0.3,
            max_tokens= 3000
        )
        
        # Use AIToolProvider to create the LLM model
        ai_tool_provider = AIToolProvider()
        llm = ai_tool_provider.chat_model_factory(LLMModelName.GEMINI_PRO)
        
        # Set fixed parameters
        llm.temperature = 0.3
        llm.max_output_tokens = 2000
        
        response = llm.invoke(question.content)

        if not response:
            raise ApplicationException(message="Failed to generate quiz content")
        
        # Extract the quiz content from response
        response_text = response.content
        
        try:
            if "```json" in response_text:
                json_content = response_text.split("```json")[1].split("```")[0].strip()
                quiz_data = json.loads(json_content)
            else:
                quiz_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON from response: {e}")
            raise ApplicationException(message="Failed to parse quiz content as JSON")
        
        # Validate quiz data structure
        required_keys = ["quiz_title", "description", "max_score", "questions"]
        for key in required_keys:
            if key not in quiz_data:
                raise ApplicationException(message=f"Generated quiz is missing required field: {key}")
        
        # # Create quiz record
        quiz_attributes = {
            "name": quiz_data["quiz_title"],
            "description": quiz_data["description"],
            "status": "new",
            "time_limit": quiz_data["estimated_completion_time"],
            "max_score": quiz_data["max_score"],
            "module_id": module.id,
        }
        
        created_quiz = await recommend_quizzes_controller.recommend_quizzes_repository.create(attributes=quiz_attributes, commit=True)
        
        if not created_quiz:
            raise ApplicationException(message="Failed to create quiz")
        
        # # Create quiz questions
        question_attributes_list = []
        for question in quiz_data["questions"]:
            question_attributes = {
                "quiz_id": created_quiz.id,
                "question_text": question["question_text"],
                "question_type": question["question_type"],
                "options": question["options"],
                "correct_answer": question["correct_answer"],
                "difficulty": question["difficulty"],
                "explanation": question["explanation"],
                "points": question["points"]
            }
            question_attributes_list.append(question_attributes)
        
        created_questions = await recommend_quiz_questions_controller.recommend_quiz_question_repository.create_many(
            attributes_list=question_attributes_list, commit=True
        )
        
        if not created_questions:
            raise ApplicationException(message="Failed to create quiz questions")
        
        # # Format the response
        quiz_response = {
            "quiz_id": str(created_quiz.id),
            "name": created_quiz.name,
            "description": created_quiz.description,
            "time_limit": created_quiz.time_limit,
            "max_score": created_quiz.max_score,
            "module_id": str(created_quiz.module_id),
            "questions": [
                {
                    "id": str(question.id),
                    "question_text": question.question_text,
                    "question_type": question.question_type,
                    "options": question.options,
                    "correct_answer": question.correct_answer,
                    "difficulty": question.difficulty,
                    "explanation": question.explanation,
                    "points": question.points,

                }
                for question in created_questions
            ]
        }
        
        return Ok(quiz_response, message="Quiz generated successfully")
        
    except Exception as e:
        print(f"Error generating quiz: {str(e)}")
        raise ApplicationException(message=f"Failed to generate quiz: {str(e)}")
    
    # if existing_learning_path and issues_summary:
    #     old_response = existing_learning_path.llm_response
    #     version = existing_learning_path.version + 1
        
    #     old_recommend_lessons = await learning_path_controller.get_recommended_lessons_by_learning_path_id(existing_learning_path.id)
        
    #     def generate_chunk_prompt(lessons_chunk, chunk_index, total_chunks):
    #         """
    #         Generate a prompt for regenerating the learning path based on old response and issues.
    #         """
    #         if isinstance(old_response, str):
    #             old_response_json = json.loads(old_response)
    #         else:
    #             old_response_json = old_response
                
    #         if isinstance(issues_summary, str):
    #             issues_summary_json = json.loads(issues_summary)
    #         else:
    #             issues_summary_json = issues_summary
                
    #         chunk_context = f"""
    #         # Learning Path Regeneration Task - Chunk {chunk_index + 1} of {total_chunks} (Version {version})
            
    #         ## Chunking Context
    #         You are regenerating a personalized learning path based on a previous version and identified issues.
    #         This is chunk {chunk_index + 1} of {total_chunks}, containing {len(lessons_chunk)} lessons.
    #         Focus only on the lessons provided in this chunk when making recommendations.
    #         """
            
    #         old_path_context = f"""
    #         ## Previous Learning Path (Version {version - 1})
    #         Below is the previous learning path response:
    #         {json.dumps(old_response_json, indent=2)}
            
    #         This learning path was used as the basis for the student's progress, but issues were identified that need to be addressed.
    #         """
            
    #         issues_context = f"""
    #         ## Issues Summary (Last Updated: {issues_summary_json.get('last_updated', 'Unknown')})
    #         The student encountered the following issues in the previous learning path (Total Issues: {issues_summary_json.get('total_issues_count', 0)}):
    #         ### Common Issues
    #         {json.dumps(issues_summary_json.get('common_issues', []), indent=2)}
            
    #         ### Issue Trends
    #         {json.dumps(issues_summary_json.get('issue_trends', {}), indent=2)}
            
    #         These issues indicate areas where the student struggled, such as concept misunderstandings or quiz failures.
    #         """
            
    #         lessons_chunk_str = json.dumps(lessons_chunk, indent=2)
            
    #         prompt = f"""
    #         {chunk_context}
            
    #         {old_path_context}
            
    #         {issues_context}
            
    #         ## Student Information
    #         - Student Name: {student.name}
    #         - Student ID: {student.mssv}
    #         - Course: {course.name} (ID: {course.courseID})
    #         - Professor: {professor.fullname}
    #         - Student's Learning Goal: "{request.goal}"
            
    #         ## Course Information
    #         - Start Date: {course.start_date.isoformat() if course.start_date else start_date.isoformat()}
    #         - End Date: {course.end_date.isoformat() if course.end_date else end_date.isoformat()}
    #         - Learning Outcomes: {json.dumps(course.learning_outcomes if course.learning_outcomes else [])}
            
    #         ## Available Lessons in This Chunk
    #         This chunk contains {len(lessons_chunk)} lessons:
    #         {lessons_chunk_str}
            
    #         Old information of recommending lessons and modules:
    #         {old_recommend_lessons}
            
    #         ## Task Requirements
    #         Regenerate the learning path for this chunk by:
    #         1. Analyzing the previous learning path and the issues summary.
    #         2. Recommending lessons from this chunk that address the identified issues (e.g., revisit lessons tied to "related_lessons" or "related_modules", they contains ids of old recommend lessons and old modules).
    #         3. Adjusting the content focus to correct misunderstandings or reinforce weak areas (e.g., UML diagrams, agile methodologies).
    #         4. Providing new or updated modules to target the most frequent or increasing issues.

    #         For each recommended lesson, provide:
    #         1. Recommended content (tailored to address specific issues)
    #         2. An explanation of why this content helps resolve the issues and supports the student's goal
    #         3. 2-3 modules per lesson with detailed breakdowns
            
    #         ## Timeline Estimation Task (REQUIRED)
    #         You MUST estimate and include a realistic start date, end date, and duration notes for each recommended lesson.
    #         Base your estimation on:
    #         1. The complexity of the recommended lessons
    #         2. The student's past struggles (e.g., frequency of issues)
    #         3. The overall course timeline ({course.start_date.isoformat() if course.start_date else start_date.isoformat()} to {course.end_date.isoformat() if course.end_date else end_date.isoformat()})
    #         4. The number and complexity of recommended lessons
            
    #         ## Reading Material Requirements
    #         For the "reading_material" field in each module:
    #         1. The theoryContent section must be comprehensive and detailed, with:
    #         - At least 3 paragraphs in each description section
    #         - At least 2 examples for each theory content section where applicable
    #         - codeSnippet must contain actual illustrative code when relevant
    #         2. All references must be:
    #         - Valid and reliable sources
    #         - Directly relevant to the specific module topic
    #         - Include a mix of academic and practical resources where appropriate
    #         - At least 3 references per module
    #         3. The practical guide section should include:
    #         - At least 4-5 detailed steps for each guide
    #         - At least 3 common errors with explanations
            
    #         ## Output Format
    #         Your response MUST be in the following JSON format and MUST include all fields shown below:
    #         {{
    #             "learning_path_start_date": "{start_date.isoformat()}",
    #             "learning_path_end_date": "{end_date.isoformat()}",
    #             "learning_path_objective": "Updated objective based on the student's goal of '{request.goal}' and resolution of identified issues",
    #             "learning_path_progress": 0,
    #             "student_id": "{student.mssv}",
    #             "course_id": "{course.courseID}",
    #             "recommend_lessons": [
    #                 {{
    #                     "lesson_id": "Lesson ID",
    #                     "recommended_content": "Detailed explanation of what to focus on in this lesson to address specific issues...",
    #                     "explain": "Explanation of why this content is important for resolving issues and achieving the student's goal...",
    #                     "status": "new",
    #                     "progress": 0,
    #                     "bookmark": false,
    #                     "start_date": "YYYY-MM-DD",
    #                     "end_date": "YYYY-MM-DD",
    #                     "duration_notes": "Brief explanation of how this timeline was determined based on lesson complexity and past issues",
    #                     "number_of_modules": 2
    #                 }}
    #             ],
    #             "modules": [
    #                 {{
    #                     "title": "Module Title",
    #                     "objectives": ["Learning objective 1", "Learning objective 2", "Learning objective 3"],
    #                     "reading_material": {{
    #                         "id": "Unique ID for this reading material",
    #                         "name": "Name of the reading material",
    #                         "theoryContent": [
    #                             {{
    #                                 "title": "Section title",
    #                                 "prerequisites": ["Prerequisite 1", "Prerequisite 2"],
    #                                 "description": [
    #                                     "Detailed description paragraph 1 - must be substantial",
    #                                     "Detailed description paragraph 2 - must be substantial",
    #                                     "Detailed description paragraph 3 - must be substantial"
    #                                 ],
    #                                 "examples": [
    #                                     {{
    #                                         "title": "Example 1 title",
    #                                         "codeSnippet": "// Actual illustrative code example when appropriate\\nfunction example() {{\\n  return 'This is sample code';\\n}}",
    #                                         "explanation": "Detailed explanation of how this code example illustrates the concept"
    #                                     }},
    #                                     {{
    #                                         "title": "Example 2 title",
    #                                         "codeSnippet": null,
    #                                         "explanation": "Detailed explanation of this conceptual example"
    #                                     }}
    #                                 ]
    #                             }}
    #                         ],
    #                         "practicalGuide": [
    #                             {{
    #                                 "title": "Guide title",
    #                                 "steps": [
    #                                     "Detailed step 1 with explanation",
    #                                     "Detailed step 2 with explanation",
    #                                     "Detailed step 3 with explanation",
    #                                     "Detailed step 4 with explanation",
    #                                     "Detailed step 5 with explanation"
    #                                 ],
    #                                 "commonErrors": [
    #                                     "Common error 1 with prevention/solution advice",
    #                                     "Common error 2 with prevention/solution advice",
    #                                     "Common error 3 with prevention/solution advice"
    #                                 ]
    #                             }}
    #                         ],
    #                         "references": [
    #                             {{
    #                                 "title": "Academic reference title",
    #                                 "link": "https://example.com/academic-reference",
    #                                 "description": "Detailed description of this academic reference and its relevance"
    #                             }},
    #                             {{
    #                                 "title": "Industry reference title",
    #                                 "link": "https://example.com/industry-reference",
    #                                 "description": "Detailed description of this industry reference and its relevance"
    #                             }},
    #                             {{
    #                                 "title": "Practical reference title",
    #                                 "link": "https://example.com/practical-reference",
    #                                 "description": "Detailed description of this practical reference and its relevance"
    #                             }}
    #                         ],
    #                         "summaryAndReview": {{
    #                             "keyPoints": ["Key point 1", "Key point 2", "Key point 3", "Key point 4", "Key point 5"],
    #                             "reviewQuestions": [
    #                                 {{
    #                                     "id": "Question ID 1",
    #                                     "question": "Challenging review question 1",
    #                                     "answer": "Comprehensive answer to review question 1",
    #                                     "maxscore": 10,
    #                                     "score": null,
    #                                     "inputUser": null
    #                                 }},
    #                                 {{
    #                                     "id": "Question ID 2",
    #                                     "question": "Challenging review question 2",
    #                                     "answer": "Comprehensive answer to review question 2",
    #                                     "maxscore": 10,
    #                                     "score": null,
    #                                     "inputUser": null
    #                                 }}
    #                             ],
    #                             "quizLink": "https://example.com/quiz"
    #                         }}
    #                     }}
    #                 }}
    #             ]
    #         }}
    #         """
    #         return prompt
    # else: