from typing import List
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
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
router = APIRouter(prefix="/modules", tags=["recommendation"])

# async def analyze_quiz_issues(
#     recommend_lessons_controller,
#     recommend_quiz_question_controller,
#     quiz_id: UUID,
#     student_id: UUID
# ) -> Dict[str, Any]:
#     """
#     Analyze quiz issues and generate insights
    
#     Args:
#         recommend_lessons_controller: Controller for recommend lessons
#         recommend_quiz_question_controller: Controller for quiz questions
#         quiz_id: ID of the submitted quiz
#         student_id: ID of the student who took the quiz
    
#     Returns:
#         Dictionary of analyzed issues
#     """
#     # Fetch quiz questions with their details
#     quiz_questions = await recommend_quiz_question_controller.recommend_quiz_question_repository.get_many(
#         where_=[RecommendQuizQuestion.quiz_id == quiz_id],
#     )
    
#     # Analyze issues using AI
#     issue_analysis = await analyze_issues_with_ai(quiz_questions)
    
#     return issue_analysis

# async def analyze_issues_with_ai(quiz_questions):
#     """
#     Use AI to analyze quiz questions and generate insights
    
#     Args:
#         quiz_questions: List of quiz questions
    
#     Returns:
#         Analyzed issues dictionary
#     """
#     try:
#         # Prepare prompt for AI analysis
#         prompt = f"""Analyze the following quiz questions and identify common issues:
#         {json.dumps([{
#             'question': q.question,
#             'correct_answer': q.correct_answer,
#             'user_choice': q.user_choice,
#             'is_correct': q.user_choice in q.correct_answer
#         } for q in quiz_questions])}
        
#         Provide insights on:
#         1. Concept misunderstandings
#         2. Repeated errors
#         3. Learning gaps
        
#         Format the response as a JSON with the following structure:
#         {
#             "common_issues": [
#                 {
#                     "type": "concept_misunderstanding",
#                     "description": "Detailed description of the issue",
#                     "frequency": percentage_of_occurrences,
#                     "related_lessons": [lesson_ids],
#                     "related_modules": [module_ids],
#                     "last_occurrence": "ISO_TIMESTAMP"
#                 }
#             ]
#         }
#         """
        
#         # Call OpenAI or your preferred AI service
#         response = openai.ChatCompletion.create(
#             model="gpt-4",
#             messages=[{"role": "system", "content": prompt}]
#         )
        
#         # Parse AI response
#         ai_analysis = json.loads(response.choices[0].message.content)
#         return ai_analysis
#     except Exception as e:
#         # Fallback to basic analysis if AI fails
#         return {
#             "common_issues": [
#                 {
#                     "type": "quiz_failure",
#                     "description": "General performance issues detected",
#                     "frequency": len(quiz_questions),
#                     "related_lessons": [],
#                     "related_modules": [],
#                     "last_occurrence": datetime.now(timezone.utc).isoformat()
#                 }
#             ]
#         }

# def merge_issues_summary(current_summary: Dict[str, List[Dict]], new_issues: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
#     """
#     Merge new issues with existing issues, avoiding duplicates
    
#     Args:
#         current_summary: Existing issues summary
#         new_issues: Newly analyzed issues
    
#     Returns:
#         Updated issues summary
#     """
#     if not current_summary:
#         current_summary = {"common_issues": []}
    
#     # Create a lookup for existing issues to prevent duplicates
#     existing_issues = {
#         (issue.get('type'), issue.get('description')) 
#         for issue in current_summary.get('common_issues', [])
#     }
    
#     # Add new unique issues
#     for new_issue in new_issues.get('common_issues', []):
#         issue_key = (new_issue.get('type'), new_issue.get('description'))
        
#         if issue_key not in existing_issues:
#             current_summary['common_issues'].append(new_issue)
#             existing_issues.add(issue_key)
#         else:
#             # If issue already exists, update its frequency and last occurrence
#             for existing_issue in current_summary['common_issues']:
#                 if (existing_issue.get('type'), existing_issue.get('description')) == issue_key:
#                     existing_issue['frequency'] += new_issue.get('frequency', 0)
#                     existing_issue['last_occurrence'] = max(
#                         existing_issue.get('last_occurrence', ''), 
#                         new_issue.get('last_occurrence', '')
#                     )
    
#     return current_summary

# async def update_lesson_issues_summary(
#     recommend_lessons_controller,
#     recommend_quiz_question_controller,
#     quiz_id: UUID,
#     student_id: UUID,
#     lesson_id: UUID
# ):
#     """
#     Main function to update lesson issues summary after quiz submission
    
#     Args:
#         recommend_lessons_controller: Controller for recommend lessons
#         recommend_quiz_question_controller: Controller for quiz questions
#         quiz_id: ID of the submitted quiz
#         student_id: ID of the student who took the quiz
#         lesson_id: ID of the related lesson
#     """
#     # Analyze quiz issues
#     new_issues = await analyze_quiz_issues(
#         recommend_lessons_controller, 
#         recommend_quiz_question_controller, 
#         quiz_id, 
#         student_id
#     )
    
#     # Fetch current issues summary
#     recommend_lesson = await recommend_lessons_controller.recommend_lessons_repository.first(
#         where_=[RecommendLessons.id == lesson_id]
#     )
    
#     current_summary = recommend_lesson.issues_summary or {"common_issues": []}
    
#     # Merge and update issues summary
#     updated_summary = merge_issues_summary(current_summary, new_issues)
    
#     # Save updated issues summary
#     await recommend_lessons_controller.recommend_lessons_repository.update(
#         where_=[RecommendLessons.id == lesson_id],
#         attributes={"issues_summary": updated_summary},
#         commit=True
#     )
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
    if not recommend_lesson.learning_path.student_id == user.id:
        raise NotFoundException(message="You are not authorized to submit this quiz.")
    
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

    for question, user_choice in zip(quiz_questions, request.answers):
        # Check if the user's choice matches the correct answer
        is_correct = user_choice in question.correct_answer

        if is_correct:
            correct_count += 1

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
    score = (correct_count / len(quiz_questions)) * 100 

    # Update quiz status and score
    await recommend_quizzes_controller.recommend_quizzes_repository.update(
        where_=[RecommendQuizzes.id == quizId],
        attributes={
            "score": score, 
            "status": StatusType.completed
        },
        commit=True, 
    )

    # Prepare response
    response = QuizScoreResponse(
        quiz_id=quizId,
        total_questions=len(quiz_questions),
        correct_answers=correct_count,
        score=score,
        results=results,
    )

    return Ok(data=response, message="Quiz answers submitted successfully.")

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