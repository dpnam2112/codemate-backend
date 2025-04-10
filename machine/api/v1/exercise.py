from os import wait
from core.db.decorators import Transactional
import machine.controllers as ctrl
from fastapi import APIRouter, Depends, Path, Query
from core.response import Ok
from machine.schemas.programming_submission import ProgrammingSubmissionCreateResponse, ProgrammingSubmissionItemSchema, ProgrammingSubmissionSchema
from machine.schemas.requests.conversation import InvokeCodingAssistantSchema
from machine.schemas.requests.exercise import  *
from machine.schemas.responses.conversation import MessageResponseSchema
from machine.schemas.responses.exercise import  *
from machine.providers import InternalProvider
from machine.controllers import *
from machine.models import *
from core.exceptions import NotFoundException, BadRequestException
from uuid import UUID
from fastapi import  Depends
from fastapi.security import OAuth2PasswordBearer
from core.utils.auth_utils import verify_token
from starlette.responses import StreamingResponse
from machine.schemas.programming_exercise import *


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
router = APIRouter(prefix="/exercises", tags=["exercises"])
@router.post("/quizzes", response_model=Ok[ExerciseQuizResponse])
async def add_exercises(
    body: ExerciseRequest,
    token : str = Depends(oauth2_scheme),
    exercises_controller: ExercisesController = Depends(InternalProvider().get_exercises_controller),
    course_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
):
    """
    Adds a new exercise with questions to a lesson.
    """
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    user = await professor_controller.professor_repository.first(where_=[Professor.id == user_id])
    if not user:
        raise NotFoundException(message="Only professors have the permission to create exercise for this course.")
    
    # Validate course existence
    course = await course_controller.courses_repository.first(
        where_=[Courses.id == body.course_id],
    )
    if not course:
        raise NotFoundException(message="Course not found for the given ID.")
    if not course.professor_id == user.id:
        raise BadRequestException(message="You are not allowed to create exercise for this course.")
    
    # Validate and process questions
    questions_data = []
    total_score = 0
    for question in body.questions:
        if not all([question.question, question.answer, question.options, question.type]):
            raise BadRequestException(
                message=f"Invalid question data: {question.model_dump()}. All fields must be provided.",
            )
        
        # Ensure feedback field is present, even if empty
        feedback = getattr(question, 'feedback', '')
        
        # Ensure difficulty field is present
        difficulty = getattr(question, 'difficulty', DifficultyLevel.medium)
        
        # Add question data with all required fields
        question_data = {
            "question": question.question,
            "answer": question.answer,
            "options": question.options,
            "feedback": feedback,
            "type": question.type.value,
            "difficulty": difficulty.value,
            "score": question.score,
        }
        questions_data.append(question_data)
        total_score += question.score

    # Prepare exercise data
    exercise_data = {
        "name": body.name,
        "description": body.description,
        "topic": body.topic,
        "type": body.type.value,
        "course_id": body.course_id,
        "questions": questions_data,
        "max_score": body.max_score or total_score,
        "time_open": getattr(body, 'time_open', None),
        "time_close": getattr(body, 'time_close', None) or getattr(body, 'deadline', None),
        "time_limit": getattr(body, 'time_limit', None) or getattr(body, 'time', None),
        "attempts_allowed": getattr(body, 'attempts_allowed', None),
        "grading_method": getattr(body, 'grading_method', GradingMethodType.highest),
        "shuffle_questions": getattr(body, 'shuffle_questions', False),
        "shuffle_answers": getattr(body, 'shuffle_answers', False),
        "review_after_completion": getattr(body, 'review_after_completion', True),
        "show_correct_answers": getattr(body, 'show_correct_answers', False),
        "penalty_per_attempt": getattr(body, 'penalty_per_attempt', 0.0),
        "pass_mark": getattr(body, 'pass_mark', 0.0),
    }

    # Create the exercise
    created_exercise = await exercises_controller.exercises_repository.create(
        exercise_data, commit=True
    )

    # Prepare quiz modal objects
    quiz_questions = []
    for q in questions_data:
        quiz_questions.append(
            QuizModal(
                question=q["question"],
                answer=q["answer"],
                options=q["options"],
                feedback=q["feedback"],
                type=QuestionType(q["type"]),
                difficulty=DifficultyLevel(q["difficulty"]),
                score=q["score"],
            )
        )

    # Return the response
    return Ok(
        data=ExerciseQuizResponse(
            exercise_id=created_exercise.id,
            course_id=created_exercise.course_id,
            name=created_exercise.name,
            description=created_exercise.description,
            topic=created_exercise.topic,
            questions=quiz_questions,
            max_score=created_exercise.max_score,
            type=ExerciseType(created_exercise.type),
            time_open=created_exercise.time_open,
            time_close=created_exercise.time_close,
            time_limit=created_exercise.time_limit,
            attempts_allowed=created_exercise.attempts_allowed,
            grading_method=GradingMethodType(created_exercise.grading_method),
            shuffle_questions=created_exercise.shuffle_questions,
            shuffle_answers=created_exercise.shuffle_answers,
            review_after_completion=created_exercise.review_after_completion,
            show_correct_answers=created_exercise.show_correct_answers,
            penalty_per_attempt=created_exercise.penalty_per_attempt,
            pass_mark=created_exercise.pass_mark,
        ),
        message="Successfully created the exercise.",
    )
@router.get("/{exercise_id}/quizzes", response_model=Ok[ExerciseQuizResponse])
async def get_exercise(
    exercise_id: UUID,
    token: str = Depends(oauth2_scheme),
    exercises_controller: ExercisesController = Depends(InternalProvider().get_exercises_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
):
    """
    Retrieves an existing quiz exercise by ID.
    """
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    professor = await professor_controller.professor_repository.first(where_=[Professor.id == user_id])
    if not professor:
        raise NotFoundException(message="Your account is not allowed to get detail quiz.")
    
    # Fetch the exercise
    exercise = await exercises_controller.exercises_repository.first(
        where_=[Exercises.id == exercise_id]
    )
    if not exercise:
        raise NotFoundException(message="Exercise not found for the given ID.")
    
    # Prepare quiz modal objects from the stored questions data
    quiz_questions = []
    for q in exercise.questions:
        quiz_questions.append(
            QuizModal(
                question=q["question"],
                answer=q["answer"],
                options=q["options"],
                feedback=q.get("feedback", ""),
                type=QuestionType(q["type"]),
                difficulty=DifficultyLevel(q.get("difficulty", "medium")),
                score=q["score"],
            )
        )

    # Return the response
    return Ok(
        data=ExerciseQuizResponse(
            exercise_id=exercise.id,
            course_id=exercise.course_id,
            name=exercise.name,
            description=exercise.description,
            topic=exercise.topic,
            questions=quiz_questions,
            max_score=exercise.max_score,
            type=ExerciseType(exercise.type),
            time_open=exercise.time_open,
            time_close=exercise.time_close,
            time_limit=exercise.time_limit,
            attempts_allowed=exercise.attempts_allowed,
            grading_method=GradingMethodType(exercise.grading_method) if exercise.grading_method else GradingMethodType.HIGHEST,
            shuffle_questions=exercise.shuffle_questions,
            shuffle_answers=exercise.shuffle_answers,
            review_after_completion=exercise.review_after_completion,
            show_correct_answers=exercise.show_correct_answers,
            penalty_per_attempt=exercise.penalty_per_attempt,
            pass_mark=exercise.pass_mark,
        ),
        message="Successfully retrieved the exercise.",
    )
@router.put("/{exercise_id}/quizzes", response_model=Ok[ExerciseQuizResponse])
async def update_exercise(
    exercise_id: UUID,
    body: ExerciseRequest,
    token: str = Depends(oauth2_scheme),
    exercises_controller: ExercisesController = Depends(InternalProvider().get_exercises_controller),
    course_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
):
    """
    Updates an existing exercise with new details and questions.
    """
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    user = await professor_controller.professor_repository.first(where_=[Professor.id == user_id])
    if not user:
        raise NotFoundException(message="Only professors have the permission to update this exercise.")
    
    # Validate exercise existence
    exercise = await exercises_controller.exercises_repository.first(
        where_=[Exercises.id == exercise_id]
    )
    if not exercise:
        raise NotFoundException(message="Exercise not found for the given ID.")

    # Validate course existence
    course = await course_controller.courses_repository.first(
        where_=[Courses.id == body.course_id],
    )
    if not course:
        raise NotFoundException(message="Course not found for the given ID.")
    if not course.professor_id == user.id:
        raise BadRequestException(message="You are not allowed to update exercise for this course.")
    
    # Validate and process questions
    questions_data = []
    total_score = 0
    for question in body.questions:
        if not all([question.question, question.answer, question.options, question.type]):
            raise BadRequestException(
                message=f"Invalid question data: {question.model_dump()}. All fields must be provided.",
            )
        
        # Ensure feedback field is present, even if empty
        feedback = getattr(question, 'feedback', '')
        
        # Ensure difficulty field is present
        difficulty = getattr(question, 'difficulty', DifficultyLevel.medium)
        
        # Add question data with all required fields
        question_data = {
            "question": question.question,
            "answer": question.answer,
            "options": question.options,
            "feedback": feedback,
            "type": question.type.value,
            "difficulty": difficulty.value,
            "score": question.score,
        }
        questions_data.append(question_data)
        total_score += question.score

    # Handle datetime timezone issues by ensuring all datetime objects are timezone-naive
    
    # Prepare updated exercise data
    update_data = {
        "name": body.name,
        "description": body.description,
        "topic": body.topic,
        "type": body.type.value,
        "course_id": body.course_id,
        "questions": questions_data,
        "max_score": body.max_score or total_score,
        "time_open": getattr(body, 'time_open', None),
        "time_close": getattr(body, 'time_close', None),
        "time_limit": getattr(body, 'time_limit', None) or getattr(body, 'time', None),
        "attempts_allowed": getattr(body, 'attempts_allowed', None),
        "grading_method": getattr(body, 'grading_method', GradingMethodType.highest).value,
        "shuffle_questions": getattr(body, 'shuffle_questions', False),
        "shuffle_answers": getattr(body, 'shuffle_answers', False),
        "review_after_completion": getattr(body, 'review_after_completion', True),
        "show_correct_answers": getattr(body, 'show_correct_answers', False),
        "penalty_per_attempt": getattr(body, 'penalty_per_attempt', 0.0),
        "pass_mark": getattr(body, 'pass_mark', 0.0),
    }

    # Update the exercise
    updated_exercise = await exercises_controller.exercises_repository.update(
        where_=[Exercises.id == exercise_id],
        attributes=update_data,
        commit=True,
    )

    # Prepare quiz modal objects
    quiz_questions = []
    for q in questions_data:
        quiz_questions.append(
            QuizModal(
                question=q["question"],
                answer=q["answer"],
                options=q["options"],
                feedback=q["feedback"],
                type=QuestionType(q["type"]),
                difficulty=DifficultyLevel(q["difficulty"]),
                score=q["score"],
            )
        )

    # Return the response
    return Ok(
        data=ExerciseQuizResponse(
            exercise_id=updated_exercise.id,
            course_id=updated_exercise.course_id,
            name=updated_exercise.name,
            description=updated_exercise.description,
            topic=updated_exercise.topic,
            questions=quiz_questions,
            max_score=updated_exercise.max_score,
            type=ExerciseType(updated_exercise.type),
            time_open=updated_exercise.time_open,
            time_close=updated_exercise.time_close,
            time_limit=updated_exercise.time_limit,
            attempts_allowed=updated_exercise.attempts_allowed,
            grading_method=GradingMethodType(updated_exercise.grading_method),
            shuffle_questions=updated_exercise.shuffle_questions,
            shuffle_answers=updated_exercise.shuffle_answers,
            review_after_completion=updated_exercise.review_after_completion,
            show_correct_answers=updated_exercise.show_correct_answers,
            penalty_per_attempt=updated_exercise.penalty_per_attempt,
            pass_mark=updated_exercise.pass_mark,
        ),
        message="Successfully updated the exercise.",
    )
@router.delete("/{exercise_id}/quizzes", response_model=Ok[ExerciseQuizResponse])
async def delete_exercise(
    exercise_id: UUID,
    token: str = Depends(oauth2_scheme),
    exercises_controller: ExercisesController = Depends(InternalProvider().get_exercises_controller),
    course_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    student_exercise_controller: StudentExercisesController = Depends(InternalProvider().get_studentexercises_controller),
):
    """
    Deletes an existing exercise by ID.
    """
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    user = await professor_controller.professor_repository.first(where_=[Professor.id == user_id])
    if not user:
        raise NotFoundException(message="Only professors have the permission to delete this exercise.")
    # Validate exercise existence
    exercise = await exercises_controller.exercises_repository.first(
        where_=[Exercises.id == exercise_id],
        relations=[Exercises.course,
                   Exercises.student_exercises],
    )
    if not exercise:
        raise NotFoundException(message="Exercise not found for the given ID.")
    if not exercise.course:
        raise NotFoundException(message="Exercise not associated with any course.")
    
    if not exercise.course.professor_id == user.id:
        raise BadRequestException(message="You are not allowed to delete exercise for this lesson.")
    # Delete the exercise
    await exercises_controller.exercises_repository.delete(
        where_=[Exercises.id == exercise_id],
    )
    if exercise.student_exercises:
        for student_exercise in exercise.student_exercises:
            await student_exercise_controller.student_exercises_repository.delete(
                where_=[StudentExercises.id == student_exercise.id]
            )
            
    await exercises_controller.exercises_repository.session.commit()
    # Return success response
    return Ok(
        data=ExerciseQuizResponse(
            exercise_id=exercise.id,
            course_id=exercise.course_id,
            name=exercise.name,
            description=exercise.description,
            topic=exercise.topic,
            max_score=exercise.max_score,   
            type=exercise.type,
            time_open=exercise.time_open,
            time_close=exercise.time_close,
            time_limit=exercise.time_limit,
            attempts_allowed=exercise.attempts_allowed,
            grading_method=exercise.grading_method,
            shuffle_questions=exercise.shuffle_questions,
            shuffle_answers=exercise.shuffle_answers,
            review_after_completion=exercise.review_after_completion,
            show_correct_answers=exercise.show_correct_answers,
            penalty_per_attempt=exercise.penalty_per_attempt,
            pass_mark=exercise.pass_mark,
            questions=[
                QuizModal(
                    question=q["question"],
                    answer=q["answer"],
                    options=q["options"],
                    type=q["type"],
                    difficulty=q["difficulty"],
                    feedback=q["feedback"],
                    score=q["score"],
                ).model_dump()  # Convert to dictionary
                for q in exercise.questions
            ],
        ),
        message="Exercise successfully deleted.")

@router.post("/code", response_model=Ok[ExerciseCodeResponse])
async def add_code_exercise(
    body: ExerciseCodeRequest,
    token : str = Depends(oauth2_scheme),
    exercises_controller: ExercisesController = Depends(InternalProvider().get_exercises_controller),
    course_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
):
    """
    Adds a new code exercise to a course.
    """
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    user = await professor_controller.professor_repository.first(where_=[Professor.id == user_id])
    if not user:
        raise NotFoundException(message="Only professors have the permission to create exercise for this course.")
    
    # Validate course existence
    course = await course_controller.courses_repository.first(
        where_=[Courses.id == body.course_id],
    )
    if not course:
        raise NotFoundException(message="Course not found for the given ID.")
    if not course.professor_id == user.id:
        raise BadRequestException(message="You are not allowed to create exercise for this course.")
    
    # Validate and process questions
    questions_data = []
    total_score = 0
    for question in body.questions:
        if not all([question.question, question.testcases]):
            raise BadRequestException(message="Each question must have both question text and test cases")
        
        for testcase in question.testcases:
            if not all([testcase.inputs is not None, testcase.output is not None]):
                raise BadRequestException(message="Each test case must have both input and output fields")
        
        # Add question data with all required fields
        question_data = {
            "question": question.question,
            "testcases": [t.model_dump() for t in question.testcases],
            "starter_code": getattr(question, 'starter_code', ''),
            "solution_code": getattr(question, 'solution_code', ''),
            "hints": getattr(question, 'hints', []),
            "score": getattr(question, 'score', 10),
            "difficulty": getattr(question, 'difficulty', DifficultyLevel.medium).value,
            "allowed_languages": getattr(question, 'allowed_languages', []),
            "time_limit_seconds": getattr(question, 'time_limit_seconds', 5),
            "memory_limit_mb": getattr(question, 'memory_limit_mb', 256),
        }
        questions_data.append(question_data)
        total_score += question_data["score"]

    # Prepare exercise data
    exercise_data = {
        "name": body.name,
        "description": body.description,
        "topic": body.topic,
        "type": body.type.value,
        "course_id": body.course_id,
        "questions": questions_data,
        "max_score": body.max_score or total_score,
        "time_open": getattr(body, 'time_open', None),
        "time_close": getattr(body, 'time_close', None),
        "time_limit": getattr(body, 'time_limit', None),
        "attempts_allowed": getattr(body, 'attempts_allowed', None),
        "grading_method": getattr(body, 'grading_method', GradingMethodType.highest).value,
        "shuffle_questions": getattr(body, 'shuffle_questions', False),
        "shuffle_answers": getattr(body, 'shuffle_answers', False),
        "review_after_completion": getattr(body, 'review_after_completion', True),
        "show_correct_answers": getattr(body, 'show_correct_answers', False),
        "penalty_per_attempt": getattr(body, 'penalty_per_attempt', 0.0),
        "pass_mark": getattr(body, 'pass_mark', 0.0),
    }

    # Create the exercise
    created_exercise = await exercises_controller.exercises_repository.create(
        exercise_data, commit=True
    )

    # Prepare code question modal objects
    code_questions = []
    for q in questions_data:
        code_questions.append(
            CodeModel(
                question=q["question"],
                testcases=[
                    TestCaseModel(
                        inputs=t["inputs"],
                        output=t["output"],
                        is_hidden=t.get("is_hidden", False),
                        description=t.get("description", "")
                    ) for t in q["testcases"]
                ],
                starter_code=q.get("starter_code", ""),
                solution_code=q.get("solution_code", ""),
                hints=q.get("hints", []),
                score=q.get("score", 10),
                difficulty=DifficultyLevel(q.get("difficulty", "medium")),
                allowed_languages=q.get("allowed_languages", []),
                time_limit_seconds=q.get("time_limit_seconds", 5),
                memory_limit_mb=q.get("memory_limit_mb", 256),
            )
        )

    # Return the response
    return Ok(
        data=ExerciseCodeResponse(
            exercise_id=created_exercise.id,
            course_id=created_exercise.course_id,
            name=created_exercise.name,
            description=created_exercise.description,
            topic=created_exercise.topic,
            questions=code_questions,
            max_score=created_exercise.max_score,
            type=ExerciseType(created_exercise.type),
            time_open=created_exercise.time_open,
            time_close=created_exercise.time_close,
            time_limit=created_exercise.time_limit,
            attempts_allowed=created_exercise.attempts_allowed,
            grading_method=GradingMethodType(created_exercise.grading_method),
            shuffle_questions=created_exercise.shuffle_questions,
            shuffle_answers=created_exercise.shuffle_answers,
            review_after_completion=created_exercise.review_after_completion,
            show_correct_answers=created_exercise.show_correct_answers,
            penalty_per_attempt=created_exercise.penalty_per_attempt,
            pass_mark=created_exercise.pass_mark,
        ),
        message="Successfully created the code exercise.",
    )

@router.get("/{exercise_id}/code", response_model=Ok[ExerciseCodeResponse])
async def get_code_exercise(
    exercise_id: UUID,
    token: str = Depends(oauth2_scheme),
    exercises_controller: ExercisesController = Depends(InternalProvider().get_exercises_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
):
    """
    Retrieves an existing code exercise by ID.
    """
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    # Fetch the exercise
    exercise = await exercises_controller.exercises_repository.first(
        where_=[Exercises.id == exercise_id]
    )
    if not exercise:
        raise NotFoundException(message="Exercise not found for the given ID.")
    if exercise.type != ExerciseType.code:
        raise BadRequestException(message="This is not a code exercise.")
    
    # Prepare code modal objects from the stored questions data
    code_questions = []
    for q in exercise.questions:
        code_questions.append(
            CodeModel(
                question=q["question"],
                testcases=[
                    TestCaseModel(
                        inputs=t["inputs"],
                        output=t["output"],
                        is_hidden=t.get("is_hidden", False),
                        description=t.get("description", "")
                    ) for t in q.get("testcases", [])
                ],
                starter_code=q.get("starter_code", ""),
                solution_code=q.get("solution_code", ""),
                hints=q.get("hints", []),
                score=q.get("score", 10),
                difficulty=DifficultyLevel(q.get("difficulty", "medium")),
                allowed_languages=q.get("allowed_languages", []),
                time_limit_seconds=q.get("time_limit_seconds", 5),
                memory_limit_mb=q.get("memory_limit_mb", 256),
            )
        )

    # Return the response
    return Ok(
        data=ExerciseCodeResponse(
            exercise_id=exercise.id,
            course_id=exercise.course_id,
            name=exercise.name,
            description=exercise.description,
            topic=exercise.topic,
            questions=code_questions,
            max_score=exercise.max_score,
            type=ExerciseType(exercise.type),
            time_open=exercise.time_open,
            time_close=exercise.time_close,
            time_limit=exercise.time_limit,
            attempts_allowed=exercise.attempts_allowed,
            grading_method=GradingMethodType(exercise.grading_method) if exercise.grading_method else GradingMethodType.highest,
            shuffle_questions=exercise.shuffle_questions,
            shuffle_answers=exercise.shuffle_answers,
            review_after_completion=exercise.review_after_completion,
            show_correct_answers=exercise.show_correct_answers,
            penalty_per_attempt=exercise.penalty_per_attempt,
            pass_mark=exercise.pass_mark,
        ),
        message="Successfully retrieved the code exercise.",
    )

@router.put("/{exercise_id}/code", response_model=Ok[ExerciseCodeResponse])
async def update_code_exercise(
    exercise_id: UUID,
    body: ExerciseCodeRequest,
    token: str = Depends(oauth2_scheme),
    exercises_controller: ExercisesController = Depends(InternalProvider().get_exercises_controller),
    course_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
):
    """
    Updates an existing code exercise with new details and questions.
    """
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    user = await professor_controller.professor_repository.first(where_=[Professor.id == user_id])
    if not user:
        raise NotFoundException(message="Only professors have the permission to update this exercise.")
    
    # Validate exercise existence
    exercise = await exercises_controller.exercises_repository.first(
        where_=[Exercises.id == exercise_id]
    )
    if not exercise:
        raise NotFoundException(message="Exercise not found for the given ID.")
    
    if exercise.type != ExerciseType.code:
        raise BadRequestException(message="This is not a code exercise.")

    # Validate course existence
    course = await course_controller.courses_repository.first(
        where_=[Courses.id == body.course_id],
    )
    if not course:
        raise NotFoundException(message="Course not found for the given ID.")
    if not course.professor_id == user.id:
        raise BadRequestException(message="You are not allowed to update exercise for this course.")
    
    # Validate and process questions
    questions_data = []
    total_score = 0
    for question in body.questions:
        if not all([question.question, question.testcases]):
            raise BadRequestException(message="Each question must have both question text and test cases")
        
        for testcase in question.testcases:
            if not all([testcase.inputs is not None, testcase.output is not None]):
                raise BadRequestException(message="Each test case must have both input and output fields")
        
        # Add question data with all required fields
        question_data = {
            "question": question.question,
            "testcases": [t.model_dump() for t in question.testcases],
            "starter_code": getattr(question, 'starter_code', ''),
            "solution_code": getattr(question, 'solution_code', ''),
            "hints": getattr(question, 'hints', []),
            "score": getattr(question, 'score', 10),
            "difficulty": getattr(question, 'difficulty', DifficultyLevel.medium).value,
            "allowed_languages": getattr(question, 'allowed_languages', []),
            "time_limit_seconds": getattr(question, 'time_limit_seconds', 5),
            "memory_limit_mb": getattr(question, 'memory_limit_mb', 256),
        }
        questions_data.append(question_data)
        total_score += question_data["score"]

    # Prepare updated exercise data
    update_data = {
        "name": body.name,
        "description": body.description,
        "topic": body.topic,
        "type": body.type.value,
        "course_id": body.course_id,
        "questions": questions_data,
        "max_score": body.max_score or total_score,
        "time_open": getattr(body, 'time_open', None),
        "time_close": getattr(body, 'time_close', None),
        "time_limit": getattr(body, 'time_limit', None),
        "attempts_allowed": getattr(body, 'attempts_allowed', None),
        "grading_method": getattr(body, 'grading_method', GradingMethodType.highest).value,
        "shuffle_questions": getattr(body, 'shuffle_questions', False),
        "shuffle_answers": getattr(body, 'shuffle_answers', False),
        "review_after_completion": getattr(body, 'review_after_completion', True),
        "show_correct_answers": getattr(body, 'show_correct_answers', False),
        "penalty_per_attempt": getattr(body, 'penalty_per_attempt', 0.0),
        "pass_mark": getattr(body, 'pass_mark', 0.0),
    }

    # Update the exercise
    updated_exercise = await exercises_controller.exercises_repository.update(
        where_=[Exercises.id == exercise_id],
        attributes=update_data,
        commit=True,
    )

    # Prepare code modal objects
    code_questions = []
    for q in questions_data:
        code_questions.append(
            CodeModel(
                question=q["question"],
                testcases=[
                    TestCaseModel(
                        inputs=t["inputs"],
                        output=t["output"],
                        is_hidden=t.get("is_hidden", False),
                        description=t.get("description", "")
                    ) for t in q["testcases"]
                ],
                starter_code=q.get("starter_code", ""),
                solution_code=q.get("solution_code", ""),
                hints=q.get("hints", []),
                score=q.get("score", 10),
                difficulty=DifficultyLevel(q.get("difficulty", "medium")),
                allowed_languages=q.get("allowed_languages", []),
                time_limit_seconds=q.get("time_limit_seconds", 5),
                memory_limit_mb=q.get("memory_limit_mb", 256),
            )
        )

    # Return the response
    return Ok(
        data=ExerciseCodeResponse(
            exercise_id=updated_exercise.id,
            course_id=updated_exercise.course_id,
            name=updated_exercise.name,
            description=updated_exercise.description,
            topic=updated_exercise.topic,
            questions=code_questions,
            max_score=updated_exercise.max_score,
            type=ExerciseType(updated_exercise.type),
            time_open=updated_exercise.time_open,
            time_close=updated_exercise.time_close,
            time_limit=updated_exercise.time_limit,
            attempts_allowed=updated_exercise.attempts_allowed,
            grading_method=GradingMethodType(updated_exercise.grading_method),
            shuffle_questions=updated_exercise.shuffle_questions,
            shuffle_answers=updated_exercise.shuffle_answers,
            review_after_completion=updated_exercise.review_after_completion,
            show_correct_answers=updated_exercise.show_correct_answers,
            penalty_per_attempt=updated_exercise.penalty_per_attempt,
            pass_mark=updated_exercise.pass_mark,
        ),
        message="Successfully updated the code exercise.",
    )

@router.delete("/{exercise_id}/code", response_model=Ok[ExerciseCodeResponse])
async def delete_code_exercise(
    exercise_id: UUID,
    token: str = Depends(oauth2_scheme),
    exercises_controller: ExercisesController = Depends(InternalProvider().get_exercises_controller),
    course_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    student_exercise_controller: StudentExercisesController = Depends(InternalProvider().get_studentexercises_controller),
):
    """
    Deletes an existing code exercise by ID.
    """
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    user = await professor_controller.professor_repository.first(where_=[Professor.id == user_id])
    if not user:
        raise NotFoundException(message="Only professors have the permission to delete this exercise.")
    
    # Validate exercise existence
    exercise = await exercises_controller.exercises_repository.first(
        where_=[Exercises.id == exercise_id],
        relations=[Exercises.course,
                   Exercises.student_exercises],
    )
    if not exercise:
        raise NotFoundException(message="Exercise not found for the given ID.")
    
    if exercise.type != ExerciseType.code:
        raise BadRequestException(message="This is not a code exercise.")
        
    if not exercise.course:
        raise NotFoundException(message="Exercise not associated with any course.")
    
    if not exercise.course.professor_id == user.id:
        raise BadRequestException(message="You are not allowed to delete exercise for this course.")
    
    # Delete student exercises first
    if exercise.student_exercises:
        for student_exercise in exercise.student_exercises:
            await student_exercise_controller.student_exercises_repository.delete(
                where_=[StudentExercises.id == student_exercise.id]
            )
    
    # Delete the exercise
    await exercises_controller.exercises_repository.delete(
        where_=[Exercises.id == exercise_id],
    )
    
    await exercises_controller.exercises_repository.session.commit()
    
    # Prepare response data
    code_questions = []
    for q in exercise.questions:
        code_questions.append(
            CodeModel(
                question=q["question"],
                testcases=[
                    TestCaseModel(
                        inputs=t["inputs"],
                        output=t["output"],
                        is_hidden=t.get("is_hidden", False),
                        description=t.get("description", "")
                    ) for t in q.get("testcases", [])
                ],
                starter_code=q.get("starter_code", ""),
                solution_code=q.get("solution_code", ""),
                hints=q.get("hints", []),
                score=q.get("score", 10),
                difficulty=DifficultyLevel(q.get("difficulty", "medium")),
                allowed_languages=q.get("allowed_languages", []),
                time_limit_seconds=q.get("time_limit_seconds", 5),
                memory_limit_mb=q.get("memory_limit_mb", 256),
            )
        )
    
    # Return success response
    return Ok(
        data=ExerciseCodeResponse(
            exercise_id=exercise.id,
            course_id=exercise.course_id,
            name=exercise.name,
            description=exercise.description,
            topic=exercise.topic,
            questions=code_questions,
            max_score=exercise.max_score,   
            type=ExerciseType(exercise.type),
            time_open=exercise.time_open,
            time_close=exercise.time_close,
            time_limit=exercise.time_limit,
            attempts_allowed=exercise.attempts_allowed,
            grading_method=GradingMethodType(exercise.grading_method) if exercise.grading_method else GradingMethodType.highest,
            shuffle_questions=exercise.shuffle_questions,
            shuffle_answers=exercise.shuffle_answers,
            review_after_completion=exercise.review_after_completion,
            show_correct_answers=exercise.show_correct_answers,
            penalty_per_attempt=exercise.penalty_per_attempt,
            pass_mark=exercise.pass_mark,
        ),
        message="Code exercise successfully deleted."
    )


@router.get(
    "/code/{coding_exercise_id}/conversation/messages",
    response_model=Ok[list[MessageResponseSchema]]
)
async def get_coding_assistant_conversation_messages(
    coding_exercise_id: UUID = Path(...),
    token: str = Depends(oauth2_scheme),
    ctrl: ctrl.ExercisesController = Depends(InternalProvider().get_exercises_controller)
):
    payload = verify_token(token)
    user_id = UUID(payload.get("sub"))

    messages = await ctrl.get_coding_assistant_conversation_messages(
        coding_exercise_id=coding_exercise_id, user_id=user_id
    )

    return Ok(
        data=[MessageResponseSchema.model_validate(msg) for msg in messages]
    )

@router.post(
    "/code/{coding_exercise_id}/conversation:invokeAssistant",
    response_class=StreamingResponse
)
async def ask_coding_assistant_stream(
    body: InvokeCodingAssistantSchema,
    coding_exercise_id: UUID = Path(...),
    token: str = Depends(oauth2_scheme),
    ctrl: ctrl.ExercisesController = Depends(InternalProvider().get_exercises_controller)
):
    payload = verify_token(token)
    user_id = UUID(payload.get("sub"))
    # The request body should contain both the user message (content) and their current work (user_solution)
    generator = ctrl.invoke_coding_assistant(
        user_id=user_id,
        coding_exercise_id=coding_exercise_id,
        content=body.content,
        user_solution=body.user_solution,
    )
    # Stream the response using text/event-stream media type.
    return StreamingResponse(generator, media_type="text/event-stream")


@router.post("/{exercise_id}/language-configs", response_model=Ok[ProgrammingLanguageConfigResponse])
async def add_language_config(
    body: ProgrammingLanguageConfigCreateRequest,
    exercise_id: UUID = Path(...),
    controller: ProgrammingLanguageConfigController = Depends(InternalProvider().get_pg_config_controller),
):
    attributes = {
        **body.model_dump(), "exercise_id": exercise_id
    }
    pg_config = await controller.create(attributes=attributes)
    return Ok(data=ProgrammingLanguageConfigResponse.model_validate(pg_config))

@router.get("/{exercise_id}/language-configs", response_model=Ok[list[ProgrammingLanguageConfigResponse]])
async def get_language_configs(
    exercise_id: UUID,
    controller: ProgrammingLanguageConfigController = Depends(InternalProvider().get_pg_config_controller)
):
    # TODO
    language_configs = await controller.get_many(
        where_=[ProgrammingLanguageConfig.exercise_id == exercise_id]
    )
    return Ok(data=[ProgrammingLanguageConfigResponse.model_validate(lc) for lc in language_configs])

@router.get("/{exercise_id}/language-configs/{lang_cfg_id}", response_model=Ok[ProgrammingLanguageConfigResponse])
async def put_lang_cfg(
    exercise_id: UUID,
    lang_cfg_id: UUID,
    body: ProgrammingLanguageConfigCreateRequest,
    controller: ProgrammingLanguageConfigController = Depends(InternalProvider().get_pg_config_controller)
):
    # TODO
    ...

@router.delete("/{exercise_id}/language-configs/{lang_cfg_id}", response_model=Ok[ProgrammingLanguageConfigResponse])
async def delete_language_configs(
    exercise_id: UUID,
    lang_cfg_id: UUID,
    controller: ProgrammingLanguageConfigController = Depends(InternalProvider().get_pg_config_controller)
):
    # TODO
    ...

@router.post("/{exercise_id}/testcases", response_model=Ok[ProgrammingTestCaseResponse])
async def create_testcase(
    exercise_id: UUID,
    body: ProgrammingTestCaseCreateRequest,
    controller: ctrl.ProgrammingTestCaseController = Depends(InternalProvider().get_programming_tc_controller)
):
    attributes = body.model_dump()
    attributes["exercise_id"] = exercise_id
    testcase = await controller.create(attributes=attributes)
    return Ok(data=ProgrammingTestCaseResponse.model_validate(testcase))

@router.get("/{testcase_id}", response_model=Ok[ProgrammingTestCaseResponse])
async def get_testcase(
    testcase_id: UUID,
    controller: ctrl.ProgrammingTestCaseController = Depends(InternalProvider().get_programming_tc_controller)
):
    testcase = await controller.repository.first(where_=[ProgrammingTestCase.id == testcase_id])
    if not testcase:
        raise NotFoundException("Programming TestCase not found")
    return Ok(data=ProgrammingTestCaseResponse.model_validate(testcase))

@router.get("/", response_model=Ok[list[ProgrammingTestCaseResponse]])
async def get_testcases(
    limit: int = Query(10, ge=1),
    offset: int = Query(0, ge=0),
    controller: ctrl.ProgrammingTestCaseController = Depends(InternalProvider().get_programming_tc_controller)
):
    testcases = await controller.get_many(limit=limit, offset=offset)
    return Ok(data=[ProgrammingTestCaseResponse.model_validate(tc) for tc in testcases])

@router.put("/{exercise_id}/testcases/{testcase_id}", response_model=Ok[ProgrammingTestCaseResponse])
async def update_testcase(
    exercise_id: UUID,
    testcase_id: UUID,
    body: ProgrammingTestCaseCreateRequest,
    controller: ctrl.ProgrammingTestCaseController = Depends(InternalProvider().get_programming_tc_controller)
):
    attributes = body.model_dump(exclude_unset=True)
    updated_testcase = await controller.repository.update(
        where_=[ProgrammingTestCase.id == testcase_id, ProgrammingTestCase.exercise_id == exercise_id],
        attributes=attributes,
        commit=True
    )
    if not updated_testcase:
        raise NotFoundException("Programming TestCase not found")
    return Ok(data=ProgrammingTestCaseResponse.model_validate(updated_testcase))

@router.delete("/{exercise_id}/testcases/{testcase_id}", response_model=Ok[ProgrammingTestCaseResponse])
async def delete_testcase(
    testcase_id: UUID = Path(...),
    exercise_id: UUID = Path(...),
    controller: ctrl.ProgrammingTestCaseController = Depends(InternalProvider().get_programming_tc_controller)
):
    testcase = await controller.repository.first(
        where_=[ProgrammingTestCase.id == testcase_id, ProgrammingTestCase.exercise_id == exercise_id]
    )
    if not testcase:
        raise NotFoundException("Programming TestCase not found")
    await controller.repository.delete(where_=[ProgrammingTestCase.id == testcase_id])
    await controller.repository.session.commit()
    return Ok(data=ProgrammingTestCaseResponse.model_validate(testcase))

@router.post(
    "/{exercise_id}/programming-submissions",
    response_model=Ok[ProgrammingSubmissionCreateResponse],
    status_code=201
)
async def submit_code(
    exercise_id: UUID,
    body: ProgrammingSubmissionCreateRequest,
    token : str = Depends(oauth2_scheme),
    user_controller: StudentController = Depends(InternalProvider().get_student_controller),
    exercise_controller: ExercisesController = Depends(InternalProvider().get_exercises_controller),
):
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    users = await user_controller.get_many(where_=[Student.id == user_id])
    assert users != []
    user = users[0]

    submission = await exercise_controller.create_coding_submission(
        user_id=user.id,
        exercise_id=exercise_id,
        user_solution=body.code,
        judge0_lang_id=body.judge0_language_id
    )

    return Ok(data=ProgrammingSubmissionCreateResponse.model_validate(submission))

@router.get("/{exercise_id}/coding-submissions/{submission_id}/status", response_model=Ok[ProgrammingSubmissionResponse])
async def get_coding_submission_status(
    submission_id: UUID,
    token : str = Depends(oauth2_scheme),
    exercise_controller: ExercisesController = Depends(InternalProvider().get_exercises_controller)
):
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    submission = await exercise_controller.submission_repo.first(
        where_=[ProgrammingSubmission.id == submission_id]
    )
    if not submission:
        raise NotFoundException(message="Submission not found.")
    return Ok(data=ProgrammingSubmissionResponse.model_validate(submission))

@router.get("/{exercise_id}/coding-submissions", response_model=Ok[list[ProgrammingSubmissionItemSchema]])
async def get_coding_submissions(
    exercise_id: UUID = Path(...),
    token : str = Depends(oauth2_scheme),
    exercise_controller: ExercisesController = Depends(InternalProvider().get_exercises_controller)
):
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    submission_repo = exercise_controller.submission_repo
    submissions = await submission_repo.get_many(
        where_=[ProgrammingSubmission.exercise_id == exercise_id, Student.id == user_id]
    )

    return Ok(data=[ProgrammingSubmissionItemSchema.model_validate(submission) for submission in submissions])
