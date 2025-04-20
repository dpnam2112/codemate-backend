import json
import os
import logging
import re
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, Body
from core.response import Ok
from core.exceptions import *
from machine.controllers.learning_material_gen import LearningMaterialGenController
from machine.models import *
from machine.models import RecommendQuizQuestion
from machine.controllers import *
from machine.providers.internal import InternalProvider
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer
from uuid import UUID
from core.utils.auth_utils import verify_token
from machine.schemas.responses.ai import GenerateCodeExerciseResponse
from machine.schemas.responses.exercise import CodeExerciseBriefResponse
from ...schemas.requests.ai import GenerateCodeExerciseRequest, GenerateLearningPathRequest,GenerateQuizRequest
from machine.schemas.requests.llm_code import *
from machine.schemas.responses.llm_code import *
from dotenv import load_dotenv
from utils.chunk_manager import ChunkingManager
from machine.services.workflows.ai_tool_provider import AIToolProvider, LLMModelName
load_dotenv()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
router = APIRouter(prefix="/ai", tags=["ai"])

async def analyze_goal_and_timeline(
    goal: str,
    course_start_date: datetime,
    course_end_date: datetime,
    course_name: str,
    course_learning_outcomes: List[str]
) -> Dict[str, str]:
    """Giai đoạn 1: Phân tích goal, xác thực tính hợp lệ và xác định timeline."""
    
    # Bước tiền xử lý: Kiểm tra tính hợp lệ cơ bản của goal
    goal = goal.strip()  # Loại bỏ khoảng trắng thừa
    if len(goal) < 10:  # Độ dài tối thiểu (ví dụ: "Learn Python" ~ 12 ký tự)
        raise ApplicationException(message="Goal is too short or incomplete. Please provide a clear and complete learning goal (e.g., 'Learn Python basics').")
        
    # Prompt cải tiến với kiểm tra tính hoàn chỉnh
    prompt = f"""
    ## Goal Analysis and Validation Task
    - Student's Learning Goal: "{goal}"
    - Course Name: "{course_name}"
    - Course Learning Outcomes: {json.dumps(course_learning_outcomes, indent=2)}
    - Course Start Date: {course_start_date.strftime('%Y-%m-%d')}
    - Course End Date: {course_end_date.strftime('%Y-%m-%d')}

    ## Task Requirements
    1. **Check Goal Completeness:**
       - Determine if the goal is a complete, meaningful sentence with a clear intent (e.g., "I want to learn Python" is complete, but "I want " is not).
       - If incomplete or vague, return an error indicating the goal lacks clarity.

    2. **Validate Goal Relevance (if complete):**
       - Check if the goal is relevant to the course based on its name, description, and learning outcomes.
       - Example: "Learn to cook" is irrelevant to a "Python Programming" course.
       - If irrelevant, return an error message.

    3. **Validate Goal Feasibility (if complete and relevant):**
       - Check if the goal aligns with or is achievable within the scope of the course's learning outcomes.
       - Example: "Master Machine Learning" is not feasible for a "Basic Python" course.
       - If not feasible, return an error message.

    4. **Analyze Timeline (if goal is valid):**
       - Detect any time constraints in the goal (e.g., "in 2 weeks").
       - Determine a feasible timeline:
         - If the goal specifies a duration, calculate end_date as start_date + duration.
         - If no duration is specified, use the full course timeline.
         - Ensure start_date >= course_start_date and end_date <= course_end_date.

    5. **Return Result:**
       - If goal is invalid/incomplete, return an error in JSON format.
       - If goal is valid, return the timeline in JSON format.

    ## Output Format
    - For valid goal:
    {{
        "start_date": "YYYY-MM-DD",
        "end_date": "YYYY-MM-DD",
        "duration_notes": "Explanation of how the timeline was determined",
        "validation": {{
            "is_complete": true,
            "is_relevant": true,
            "is_feasible": true,
            "notes": "Explanation of why the goal is valid"
        }}
    }}
    - For invalid goal:
    {{
        "error": "Goal is incomplete" OR "Goal is not relevant to the course" OR "Goal exceeds the course scope",
        "details": "Explanation of why the goal is invalid",
        "validation": {{
            "is_complete": false/true,
            "is_relevant": false/true,
            "is_feasible": false/true,
            "notes": "Explanation of validation failure"
        }}
    }}
    """
    chunking_manager = ChunkingManager(
        provider="gemini",
        gemini_model_name="gemini-2.0-flash-lite",
        max_tokens_per_chunk=15000,
        temperature=0.7,
        max_output_tokens=8000
    )
    response = chunking_manager.call_llm_api(prompt, "You are an expert in goal validation and timeline analysis.")
    
    # Parse response
    if isinstance(response, str):
        response = json.loads(response)
    
    # Check if there's an error
    if "error" in response:
        raise ApplicationException(message=f"Goal validation failed: {response['error']}. {response['details']}")
    
    return response

async def select_relevant_lessons(
    goal: str,
    lessons_data: List[Dict],
    timeline: Dict[str, str],
    course_name: str,
    course_learning_outcomes: List[str]
) -> List[Dict]:
    """Giai đoạn 2: Lọc và sắp xếp các lesson liên quan đến goal trong bối cảnh khóa học."""
    prompt = f"""
    ## Lesson Selection Task
    - Student's Learning Goal: "{goal}"
    - Course Name: "{course_name}"
    - Course Learning Outcomes: {json.dumps(course_learning_outcomes, indent=2)}
    - Timeline: Start Date: {timeline['start_date']}, End Date: {timeline['end_date']}
    - Available Lessons: {json.dumps(lessons_data, indent=2)}

    ## Task Requirements
    1. **Analyze the Goal in Context:**
       - Interpret the student's goal in the context of the course name and learning outcomes.
       - If the goal is vague or grade-based (e.g., "achieve at least B+"), assume it means achieving a subset of the course's learning outcomes sufficient for that grade (e.g., B+ might cover 70-80% of outcomes, while A+ covers 100%).
       - Example: For a goal "achieve at least B+ grade" in a "Python Programming" course with outcomes like ["Understand loops", "Master functions", "Apply OOP"], select lessons covering core concepts (e.g., loops and functions) but not necessarily advanced topics (e.g., OOP).

    2. **Select Relevant Lessons:**
       - Choose lessons from the available list that directly support achieving the goal, aligned with the course's learning outcomes.
       - Prioritize foundational lessons if the timeline is short or the goal implies a minimum competency level.

    3. **Assign Order:**
       - Assign an "order" (1, 2, 3...) based on logical progression (e.g., foundational lessons first, advanced lessons later).

    4. **Fit the Timeline:**
       - Limit the number of lessons to fit the timeline (short-term: fewer lessons, long-term: more comprehensive).
       - Consider the complexity and duration of lessons relative to the timeline.

    5. **Return Result:**
       - Return only the relevant lessons with their IDs, order, titles, and explanations.

    ## Output Format
    [
        {{
            "lesson_id": "Lesson ID",
            "order": 1,
            "title": "Lesson Title",
            "relevance_explanation": "Why this lesson is needed for the goal and how it relates to the course learning outcomes"
        }}
    ]
    """
    chunking_manager = ChunkingManager(
        provider="gemini",
        gemini_model_name="gemini-2.0-flash-lite",
        max_tokens_per_chunk=15000,
        temperature=0.7,
        max_output_tokens=8000
    )
    response = chunking_manager.call_llm_api(prompt, "You are an expert in educational content selection.")
    return response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def generate_detailed_learning_path(
    goal: str,
    timeline: Dict[str, str],
    selected_lessons: List[Dict],
    lessons_data: List[Dict],
    student_id: str,
    course_id: str,
) -> Dict:
    """Giai đoạn 3: Tạo learning path chi tiết với đầy đủ các yêu cầu và ràng buộc."""
    # Split the task into smaller chunks by generating recommend_lessons and modules separately
    chunking_manager = ChunkingManager(
        provider="gemini",
        gemini_model_name="gemini-2.0-flash-lite",
        max_tokens_per_chunk=10000,  # Reduced to ensure input fits
        temperature=0.7,
        max_output_tokens=12000,     # Increased to allow larger output
    )

    # Step 1: Generate recommend_lessons
    lessons_prompt = f"""
    ## Learning Path Lessons Generation Task

    ### Context
    - Student's Learning Goal: "{goal}"
    - Timeline: Start Date: {timeline['start_date']}, End Date: {timeline['end_date']}
    - Selected Lessons: {json.dumps(selected_lessons, indent=2)}

    ## Task Requirements
    1. Generate ONLY the "recommend_lessons" section using the selected lessons.
    2. Ensure sequential order and dates:
       - Use "order" from `selected_lessons`.
       - Assign "start_date" and "end_date" starting from {timeline['start_date']}.
    3. Include ALL mandatory fields:
       - "order": Exact value from `selected_lessons`.
       - "number_of_modules": 2 or 3 based on complexity.

    ## CRITICAL INSTRUCTIONS
    - DO NOT OMIT "order" or "number_of_modules".
    - Return ONLY the "recommend_lessons" array.
    **Provide Detailed Recommendations:**
        - For each recommended lesson:
            - "recommended_content": Explain clearly what to focus on in this lesson to achieve the goal (at least 5 sentences to describe).
            - "explain": Justify why this lesson is critical for the goal. (at least 5 sentences to describe)
            - Include 2-3 modules per lesson to break down key concepts.

    ## Output Format
     [
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
    ]
    """

    try:
        lessons_response = chunking_manager.call_llm_api(
            lessons_prompt,
            "You are an expert in creating detailed learning paths."
        )
        logger.info(f"Raw lessons response from Gemini: {lessons_response}")
        if isinstance(lessons_response, str):
            recommend_lessons = json.loads(lessons_response)
        else:
            recommend_lessons = lessons_response

        # Validate lessons
        for lesson in recommend_lessons:
            if "order" not in lesson or "number_of_modules" not in lesson:
                matching_lesson = next((sl for sl in selected_lessons if sl["lesson_id"] == lesson["lesson_id"]), None)
                lesson["order"] = matching_lesson["order"] if matching_lesson else 1
                lesson["number_of_modules"] = 2  # Default
            if lesson["number_of_modules"] not in [2, 3]:
                lesson["number_of_modules"] = 2

    except Exception as e:
        logger.error(f"Error generating recommend_lessons: {str(e)}")
        raise ApplicationException(message=f"Failed to generate lessons: {str(e)}")

    # Step 2: Generate modules for each lesson
    modules = []
    for lesson in recommend_lessons:
        num_modules = lesson["number_of_modules"]
        modules_prompt = f"""
        ## Modules Generation Task

        ### Context
        - Lesson ID: "{lesson['lesson_id']}"
        - Recommended Content: "{lesson['recommended_content']}"
        - Goal: "{goal}"

        ## Task Requirements
        1. Generate {num_modules} modules for this lesson.
        2. Each module must include "title", "objectives", and "reading_material" with all subfields.
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
        [
            {{
                "title": "Module Title",
                "objectives": ["Objective 1", "Objective 2"],
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
        """
        try:
            module_response = chunking_manager.call_llm_api(
                modules_prompt,
                "You are an expert in creating educational modules."
            )
            if isinstance(module_response, str):
                module_data = json.loads(module_response)
            else:
                module_data = module_response
            modules.extend(module_data)
        except Exception as e:
            logger.error(f"Error generating modules for lesson {lesson['lesson_id']}: {str(e)}")
            raise ApplicationException(message=f"Failed to generate modules: {str(e)}")

    # Step 3: Assemble final response
    final_response = {
        "learning_path_start_date": timeline["start_date"],
        "learning_path_end_date": timeline["end_date"],
        "learning_path_objective": f"Achieve {goal}",
        "learning_path_progress": 0,
        "student_id": student_id,
        "course_id": course_id,
        "recommend_lessons": recommend_lessons,
        "modules": modules
    }

    logger.info(f"Final validated response: {json.dumps(final_response, indent=2)}")
    return final_response

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
    recommend_documents_controller: RecommendDocumentsController = Depends(InternalProvider().get_recommenddocuments_controller),
    lessons_controller: LessonsController = Depends(InternalProvider().get_lessons_controller),
):
    """
    Generate a personalized learning path for a student based on their goals and course content.
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
    
    # Giai đoạn 1: Phân tích goal và xác định timeline
    timeline = await analyze_goal_and_timeline(
        goal=request.goal,
        course_start_date=course.start_date,
        course_end_date=course.end_date,
        course_name=course.name,
        course_learning_outcomes=course.learning_outcomes or []
    )

    # Giai đoạn 2: Chọn và sắp xếp lessons liên quan
    selected_lessons = await select_relevant_lessons(
        goal=request.goal,
        lessons_data=lessons_data,
        timeline=timeline,
        course_name=course.name,
        course_learning_outcomes=course.learning_outcomes or []
    )

    # Giai đoạn 3: Tạo learning path chi tiết
    learning_path = await generate_detailed_learning_path(
        goal=request.goal,
        timeline=timeline,
        selected_lessons=selected_lessons,
        lessons_data=lessons_data,
        student_id=str(student.id),
        course_id=str(request.course_id)
    )
    # Save to database
    if learning_path:
        logger.info(f"Generated learning path successfully: {json.dumps(learning_path, indent=2)}")
        # Sanitize date fields to remove timestamp if present
        for key in ["learning_path_start_date", "learning_path_end_date"]:
            if 'T' in learning_path[key]:
                learning_path[key] = learning_path[key].split('T')[0]
        
        # Sanitize dates in recommend_lessons
        for lesson in learning_path["recommend_lessons"]:
            if 'T' in lesson["start_date"]:
                lesson["start_date"] = lesson["start_date"].split('T')[0]
            if 'T' in lesson["end_date"]:
                lesson["end_date"] = lesson["end_date"].split('T')[0]

        if isinstance(learning_path, str):
            try:
                learning_path = json.loads(learning_path)
            except json.JSONDecodeError:
                raise ApplicationException(message="Failed to parse learning_path as JSON.")
        
        learning_path_attributes = {
            "start_date": datetime.strptime(learning_path["learning_path_start_date"], '%Y-%m-%d').date(),
            "end_date": datetime.strptime(learning_path["learning_path_end_date"], '%Y-%m-%d').date(),
            "objective": request.goal,
            "student_id": str(student.id),
            "course_id": str(request.course_id),
            "llm_response": learning_path,
        }
        
        add_learning_path = await learning_path_controller.learning_paths_repository.create(
            attributes=learning_path_attributes, commit=True
        )
        
        if add_learning_path:
            recommend_lesson_attributes_list = []
            for recommend_lesson in learning_path["recommend_lessons"]:
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

            for i, module_data in enumerate(learning_path["modules"]):
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
                module_attributes_list, learning_path["recommend_lessons"], created_recommend_lessons
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
                
                created_recommend_lessons_response = []
                for i, recommend_lesson in enumerate(created_recommend_lessons):
                    # Get the corresponding number_of_modules from learning_path["recommend_lessons"]
                    original_lesson = learning_path["recommend_lessons"][i]
                    num_modules = original_lesson.get("number_of_modules", 2)  # Use pre-calculated value
                    created_recommend_lessons_response.append({
                        "lesson_id": str(recommend_lesson.lesson_id),
                        "recommended_content": recommend_lesson.recommended_content,
                        "explain": recommend_lesson.explain,
                        "status": recommend_lesson.status,
                        "progress": recommend_lesson.progress,
                        "bookmark": recommend_lesson.bookmark,
                        "start_date": str(recommend_lesson.start_date),
                        "end_date": str(recommend_lesson.end_date),
                        "duration_notes": recommend_lesson.duration_notes,
                        "order": recommend_lesson.order,
                        "number_of_modules": num_modules,  # Use the pre-calculated value
                    })
                
                created_modules_response = [
                    {
                        "recommend_lesson_id": str(module.recommend_lesson_id),
                        "title": module.title,
                        "objectives": module.objectives,
                        "last_accessed": module.last_accessed,
                        "id": str(module.id)
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
        
        return Ok(learning_path)
    else:
        raise ApplicationException(message="Failed to generate recommendations")

def assign_recommend_lesson_id(modules, recommend_lessons, created_recommend_lessons):
    current_lesson_index = 0 
    created_lesson_index = 0 
    modules_processed = 0  

    for module in modules:
        recommend_lesson = recommend_lessons[current_lesson_index]
        number_of_modules = recommend_lesson.get("number_of_modules", 2)  # Default to 2 if not specified

        module["recommend_lesson_id"] = created_recommend_lessons[created_lesson_index].id

        modules_processed += 1

        if modules_processed >= number_of_modules:
            current_lesson_index += 1
            created_lesson_index += 1
            modules_processed = 0 

    return modules

async def regenerate_lesson_content(
    recommend_lesson_id: UUID,
    analysis_result: dict,
    prior_recommend_lessons_data: List[dict],
    lessons_controller: LessonsController,
    recommend_lessons_controller: RecommendLessonsController,
    modules_controller: ModulesController,
    recommend_documents_controller: RecommendDocumentsController
) -> dict:
    """Bổ sung nội dung cho một recommended lesson dựa trên analysis result mà không xóa modules cũ."""
    # Fetch existing data
    recommend_lesson = await recommend_lessons_controller.recommend_lessons_repository.first(
        where_=[RecommendLessons.id == recommend_lesson_id]
    )
    if not recommend_lesson:
        raise NotFoundException(message="Recommended lesson not found.")
    
    lesson = await lessons_controller.lessons_repository.first(
        where_=[Lessons.id == recommend_lesson.lesson_id]
    )
    if not lesson:
        raise NotFoundException(message="Lesson not found.")

    # Get existing modules to reference later
    existing_modules = await modules_controller.modules_repository.get_many(
        where_=[Modules.recommend_lesson_id == recommend_lesson_id]
    )
    existing_module_titles = [module.title for module in existing_modules]

    # Initialize the ChunkingManager
    chunking_manager = ChunkingManager(
        provider="gemini",
        gemini_model_name="gemini-2.0-flash-lite",
        max_tokens_per_chunk=15000,
        temperature=0.7,
        max_output_tokens=8000
    )

    # Prompt for creating supplementary modules focused on issues
    prompt = f"""
    ## Supplementary Learning Content Generation Task

    ### Context
    - Lesson Title: "{lesson.title}"
    - Current Recommended Content: "{recommend_lesson.recommended_content}"  
    - Current Explanation: "{recommend_lesson.explain}"
    - Start Date: "{recommend_lesson.start_date}"
    - End Date: "{recommend_lesson.end_date}"
    - Existing Module Titles: {json.dumps(existing_module_titles)}
    - Issues Analysis: {json.dumps(analysis_result.get('issues_analysis', {}), indent=2)}

    ### Prior Recommend Lessons Context (Only if Review Prior is Required)
    - Prior Recommend Lessons:
    {{
        "lessons": {json.dumps(prior_recommend_lessons_data, indent=2) if prior_recommend_lessons_data else "No prior recommend lessons provided"}
    }}

    ### Task Requirements
    You are tasked with creating supplementary modules that specifically address the issues identified in the student's learning progress. Rather than replacing existing content, these new modules will complement it and help the student overcome their specific challenges.

    1. **Analyze Issues and Current Content:**
       - Review the `issues_analysis` to identify the significant issues the student is struggling with
       - Consider the existing module titles to avoid duplication
       - Use the `recommendations` to inform your approach (e.g., if "review_prior" is recommended)

    2. **Create Targeted Supplementary Modules:**
       - Generate 1-3 new modules that directly address the significant issues identified
       - Each module title MUST start with phrases like "Addressing:", "Resolving:", "Overcoming:", or "Deep Dive:" followed by the specific issue
       - Each module should focus on ONE specific challenge from the issues analysis
       - If "review_prior" is in recommendations, include a module that connects prior knowledge to current issues

    3. **Update Recommended Content and Explanation:**
       - Create additional content that introduces these new modules and explains how they relate to the existing content
       - Provide a clear path for the student to follow (e.g., "After reviewing the original modules, focus on these supplementary modules")

    ### Output Format
    {{
        "supplementary_content": "- Point 1\\n- Point 2\\n- Point 3 (Additional content introducing the supplementary modules and their purpose...)",
        "supplementary_explanation": "- Explanation point 1\\n- Explanation point 2\\n- Explanation point 3 (Explanation of how these modules address the specific issues...)",
        "supplementary_modules": [
            {{
                "title": "Addressing: [Specific Issue]",
                "objectives": ["Objective 1", "Objective 2", "Objective 3"],
                "reading_material": {{
                    "theoryContent": [
                        {{
                            "title": "Understanding [Issue] Better",
                            "description": ["Para 1", "Para 2", "Para 3"],
                            "examples": [
                                {{
                                    "title": "Example: Common Mistake",
                                    "codeSnippet": "code here",
                                    "explanation": "How this relates to the issue"
                                }},
                                {{
                                    "title": "Example: Correct Approach",
                                    "codeSnippet": "code here",
                                    "explanation": "How to solve the issue"
                                }}
                            ]
                        }}
                    ],
                    "practicalGuide": [
                        {{
                            "title": "Step-by-Step Solution Guide",
                            "steps": ["Step 1", "Step 2", "Step 3", "Step 4", "Step 5"],
                            "commonErrors": ["Error 1 - solution", "Error 2 - solution", "Error 3 - solution"]
                        }}
                    ],
                    "references": [
                        {{
                            "title": "Resource specifically targeting this issue",
                            "link": "https://example.com",
                            "description": "How this helps with the specific issue"
                        }},
                        {{
                            "title": "Practice exercises",
                            "link": "https://example.com",
                            "description": "Additional practice"
                        }},
                        {{
                            "title": "Visual explanation",
                            "link": "https://example.com",
                            "description": "Visual explanation of the concept"
                        }}
                    ],
                    "summaryAndReview": {{
                        "keyPoints": ["Point 1", "Point 2", "Point 3", "Point 4", "Point 5"],
                        "reviewQuestions": [
                            {{
                                "id": "Q1",
                                "question": "Question targeting the specific issue",
                                "answer": "Answer",
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

    # Get response from LLM
    response = chunking_manager.call_llm_api(prompt, "You are an expert in educational content generation.")
    supplementary_content = response if isinstance(response, dict) else json.loads(response)

    # Update recommend_lesson with combined content
    updated_recommended_content = f"{recommend_lesson.recommended_content}\n\n**SUPPLEMENTARY CONTENT**: {supplementary_content['supplementary_content']}"
    updated_explanation = f"{recommend_lesson.explain}\n\n**ADDITIONAL GUIDANCE**: {supplementary_content['supplementary_explanation']}"

    await recommend_lessons_controller.recommend_lessons_repository.update(
        where_=[RecommendLessons.id == recommend_lesson_id],
        attributes={
            "recommended_content": updated_recommended_content,
            "explain": updated_explanation,
            "status": "new",  # Reset status for student to work through again
            "progress": recommend_lesson.progress  # Keep existing progress 
        },
        commit=True
    )

    # Create just the new supplementary modules
    module_attributes_list = []
    recommend_documents_attributes_list = []

    for module_data in supplementary_content["supplementary_modules"]:
        module_attr = {
            "recommend_lesson_id": recommend_lesson_id,
            "title": module_data["title"],
            "objectives": module_data["objectives"]
        }
        module_attributes_list.append(module_attr)
        recommend_documents_attributes_list.append({
            "module_id": None,
            "content": module_data["reading_material"]
        })

    # Only create new modules, don't replace existing ones
    created_modules = await modules_controller.modules_repository.create_many(
        attributes_list=module_attributes_list,
        commit=True
    )

    # Link new modules to their content
    for i, module in enumerate(created_modules):
        recommend_documents_attributes_list[i]["module_id"] = module.id

    # Create new recommend documents
    created_recommend_documents = await recommend_documents_controller.recommend_documents_repository.create_many(
        attributes_list=recommend_documents_attributes_list,
        commit=True
    )
    
    created_recommend_documents_response = [
        {
            "id": str(doc.id),
            "module_id": str(doc.module_id),
            "content": doc.content if isinstance(doc.content, str) else json.dumps(doc.content)
        }
        for doc in created_recommend_documents
    ]

    # Return all modules including existing ones
    all_modules = await modules_controller.modules_repository.get_many(
        where_=[Modules.recommend_lesson_id == recommend_lesson_id]
    )

    # Format the response with all modules (both existing and new)
    updated_content = {
        "recommended_content": updated_recommended_content,
        "explain": updated_explanation, 
        "start_date": str(recommend_lesson.start_date),
        "end_date": str(recommend_lesson.end_date),
        "duration_notes": recommend_lesson.duration_notes,
        "modules": [
            {
                "id": str(module.id),
                "title": module.title,
                "objectives": module.objectives,
                "is_supplementary": module.id in [m.id for m in created_modules]  # Flag to identify new modules
            } for module in all_modules
        ],
        "recommend_documents": created_recommend_documents_response
    }

    return updated_content

@router.get("/monitor-study-progress/course/{course_id}/recommend_lesson/{recommend_lesson_id}")
async def monitor_study_progress(
    recommend_lesson_id: UUID,
    course_id: UUID,
    token: str = Depends(oauth2_scheme),
    recommend_lessons_controller: RecommendLessonsController = Depends(InternalProvider().get_recommendlessons_controller),
    learning_path_controller: LearningPathsController = Depends(InternalProvider().get_learningpaths_controller),
    lessons_controller: LessonsController = Depends(InternalProvider().get_lessons_controller),
    student_courses_controller: StudentCoursesController = Depends(InternalProvider().get_studentcourses_controller),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller)
):  # Remove the -> dict annotation
    # Verify token to get student_id
    payload = verify_token(token)
    student_id = payload.get("sub")
    if not student_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    
    # Get student record
    student = await student_controller.student_repository.first(where_=[Student.id == student_id])
    if not student:
        raise NotFoundException(message="Your account is not allowed to access this feature.")
    
    # Get recommend_lesson
    recommend_lesson = await recommend_lessons_controller.recommend_lessons_repository.first(
        where_=[RecommendLessons.id == recommend_lesson_id]
    )
    if not recommend_lesson:
        raise NotFoundException(message="Recommended lesson not found.")

    # Get learning path
    learning_path = await learning_path_controller.learning_paths_repository.first(
        where_=[LearningPaths.student_id == UUID(student_id), LearningPaths.course_id == course_id],
        order_={"desc": ["version"]}
    )
    if not learning_path:
        raise NotFoundException(message="Learning path not found.")

    # if recommend_lesson.progress < 80:
    #     return Ok(data=None, message="Student has not met the required learning criteria to analyze their study results.")

    student_course = await student_courses_controller.student_courses_repository.first(
        where_=[StudentCourses.student_id == UUID(student_id), StudentCourses.course_id == course_id]
    )
    issues_summary = student_course.issues_summary if student_course and student_course.issues_summary else {}

    analysis_result = await analyze_issues(
        recommend_lesson,
        issues_summary,
        learning_path,
        recommend_lessons_controller,
        lessons_controller
    )

    if analysis_result["can_proceed"]:
        await recommend_lessons_controller.recommend_lessons_repository.update(
            where_=[RecommendLessons.id == recommend_lesson_id],
            attributes={"status": "completed", "progress": 100},
            commit=True
        )
        return Ok(data=analysis_result, message="Lesson completed successfully. Student can proceed to the next lesson.")
        
    if analysis_result["needs_repeat"]:
        return Ok(data=analysis_result, message="Student needs to repeat the lesson due to identified issues.")

    return Ok(data=analysis_result, message="Student needs to review prior lessons before proceeding.")
async def analyze_issues(
    recommend_lesson: RecommendLessons,
    issues_summary: dict,
    learning_path: LearningPaths,
    recommend_lessons_controller: RecommendLessonsController,
    lessons_controller: LessonsController
) -> dict:
    """
    Analyze the issues_summary using AI to determine next steps for the student.
    
    Args:
        recommend_lesson: The recommended lesson object
        issues_summary: JSON data from StudentCourses.issues_summary
        learning_path: The latest learning path for the student
        recommend_lessons_controller: Controller for recommend_lessons
        lessons_controller: Controller for lessons
    
    Returns:
        Dict with AI-driven analysis results and recommendations
    """
    result = {
        "can_proceed": True,
        "needs_repeat": False,
        "needs_review_prior": False,
        "issues_analysis": {},
        "recommendations": [],
    }

    # If no issues_summary or empty, return early
    if not issues_summary or "common_issues" not in issues_summary:
        result["message"] = "No significant issues found."
        return result

    # Initialize ChunkingManager for AI analysis
    chunking_manager = ChunkingManager(
        provider="gemini",
        gemini_model_name="gemini-2.0-flash-lite",
        max_tokens_per_chunk=15000,
        temperature=0.7,
        max_output_tokens=8000
    )

    # Fetch lesson and learning path details
    lesson = await lessons_controller.lessons_repository.first(
        where_=[Lessons.id == recommend_lesson.lesson_id]
    )
    all_recommend_lessons = await recommend_lessons_controller.recommend_lessons_repository.get_many(
        where_=[RecommendLessons.learning_path_id == learning_path.id]
    )
    prior_lessons = [rl for rl in all_recommend_lessons if rl.order < recommend_lesson.order]
    
    # Get lesson details for prior lessons (if any)
    prior_lessons_details = []
    if prior_lessons:
        for rl in prior_lessons:
            prior_lesson = await lessons_controller.lessons_repository.first(
                where_=[Lessons.id == rl.lesson_id]
            )
            prior_lessons_details.append({
                "id": str(rl.id),
                "title": prior_lesson.title,
                "order": rl.order
            })
    
    # Determine if current lesson is the first one
    is_first_lesson = len(prior_lessons) == 0
    
    # Construct AI prompt
    ## 6. For analyze_issues in ai_routers.py

    prompt = f"""
    ## Issues Analysis Task
    - Lesson Title: "{lesson.title}"
    - Recommended Lesson ID: "{recommend_lesson.id}"
    - Student Goal: "{learning_path.objective}"
    - Issues Summary (JSON): {json.dumps(issues_summary, indent=2)}
    - Is First Lesson in Learning Path: {is_first_lesson}
    - Prior Lessons in Learning Path: {json.dumps(prior_lessons_details, indent=2)}

    ## FORMATTING REQUIREMENTS:
    - Present ALL content in list format with bullet points or numbering
    - Never use paragraphs - break content into structured lists
    - Use line breaks between major points
    - Keep individual points concise (1-2 sentences maximum)
    - Use hierarchical structure for clarity
    - Include bullet points (•) at the start of list items
    - Use numbered lists (1., 2., etc.) for sequential steps

    ## Task Requirements
    Analyze the provided `issues_summary` to determine the student's next steps.

    {
    "For first lesson analysis:" if is_first_lesson else "For subsequent lesson analysis:"
    }

    {
    """
    1. Focus ONLY on issues related to the current lesson (this is the first lesson in the path).
    2. Look in the common_issues array for issues where related_lessons contains the current recommended lesson ID.
    """ if is_first_lesson else """
    1. Analyze issues related to BOTH the current lesson AND any prior lessons.
    2. Look in the common_issues array for issues where related_lessons contains either the current or prior recommended lesson IDs.
    """
    }

    Consider:
    1. **Severity of Issues**:
    - Present analysis as bulleted list points
    - Break down frequency data into structured format

    2. **Impact on Long-term Goals**:
    - Structure impact assessment as bullet points
    - List specific consequences with clear formatting

    3. **Relation to Prior Lessons**: {
    "" if is_first_lesson else """
    - Present connections as structured list items
    - Format lesson references with clear hierarchy
    """
    }

    4. **Recommendations**:
    - Format each recommendation as a structured list
    - Present reasoning as bulleted points
    - Structure lesson references with clear formatting

    ## Output Format
    {{
        "can_proceed": true/false,
        "needs_repeat": true/false,
        "needs_review_prior": true/false,
        "issues_analysis": {{
            "significant_issues": [
                {{
                    "type": "issue type",
                    "frequency": number,
                    "description": "• Issue point 1\\n• Issue point 2",
                    "severity": "low/medium/high",
                    "impact_on_goals": "• Impact 1\\n• Impact 2\\n• Impact 3"
                }}
            ],
            "total_issues_count": number,
            "increasing_issues": ["issue1", "issue2"],
            "most_frequent_type": "type"
        }},
        "recommendations": [
            {{
                "action": "proceed/repeat/review_prior",
                "reason": "• Reason 1\\n• Reason 2\\n• Reason 3",
                "details": "• Lesson detail 1\\n• Lesson detail 2"
            }}
        ]
    }}

    IMPORTANT RULES:
    1. YOU MUST RETURN THE RESPONSE IN JSON FORMAT ABOVE.
    2. NEVER return IDs of lessons in recommendations - use LESSON TITLES instead.
    3. Give ONLY ONE or at most TWO recommendations.
    4. If giving two recommendations, "proceed" and "repeat" CANNOT both be included.
    5. ALL TEXT MUST BE FORMATTED AS LISTS WITH BULLET POINTS, NOT PARAGRAPHS.
    """
        
    print(f"AI prompt: {prompt}")

    # Call AI for analysis
    try:
        response = chunking_manager.call_llm_api(
            prompt,
            "You are an expert AI assistant specializing in educational analysis and student progress evaluation."
        )
        analysis_result = response if isinstance(response, dict) else json.loads(response)
    except Exception as e:
        print(f"AI analysis failed: {str(e)}")
        # Fallback to basic analysis if AI fails
        analysis_result = {
            "can_proceed": True,
            "needs_repeat": False,
            "needs_review_prior": False,
            "issues_analysis": {"significant_issues": [], "total_issues_count": issues_summary.get("total_issues_count", 0)},
            "recommendations": []
        }
        raise BadRequestException(message="AI analysis unavailable. Defaulting to proceed due to insufficient data.")

    # Populate result from AI response
    result.update(analysis_result)

    return result

class RegenerateLessonRequest(BaseModel):
    recommend_lesson_id: UUID
    analysis_result: dict  # Kết quả từ monitor_study_progress_endpoint

@router.post("/regenerate-lesson-content")
async def regenerate_lesson_content_endpoint(
    request: RegenerateLessonRequest = Body(...),
    token: str = Depends(oauth2_scheme),
    recommend_lessons_controller: RecommendLessonsController = Depends(InternalProvider().get_recommendlessons_controller),
    lessons_controller: LessonsController = Depends(InternalProvider().get_lessons_controller),
    modules_controller: ModulesController = Depends(InternalProvider().get_modules_controller),
    learning_path_controller: LearningPathsController = Depends(InternalProvider().get_learningpaths_controller),
    recommend_documents_controller: RecommendDocumentsController = Depends(InternalProvider().get_recommenddocuments_controller),
):
    """Regenerate content for a recommended lesson based on analysis result from monitor_study_progress."""
    payload = verify_token(token)
    student_id = payload.get("sub")
    if not student_id:
        raise BadRequestException(message="Invalid token.")

    # Kiểm tra analysis_result
    analysis_result = request.analysis_result
    if not analysis_result.get("needs_repeat", False):
        raise BadRequestException(message="Regeneration is only allowed when the lesson needs to be repeated.")

    # Fetch recommend_lesson
    recommend_lesson = await recommend_lessons_controller.recommend_lessons_repository.first(
        where_=[RecommendLessons.id == request.recommend_lesson_id]
    )
    if not recommend_lesson:
        raise NotFoundException(message="Recommended lesson not found.")

    # Check if review_prior is required
    needs_review_prior = analysis_result.get("needs_review_prior", False)
    prior_recommend_lessons_data = []
    if needs_review_prior:
        # Fetch prior recommend lessons if review_prior is in recommendations
        learning_path = await learning_path_controller.learning_paths_repository.first(
            where_=[LearningPaths.id == recommend_lesson.learning_path_id]
        )
        prior_recommend_lessons = await recommend_lessons_controller.recommend_lessons_repository.get_many(
            where_=[RecommendLessons.learning_path_id == learning_path.id, RecommendLessons.order < recommend_lesson.order],
            order_={"asc": ["order"]}
        )
        # Limit to 2 most recent prior recommend lessons
        for prior_rl in prior_recommend_lessons[-2:]:
            prior_lesson = await lessons_controller.lessons_repository.first(
                where_=[Lessons.id == prior_rl.lesson_id]
            )
            prior_recommend_lessons_data.append({
                "title": prior_lesson.title,
                "recommended_content": prior_rl.recommended_content,
                "explain": prior_rl.explain,
                "order": prior_rl.order,
                "progress": prior_rl.progress
            })

    # Call regenerate_lesson_content with analysis_result and prior data
    updated_content = await regenerate_lesson_content(
        recommend_lesson_id=request.recommend_lesson_id,
        analysis_result=analysis_result,
        prior_recommend_lessons_data=prior_recommend_lessons_data,
        lessons_controller=lessons_controller,
        recommend_lessons_controller=recommend_lessons_controller,
        modules_controller=modules_controller,
        recommend_documents_controller=recommend_documents_controller
    )
    return Ok(data=updated_content, message="Lesson content regenerated successfully.")

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
    
    # Use AIToolProvider to create the LLM model
    ai_tool_provider = AIToolProvider()
    llm = ai_tool_provider.chat_model_factory(LLMModelName.GEMINI_PRO)
    
    # Set fixed parameters with increased token limit
    llm.temperature = 0.3
    llm.max_output_tokens = 8192 
    
    # Create quiz record first with basic info
    quiz_attributes = {
        "name": f"Quiz for {lesson.title}",
        "description": f"Assessment based on {module.title}",
        "status": "new",
        "time_limit": 30,  # Default, will update later
        "max_score": 100,  # Default, will update later
        "module_id": module.id,
    }
    
    created_quiz = await recommend_quizzes_controller.recommend_quizzes_repository.create(attributes=quiz_attributes, commit=True)
    
    if not created_quiz:
        raise ApplicationException(message="Failed to create quiz")
    
    # Initialize questions list
    all_questions = []
    
    # Generate questions in batches by difficulty
    difficulties = [
        {"name": "easy", "count": request.difficulty_distribution.easy},
        {"name": "medium", "count": request.difficulty_distribution.medium},
        {"name": "hard", "count": request.difficulty_distribution.hard}
    ]
    
    total_points = 0
    question_count = 0
    
    # Generate questions for each difficulty level
    for difficulty in difficulties:
        if difficulty["count"] <= 0:
            continue
            
        # Skip if no questions needed for this difficulty
        difficulty_name = difficulty["name"]
        questions_needed = difficulty["count"]
        
        # Build prompt for this difficulty only
        prompt = f"""
        ## Quiz Generation Task for {difficulty_name.upper()} Questions Only
        
        ## Module Information
        - Module Title: {module.title}
        - Module Objectives: {json.dumps(module.objectives if module.objectives else [])}
        
        ## Lesson Information
        - Lesson Title: {lesson.title}
        - Lesson Description: {lesson.description}
        - Learning Outcomes: {json.dumps(lesson.learning_outcomes if lesson.learning_outcomes else [])}
        - Recommended focus areas: "{recommended_content}"
        
        ## Task Requirements
        Generate EXACTLY {questions_needed} {difficulty_name} difficulty questions for a quiz on this module. The questions should:
        1. Focus specifically on assessing the module objectives
        2. Align with the recommended content areas
        3. Cover key concepts from the lesson materials
        
        ## Document Content Summary
        {lesson.description}
        {recommended_content}
        
        ## Output Format
        Your response MUST be valid JSON in the following format:
        {{
            "questions": [
                {{
                    "question_text": "The question text goes here?",
                    "question_type": "single_choice", 
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "correct_answer": ["Option B"],
                    "difficulty": "{difficulty_name}", 
                    "explanation": "Detailed explanation of why this is the correct answer",
                    "points": {10 if difficulty_name == "hard" else (7 if difficulty_name == "medium" else 5)}
                }},
                ...
            ]
        }}
        
        IMPORTANT REQUIREMENTS:
        1. Generate EXACTLY {questions_needed} questions, all with "{difficulty_name}" difficulty
        2. Include a mix of single_choice, multiple_choice, and true_false question types
        3. For single_choice questions: have only one correct answer among options
        4. For multiple_choice questions: may have multiple correct answers
        5. For true/false questions: options should be exactly ["True", "False"]
        6. Each question must have a detailed explanation for the correct answer
        7. Make sure correct_answer exactly matches one of the options
        8. All correct_answer values must be provided as arrays, even for single answers
        9. Each question should be worth {10 if difficulty_name == "hard" else (7 if difficulty_name == "medium" else 5)} points
        """
        
        try:
            question_request = QuestionRequest(
                content=prompt,
                temperature=0.3,
                max_tokens=8192  
            )
            
            response = llm.invoke(question_request.content)
            
            if not response:
                print(f"Failed to generate {difficulty_name} questions")
                continue
                
            # Extract JSON from response
            response_text = response.content
            
            try:
                if "```json" in response_text:
                    json_content = response_text.split("```json")[1].split("```")[0].strip()
                    difficulty_data = json.loads(json_content)
                else:
                    # Try to find JSON object in the text
                    json_pattern = r'(\{[\s\S]*\})' 
                    match = re.search(json_pattern, response_text)
                    if match:
                        json_content = match.group(1)
                        difficulty_data = json.loads(json_content)
                    else:
                        difficulty_data = json.loads(response_text)
                
                # Add questions to our list
                if "questions" in difficulty_data and isinstance(difficulty_data["questions"], list):
                    # Validate each question before adding
                    for q in difficulty_data["questions"]:
                        # Ensure required fields exist
                        if all(key in q for key in ["question_text", "question_type", "options", "correct_answer", "difficulty", "explanation", "points"]):
                            # Force difficulty to match the current batch
                            q["difficulty"] = difficulty_name
                            all_questions.append(q)
                            total_points += q["points"]
                            question_count += 1
                
            except (json.JSONDecodeError, Exception) as e:
                print(f"Error parsing {difficulty_name} questions: {str(e)}")
                # Continue with other difficulties even if one fails
                
        except Exception as e:
            print(f"Error generating {difficulty_name} questions: {str(e)}")
            # Continue with other difficulties
    
    # If we couldn't generate any questions, raise an error
    if not all_questions:
        # Clean up by deleting the created quiz
        await recommend_quizzes_controller.recommend_quizzes_repository.delete(created_quiz.id, commit=True)
        raise ApplicationException(message="Failed to generate any quiz questions")
    
    # Update quiz with actual information
    updated_quiz_attributes = {
        "name": f"Quiz: {module.title}",
        "description": f"Assessment covering key concepts from {lesson.title}",
        "time_limit": min(60, question_count * 2),  # Estimate 2 minutes per question
        "max_score": total_points,
    }
    
    await recommend_quizzes_controller.recommend_quizzes_repository.update(
        where_=[RecommendQuizzes.id == created_quiz.id],
        attributes=updated_quiz_attributes,
        commit=True
    )
    
    # Create quiz questions
    question_attributes_list = []
    for question in all_questions:
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
        # Clean up
        await recommend_quizzes_controller.recommend_quizzes_repository.delete(created_quiz.id, commit=True)
        raise ApplicationException(message="Failed to create quiz questions")
    
    # Format the response
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

@router.post("/generate-code-exercise", response_model=Ok[CodeExerciseBriefResponse])
async def generate_code_exercise(
    request: GenerateCodeExerciseRequest,
    learning_material_gen_controller: LearningMaterialGenController = Depends(InternalProvider().get_learning_material_gen_controller)
):
    new_exercise = await learning_material_gen_controller.generate_programming_exercise(module_id=request.module_id)
    return Ok(data=CodeExerciseBriefResponse.model_validate(new_exercise))
    
'''
export interface Root {
  can_proceed: boolean
  needs_repeat: boolean
  needs_review_prior: boolean
  issues_analysis: IssuesAnalysis
  recommendations: Recommendation[]
}

export interface IssuesAnalysis {
  significant_issues: SignificantIssue[]
  total_issues_count: number
  increasing_issues: string[]
  most_frequent_type: string
}

export interface SignificantIssue {
  type: string
  frequency: number
  description: string
  severity: string
  impact_on_goals: string
}

export interface Recommendation {
  action: string
  reason: string
  details: string
}

{
  "can_proceed": false,
  "needs_repeat": true,
  "needs_review_prior": true,
  "issues_analysis": {
    "significant_issues": [
      {
        "type": "concept_misunderstanding",
        "frequency": 8,
        "description": "Struggling to grasp recursion base cases.",
        "severity": "high",
        "impact_on_goals": "This significantly hinders the student's ability to understand and implement recursive functions, which is fundamental to mastering Python programming."
      },
      {
        "type": "code_error",
        "frequency": 5,
        "description": "Errors in recursive function implementation.",
        "severity": "medium",
        "impact_on_goals": "Frequent code errors will slow down the student's progress and may lead to frustration, ultimately affecting their ability to master Python programming."
      }
    ],
    "total_issues_count": 13,
    "increasing_issues": [
      "recursion application"
    ],
    "most_frequent_type": "concept_misunderstanding"
  },
  "recommendations": [
    {
      "action": "repeat",
      "reason": "The student demonstrates significant difficulties with base cases and implementing recursive functions. Repeating the current lesson will allow for more practice and clarification of these core concepts.",
      "details": "Review the 'Advanced Recursion' lesson."
    },
    {
      "action": "review_prior",
      "reason": "The issues with base cases suggest a potential gap in understanding the foundational concepts of recursion, covered in a prior lesson.",
      "details": "Review the lesson titled 'Introduction to Recursion' (ID: 6a5216cc-f261-45f2-acac-e602c9ab48e3)."
    }
  ]
}
'''
