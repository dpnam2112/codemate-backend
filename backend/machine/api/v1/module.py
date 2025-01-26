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
router = APIRouter(prefix="/modules", tags=["recomendation"])


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
                status=quiz.status,
                difficulty=quiz.difficulty,
                score=quiz.score,
                
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
    try:
        questions = quiz.questions 
        parsed_questions = [
            QuizQuestionResponse(
                id=UUID(question["id"]),
                question=question["question"],
                image=question.get("image"),
                options=question["options"],
                correct_answer=question["correct_answer"],
                explanation=question["explanation"],
                user_choice=question.get("user_choice"),
            )
            for question in questions
        ]
    except KeyError as e:
        raise SystemError(message=f"Invalid data format in questions: {e}")

    response_data = QuizExerciseResponse(
        id=quiz.id,
        name=quiz.name,
        status=quiz.status,
        difficulty=quiz.difficulty,
        score=quiz.score,
        max_score=quiz.max_score,
        questions=parsed_questions,
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
):  
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    user = await student_controller.student_repository.first(where_=[Student.id == user_id])
    if not user:
        raise NotFoundException(message="Only Student have the permission to submit this quiz.")
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
        raise NotFoundException(message="You are not authorized to submit this quiz.")
    
    if len(request.answers) != len(quiz.questions):
        raise BadRequestException(message="Number of answers does not match the number of questions.")

    correct_count = 0
    results = []

    for question, user_choice in zip(quiz.questions, request.answers):
        question['user_choice'] = user_choice
        is_correct = question['options'][user_choice] == question['correct_answer']
        if is_correct:
            correct_count += 1

        results.append(
            QuizQuestionResult(
                question_id=question['id'],
                is_correct=is_correct,
            )
        )
    quiz.score = (correct_count / len(quiz.questions)) * 100 
    quiz.status = StatusType.completed
    await recommend_quizzes_controller.recommend_quizzes_repository.update(
        where_=[recommend_quizzes.id == quizId],
        attributes={"questions": quiz.questions, "score": quiz.score, "status": quiz.status},
        commit=True, 
    )

    response = QuizScoreResponse(
        quiz_id=quizId,
        total_questions=len(quiz.questions),
        correct_answers=correct_count,
        score=quiz.score,
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