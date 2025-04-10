from typing import List,Dict
from core.response import Ok
from machine.models import *
from fastapi import APIRouter, Depends
from machine.schemas.requests import *
from machine.schemas.responses.recommend import *
from machine.schemas.responses.quiz import *
from machine.schemas.responses.document import *
from machine.controllers import *
from machine.providers import InternalProvider
from core.exceptions import NotFoundException, BadRequestException
from fastapi.security import OAuth2PasswordBearer
from core.utils.auth_utils import verify_token
from machine.services.workflows.ai_tool_provider import AIToolProvider, LLMModelName
import json
from datetime import timezone

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
router = APIRouter(prefix="/modules", tags=["recommendation"])

@router.get("/{moduleId}/quizzes", response_model=Ok[ModuleQuizResponse])
async def get_module_by_quiz(
    moduleId: UUID,
    token: str = Depends(oauth2_scheme),
    modules_controller: ModulesController = Depends(InternalProvider().get_modules_controller),
    recommend_lessons_controller: RecommendLessonsController = Depends(InternalProvider().get_recommendlessons_controller),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
):
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    user = await student_controller.student_repository.first(where_=[Student.id == user_id])
    if not user:
        raise NotFoundException(message="Only Student have the permission to get this module.")
    if not moduleId:
        raise BadRequestException(message="Module ID is required.")

    module = await modules_controller.modules_repository.first(
        where_=[Modules.id == moduleId],
        relations=[Modules.quizzes],
    )
    if not module:
        raise NotFoundException(message="Module not found for the given ID.")
    recommend_lesson = await recommend_lessons_controller.recommend_lessons_repository.first(
        where_=[RecommendLessons.id == module.recommend_lesson_id],
        relations=[RecommendLessons.learning_path],
    )
    if not recommend_lesson:
        raise NotFoundException(message="Recommend Lesson not found for the given ID.")
    
    if not recommend_lesson.learning_path.student_id == user.id:
        raise NotFoundException(message="You are not authorized to access this module.")

    response_data = ModuleQuizResponse(
        module_id=module.id,
        title=module.title,
        objectives=module.objectives,
        quizzes=[
            QuizListResponse(
                id=quiz.id,
                name=quiz.name,
                description=quiz.description,
                status=quiz.status,
                score=quiz.score,
                max_score=quiz.max_score,
                time_limit=quiz.time_limit,
                duration=quiz.duration,
            )
            for quiz in module.quizzes
        ],
    )

    return Ok(data=response_data, message="Successfully fetched the module and quizzes.")
@router.get("/quizzes/{quizId}", response_model=Ok[QuizExerciseResponse])
async def get_quiz_exercise(
    quizId: UUID,
    token: str = Depends(oauth2_scheme),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    modules_controller: ModulesController = Depends(InternalProvider().get_modules_controller),
    recommend_lessons_controller: RecommendLessonsController = Depends(InternalProvider().get_recommendlessons_controller),
    recommend_quizzes_controller: RecommendQuizzesController = Depends(InternalProvider().get_recommend_quizzes_controller),
    recommend_quiz_question_controller: RecommendQuizQuestionController = Depends(InternalProvider().get_recommend_quiz_question_controller),
):
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    user = await student_controller.student_repository.first(where_=[Student.id == user_id])
    if not user:
        raise NotFoundException(message="Only Student have the permission to get this quiz.")
    
    
    quiz = await recommend_quizzes_controller.recommend_quizzes_repository.first(
        where_=[RecommendQuizzes.id == quizId],
    )
    if not quiz:
        raise NotFoundException(message="Quiz not found for the given ID in the specified module.")
    
    quiz_questions = await recommend_quiz_question_controller.recommend_quiz_question_repository.get_many(
        where_=[RecommendQuizQuestion.quiz_id == quizId],
    )
    module = await modules_controller.modules_repository.first(where_=[Modules.id == quiz.module_id])
    if not module:
        raise NotFoundException(message="Module not found for the given ID.")
    recommend_lesson = await recommend_lessons_controller.recommend_lessons_repository.first(
        where_=[RecommendLessons.id == module.recommend_lesson_id],
        relations=[RecommendLessons.learning_path],
    )
    if not recommend_lesson:
        raise NotFoundException(message="Recommend Lesson not found for the given ID.")
    if not recommend_lesson.learning_path.student_id == user.id:
        raise NotFoundException(message="You are not authorized to access this quiz.")
    
    # Use the quiz_questions from database instead of quiz.questions
    questions_response = [
        QuizQuestionResponse(
            id=question.id,
            question_text=question.question_text,
            question_type=question.question_type,
            options=question.options,
            correct_answer=question.correct_answer,
            difficulty=question.difficulty,
            points=question.points,
            explanation=question.explanation,
            user_choice=question.user_choice,
        ) for question in quiz_questions
    ]

    response_data = QuizExerciseResponse(
        id=quiz.id,
        name=quiz.name,
        description=quiz.description,
        status=quiz.status,
        score=quiz.score,
        max_score=quiz.max_score,
        time_limit=quiz.time_limit,
        duration=quiz.duration,
        questions=questions_response,
    )

    return Ok(data=response_data, message="Successfully fetched quiz details.")

@router.put("/quizzes/{quizId}/submit", response_model=Ok[QuizScoreResponse])
async def submit_quiz_answers(
    quizId: UUID,
    request: QuizAnswerRequest,
    token: str = Depends(oauth2_scheme),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    modules_controller: ModulesController = Depends(InternalProvider().get_modules_controller),
    recommend_lessons_controller: RecommendLessonsController = Depends(InternalProvider().get_recommendlessons_controller),
    recommend_quizzes_controller: RecommendQuizzesController = Depends(InternalProvider().get_recommend_quizzes_controller),
    recommend_quiz_question_controller: RecommendQuizQuestionController = Depends(InternalProvider().get_recommend_quiz_question_controller),
    learning_paths_controller: LearningPathsController = Depends(InternalProvider().get_learningpaths_controller),
    student_courses_controller: StudentCoursesController = Depends(InternalProvider().get_studentcourses_controller),
):  
    # Token verification
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    
    # Verify student
    user = await student_controller.student_repository.first(where_=[Student.id == user_id])
    if not user:
        raise NotFoundException(message="Only Students have permission to submit this quiz.")
    
    # Fetch quiz
    quiz = await recommend_quizzes_controller.recommend_quizzes_repository.first(
        where_=[RecommendQuizzes.id == quizId],
        relations=[RecommendQuizzes.questions]
    )
    if not quiz:
        raise NotFoundException(message="Quiz not found for the given ID.")
    
    # Fetch module and recommend lesson
    module = await modules_controller.modules_repository.first(where_=[Modules.id == quiz.module_id])
    if not module:
        raise NotFoundException(message="Module not found for the given ID.")
    
    recommend_lesson = await recommend_lessons_controller.recommend_lessons_repository.first(
        where_=[RecommendLessons.id == module.recommend_lesson_id],
        relations=[RecommendLessons.learning_path],
    )
    if not recommend_lesson:
        raise NotFoundException(message="Recommend Lesson not found for the given ID.")
    
    # Check authorization
    # if not recommend_lesson.learning_path.student_id == user.id:
    #     raise NotFoundException(message="You are not authorized to submit this quiz.")
    
    # Fetch quiz questions
    quiz_questions = await recommend_quiz_question_controller.recommend_quiz_question_repository.get_many(
        where_=[RecommendQuizQuestion.quiz_id == quizId],
    )
    
    # Validate answers
    if len(request.answers) != len(quiz_questions):
        raise BadRequestException(message="Number of answers does not match the number of questions.")

    # Calculate quiz results
    correct_count = 0
    results = []
    question_results = []  

    for question, user_choice in zip(quiz_questions, request.answers):
        # Check if the user's choice matches the correct answer
        is_correct = user_choice in question.correct_answer

        if is_correct:
            correct_count += 1
            
        difficulty = str(question.difficulty) if hasattr(question.difficulty, '__str__') else (
            question.difficulty.value if hasattr(question.difficulty, 'value') else question.difficulty
        )
        # Store detailed result for analysis
        question_results.append({
            "question_id": str(question.id),
            "question_text": question.question_text,
            "question_type": question.question_type,
            "options": question.options,
            "correct_answer": question.correct_answer,
            "user_choice": user_choice,
            "is_correct": is_correct,
            "difficulty": difficulty,
            "explanation": question.explanation
        })

        # Update the user's choice for the question
        await recommend_quiz_question_controller.recommend_quiz_question_repository.update(
            where_=[RecommendQuizQuestion.id == question.id],
            attributes={"user_choice": [user_choice]},
            commit=True
        )

        results.append(
            QuizQuestionResult(
                question_id=question.id,
                is_correct=is_correct,
            )
        )

    # Calculate score
    score = round((correct_count / len(quiz_questions)) * 100, 2)

    # Update quiz status and score
    await recommend_quizzes_controller.recommend_quizzes_repository.update(
        where_=[RecommendQuizzes.id == quizId],
        attributes={
            "score": score, 
            "status": StatusType.completed
        },
        commit=True, 
    )
    module_quizzes = await recommend_quizzes_controller.recommend_quizzes_repository.get_many(
        where_=[RecommendQuizzes.module_id == module.id]
    )
    completed_quizzes = [q for q in module_quizzes if q.status == StatusType.completed and q.score is not None]
    if completed_quizzes:
        total_score = sum(q.score for q in completed_quizzes)
        average_score = round(total_score / len(completed_quizzes), 2)
        
        await modules_controller.modules_repository.update(
            where_=[Modules.id == module.id],
            attributes={"progress": average_score},
            commit=True
        )
        
    # Variable to store identified issues
    identified_issues = None
    
    try:
        # Call the analysis function and capture any identified issues
        identified_issues = await analyze_and_return_issues(
            quiz_id=quizId,
            user_id=user.id,
            module=module,
            recommend_lesson=recommend_lesson,
            questions_results=question_results,
            recommend_lessons_controller=recommend_lessons_controller,
            learning_paths_controller=learning_paths_controller,
            student_courses_controller=student_courses_controller
        )
    except Exception as e:
        # Log the error but don't fail the quiz submission
        print(f"Error during issues analysis: {str(e)}")
        # You might want to add proper logging here
        
    await modules_controller.modules_repository.update_module_progress(module.id)
    await recommend_lessons_controller.recommend_lessons_repository.update_recommend_lesson_progress(recommend_lesson.id)
    await learning_paths_controller.learning_paths_repository.update_learning_path_progress(recommend_lesson.learning_path.id)
    
    # Prepare response
    response = QuizScoreResponse(
        quiz_id=quizId,
        total_questions=len(quiz_questions),
        correct_answers=correct_count,
        score=score,
        results=results,
        identified_issues=identified_issues  # Include identified issues in the response
    )

    return Ok(data=response, message="Quiz answers submitted successfully.")

async def analyze_and_return_issues(
    quiz_id: UUID,
    user_id: UUID,
    module,
    recommend_lesson,
    questions_results: List[Dict],
    recommend_lessons_controller: RecommendLessonsController,
    learning_paths_controller: LearningPathsController,
    student_courses_controller: StudentCoursesController,
):
    """
    Analyze quiz results, update the issues_summary in student_courses, and return identified issues
    """
    # Only proceed with analysis if there are incorrect answers
    incorrect_answers = [q for q in questions_results if not q["is_correct"]]
    if not incorrect_answers:
        return None  # No issues to analyze
    
    # Get current issues summary from student_courses
    learning_path = await learning_paths_controller.learning_paths_repository.first(
        where_=[LearningPaths.id == recommend_lesson.learning_path_id],
    )
    
    student_course = await student_courses_controller.student_courses_repository.first(
        where_=[StudentCourses.course_id == learning_path.course_id, StudentCourses.student_id == user_id],
    )
    
    current_summary = student_course.issues_summary if student_course.issues_summary else {"common_issues": []}
    
    # Prepare data for AI analysis
    prompt = prepare_analysis_prompt(
        quiz_id=quiz_id,
        module=module,
        recommend_lesson=recommend_lesson,
        questions_results=questions_results,
        current_summary=current_summary
    )
    
    ai_tool_provider = AIToolProvider()
    llm = ai_tool_provider.chat_model_factory(LLMModelName.GEMINI_PRO)
    
    llm.temperature = 0.3
    llm.max_output_tokens = 2000
    
    try:
        response = llm.invoke(prompt)
        
        if not response:
            print("Failed to get analysis from LLM")
            return None
        
        response_text = response.content
        analyzed_issues = extract_json_from_response(response_text)
        
        # Check if analysis returned valid data with issues
        if not analyzed_issues or "common_issues" not in analyzed_issues:
            print("Invalid response format from LLM")
            return None
        
        # Check if there are any issues to add
        if len(analyzed_issues["common_issues"]) == 0:
            print("No new issues identified based on quiz performance")
            return None  # No issues identified
        
        # Merge new issues with existing issues
        updated_summary = merge_issues_summary(current_summary, analyzed_issues)
        
        # Update issues_summary in student_courses
        await student_courses_controller.student_courses_repository.update(
            where_=[StudentCourses.course_id == learning_path.course_id, StudentCourses.student_id == user_id],
            attributes={"issues_summary": updated_summary},
            commit=True
        )
        
        # Return the newly identified issues for the API response
        return analyzed_issues["common_issues"]
        
    except Exception as e:
        print(f"Error during AI analysis: {str(e)}")
        raise e
def prepare_analysis_prompt(quiz_id, module, recommend_lesson, questions_results, current_summary):
    """
    Prepare the prompt for AI analysis
    """
    # Extract information about incorrect answers
    incorrect_answers = [q for q in questions_results if not q["is_correct"]]
    
    # Calculate performance metrics
    total_questions = len(questions_results)
    incorrect_count = len(incorrect_answers)
    correct_percentage = ((total_questions - incorrect_count) / total_questions) * 100
    
    # Check if performance is good enough to potentially skip issue creation
    high_performance = correct_percentage >= 90
    only_few_errors = incorrect_count <= 2
    complex_errors_only = all(q.get("difficulty", "").lower() in ["hard", "difficult", "advanced"] for q in incorrect_answers)
    
    prompt = f"""
    ## Quiz Analysis Task
    
    ## Quiz Information
    - Quiz ID: {quiz_id}
    - Module Title: {module.title}
    - Module Objectives: {json.dumps(module.objectives if module.objectives else [])}
    
    ## Lesson Information
    - Lesson Title: {recommend_lesson.title if hasattr(recommend_lesson, 'title') else 'N/A'}
    - Learning Outcomes: {json.dumps(recommend_lesson.learning_outcomes if hasattr(recommend_lesson, 'learning_outcomes') and recommend_lesson.learning_outcomes else [])}
    
    ## Quiz Results
    - Total Questions: {total_questions}
    - Incorrect Answers: {incorrect_count}
    - Correct Percentage: {correct_percentage:.1f}%
    - High Performance: {high_performance}
    - Only Few Errors: {only_few_errors}
    - Complex Questions Only: {complex_errors_only}
    
    ## Questions with Incorrect Answers
    {json.dumps(incorrect_answers, indent=2)}
    
    ## Current Issues Summary (for reference)
    {json.dumps(current_summary, indent=2)}
    
    ## Task
    Analyze the incorrectly answered questions and identify common issues or misunderstandings. 
    Consider the pattern of incorrect answers, the difficulty of questions, and any recurring themes.
    
    IMPORTANT: If the user performed well (high percentage correct) and only missed a few difficult questions,
    you may determine there are no significant issues to add. In such cases, return an empty issues list.
    
    ## Output Format
    Your response MUST be in the following JSON format:
    {{
        "common_issues": [
            {{
                "type": "concept_misunderstanding",
                "description": "Detailed description of the specific concept misunderstood",
                "frequency": number_of_occurrences,
                "related_lessons": [],
                "related_modules": [],
                "last_occurrence": "{datetime.now(timezone.utc).isoformat()}"
            }},
            {{
                "type": "quiz_failure",
                "description": "Detailed description of the specific difficulty faced",
                "frequency": number_of_occurrences,
                "related_lessons": [],
                "related_modules": [],
                "last_occurrence": "{datetime.now(timezone.utc).isoformat()}"
            }}
        ]
    }}
    
    IMPORTANT REQUIREMENTS:
    1. Each issue must have a clear "type" (e.g., "concept_misunderstanding", "quiz_failure", "knowledge_gap", etc.)
    2. The description must be specific and detailed about the exact concept misunderstood or problem encountered
    3. Frequency should reflect how many questions showed evidence of this issue
    4. Only include strong evidence-based issues that are clearly demonstrated by the incorrect answers
    5. Focus primarily on identifying conceptual misunderstandings rather than simple mistakes
    6. Focus on meaningful issues rather than superficial ones
    7. Look for patterns across multiple questions when possible
    8. Do not include issues that are already exactly the same in the current issues summary
    9. If the student performed very well (90%+ correct) or only missed a few difficult questions, return an empty "common_issues" list like: {{"common_issues": []}}
    
    Respond ONLY with the JSON. Do not include any other text, explanations, or notes.
    """
    
    return prompt

def extract_json_from_response(response_text):
    """
    Extract JSON from LLM response
    """
    try:
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass
        
        if "```json" in response_text:
            json_content = response_text.split("```json")[1].split("```")[0].strip()
            return json.loads(json_content)
        elif "```" in response_text:
            json_content = response_text.split("```")[1].split("```")[0].strip()
            return json.loads(json_content)
        
        import re
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        
        return None
    except Exception as e:
        print(f"Error extracting JSON: {str(e)}")
        return None

def merge_issues_summary(current_summary, new_issues):
    """
    Merge existing and new issues avoiding duplicates
    """
    
    if not isinstance(current_summary, dict):
        current_summary = {"common_issues": []}
    if "common_issues" not in current_summary:
        current_summary["common_issues"] = []
    
    # Create lookup dictionary for existing issues
    existing_issues = {}
    for i, issue in enumerate(current_summary["common_issues"]):
        key = (issue.get("type", ""), issue.get("description", ""))
        existing_issues[key] = i
    
    # Process new issues
    for new_issue in new_issues.get("common_issues", []):
        key = (new_issue.get("type", ""), new_issue.get("description", ""))
        
        if key in existing_issues:
            # Update existing issue
            index = existing_issues[key]
            existing_issue = current_summary["common_issues"][index]
            
            # Update frequency
            existing_issue["frequency"] = existing_issue.get("frequency", 0) + new_issue.get("frequency", 1)
            
            # Update last_occurrence if newer
            existing_last = existing_issue.get("last_occurrence", "")
            new_last = new_issue.get("last_occurrence", "")
            if new_last and (not existing_last or new_last > existing_last):
                existing_issue["last_occurrence"] = new_last
                
            # Merge related lessons and modules
            for field in ["related_lessons", "related_modules"]:
                existing_items = set(existing_issue.get(field, []))
                new_items = set(new_issue.get(field, []))
                existing_issue[field] = list(existing_items.union(new_items))
        else:
            # Add new issue
            current_summary["common_issues"].append(new_issue)
    
    return current_summary

@router.put("/quizzes/{quizId}/clear", response_model=Ok[bool])
async def clear_quiz_answers(
    quizId: UUID,
    token: str = Depends(oauth2_scheme),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    modules_controller: ModulesController = Depends(InternalProvider().get_modules_controller),
    recommend_lessons_controller: RecommendLessonsController = Depends(InternalProvider().get_recommendlessons_controller),
    recommend_quizzes_controller: RecommendQuizzesController = Depends(InternalProvider().get_recommend_quizzes_controller),
):
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    user = await student_controller.student_repository.first(where_=[Student.id == user_id])
    if not user:
        raise NotFoundException(message="Only Student have the permission to clear answer this quiz.")
    quiz = await recommend_quizzes_controller.recommend_quizzes_repository.first(
        where_=[RecommendQuizzes.id == quizId],
    )
    if not quiz:
        raise NotFoundException(message="Quiz not found for the given ID.")

    module = await modules_controller.modules_repository.first(where_=[Modules.id == quiz.module_id])
    if not module:
        raise NotFoundException(message="Module not found for the given ID.")
    recommend_lesson = await recommend_lessons_controller.recommend_lessons_repository.first(
        where_=[RecommendLessons.id == module.recommend_lesson_id],
        relations=[RecommendLessons.learning_path],
    )
    if not recommend_lesson:
        raise NotFoundException(message="Recommend Lesson not found for the given ID.")
    if not recommend_lesson.learning_path.student_id == user.id:
        raise NotFoundException(message="You are not authorized to clear answers for this quiz.")
    
    for question in quiz.questions:
        question['user_choice'] = None

    quiz.score = 0 
    quiz.status = StatusType.in_progress

    await recommend_quizzes_controller.recommend_quizzes_repository.update(
        where_=[RecommendQuizzes.id == quizId],
        attributes={"questions": quiz.questions, "score": quiz.score, "status": quiz.status},
        commit=True,
    )

    return Ok(data=True, message="Quiz answers cleared and reset successfully.")


@router.get("/{moduleId}/documents", response_model=Ok[DocumentResponse])
async def get_document(
    moduleId: UUID,
    token: str = Depends(oauth2_scheme),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    modules_controller: ModulesController = Depends(InternalProvider().get_modules_controller),
    recommend_lessons_controller: RecommendLessonsController = Depends(InternalProvider().get_recommendlessons_controller),
    recommend_documents_controller: RecommendDocumentsController = Depends(InternalProvider().get_recommenddocuments_controller),
):
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    user = await student_controller.student_repository.first(where_=[Student.id == user_id])
    if not user:
        raise NotFoundException(message="Only Student have the permission to get this document.")
    
    if not moduleId:
        raise BadRequestException(message="Document ID is required.")
    module = await modules_controller.modules_repository.first(
        where_=[Modules.id == moduleId],
    )
    if not module:
        raise NotFoundException(message="Module not found for the given ID.")
    recommend_lesson = await recommend_lessons_controller.recommend_lessons_repository.first(
        where_=[RecommendLessons.id == module.recommend_lesson_id],
        relations=[RecommendLessons.learning_path],
    )
    if not recommend_lesson:
        raise NotFoundException(message="Recommend Lesson not found for the given ID.")
    if not recommend_lesson.learning_path.student_id == user.id:
        raise NotFoundException(message="You are not authorized to access this document.")
    
    document = await recommend_documents_controller.recommend_documents_repository.first(
        where_=[RecommendDocuments.module_id == moduleId],
        relations=[RecommendDocuments.module], 
    )

    if not document:
        raise NotFoundException(message="Document not found for the given ID.")

    content = document.content or {}

    response_data = DocumentResponse(
        id=document.id,
        name=content.get("name", "No Name"),
        theoryContent=[
            TheoryContentResponse(
                title=theory.get("title", ""),
                prerequisites=theory.get("prerequisites", []),
                description=theory.get("description", []),
                examples=[
                    ExampleResponse(
                        title=example.get("title", ""),
                        codeSnippet=example.get("codeSnippet", ""),
                        explanation=example.get("explanation", "")
                    )
                    for example in theory.get("examples", [])
                ] if theory.get("examples") else None,
            )
            for theory in content.get("theoryContent", [])
        ],
        practicalGuide=[
            PracticalGuideResponse(
                title=guide.get("title", ""),
                steps=guide.get("steps", []),
                commonErrors=guide.get("commonErrors", []),
            )
            for guide in content.get("practicalGuide", [])
        ],
        references=[
            ReferenceResponse(
                title=ref.get("title", ""),
                link=ref.get("link", ""),
                description=ref.get("description", "")
            )
            for ref in content.get("references", [])
        ],
        summaryAndReview=SummaryAndReviewResponse(
            keyPoints=content.get("summaryAndReview", {}).get("keyPoints", []),
            reviewQuestions=[
                ReviewQuestionResponse(
                    id=question.get("id"),
                    question=question.get("question", ""),
                    answer=question.get("answer", ""),
                    maxscore=question.get("maxscore", 0),
                    score=question.get("score"),
                    inputUser=question.get("inputUser"),
                )
                for question in content.get("summaryAndReview", {}).get("reviewQuestions", [])
            ],
            quizLink=content.get("summaryAndReview", {}).get("quizLink", ""),
        ),
    )

    return Ok(data=response_data, message="Successfully fetched the document.")