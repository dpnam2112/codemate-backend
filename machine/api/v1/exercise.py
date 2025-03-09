from fastapi import APIRouter, Depends
from core.response import Ok
from machine.schemas.requests.exercise import  *
from machine.schemas.responses.exercise import  *
from machine.providers import InternalProvider
from machine.controllers import *
from machine.models import *
from core.exceptions import NotFoundException, BadRequestException
from uuid import UUID
from fastapi import  Depends
from fastapi.security import OAuth2PasswordBearer
from core.utils.auth_utils import verify_token

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
@router.delete("/quizzes/{exercise_id}", response_model=Ok[ExerciseQuizResponse])
async def delete_exercise(
    exercise_id: UUID,
    token: str = Depends(oauth2_scheme),
    exercises_controller: ExercisesController = Depends(InternalProvider().get_exercises_controller),
    course_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
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
        relations=[Exercises.course],
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
    # Return success response
    return Ok(
        data=ExerciseQuizResponse(
            exercise_id=exercise.id,
            name=exercise.name,
            description=exercise.description,
            deadline=exercise.deadline,
            time=exercise.time,
            topic=exercise.topic,
            difficulty=exercise.difficulty,
            type=exercise.type,
            max_score=exercise.max_score,
            course_id=exercise.course_id,
            questions=[
                QuizModal(
                    question=q["question"],
                    answer=q["answer"],
                    options=q["options"],
                    type=q["type"],
                    score=q["score"],
                ).model_dump()  # Convert to dictionary
                for q in exercise.questions
            ],
        ),
        message="Exercise successfully deleted.")
@router.post("/code", response_model=Ok[ExerciseCodeResponse])
async def add_exercises(
    body: ExerciseCodeRequest,
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
    user = await professor_controller.professor_repository.first(where_=[Professor.id == user_id])
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
    for question in body.questions:
        if not all([question.question, question.testcases]):
            for testcase in question.testcases:
                if not all([testcase.input, testcase.output]):
                    raise BadRequestException(message="Each test case must have both input and output fields")
            raise BadRequestException(message="Each question must have test cases")
        questions_data.append(question.model_dump())

    # Prepare exercise data
    exercise_data = {
        "name": body.name,
        "description": body.description,
        "deadline": body.deadline,
        "time": body.time,
        "topic": body.topic,
        "difficulty": body.difficulty,
        "max_score": body.max_score,
        "type": body.type,
        "course_id": body.course_id,
        "questions": questions_data,
    }

    # Create the exercise
    created_exercise = await exercises_controller.exercises_repository.create(
        exercise_data, commit=True
    )

    # Return the response
    return Ok(
        data=ExerciseCodeResponse(
            exercise_id=created_exercise.id,
            name=created_exercise.name,
            description=created_exercise.description,
            deadline=created_exercise.deadline,
            time=created_exercise.time,
            topic=created_exercise.topic,
            difficulty=created_exercise.difficulty,
            type=created_exercise.type,
            max_score=created_exercise.max_score,
            course_id=created_exercise.course_id,
            questions=[
                CodeModel(
                    question=q["question"],
                    testcases= [
                        TestCaseModel(
                            input=t["input"],
                            output=t["output"],
                        ).model_dump()
                    for t in q["testcases"]
                ]
                ).model_dump()  # Convert to dictionary
                for q in exercise_data["questions"]
            ],
        ),
        message="Successfully created the exercise.",
    )
@router.put("/code/{exercise_id}", response_model=Ok[ExerciseCodeResponse])
async def update_code_exercise(
    exercise_id: UUID,
    body: ExerciseCodeRequest,
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
    user = await professor_controller.professor_repository.first(where_=[Professor.id == user_id])
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
        raise BadRequestException(message="You are not allowed to create exercise for this course.")
    
    # Validate and process questions
    questions_data = []
    for question in body.questions:
        if not all([question.question, question.testcases]):
            for testcase in question.testcases:
                if not all([testcase.input, testcase.output]):
                    raise BadRequestException(message="Each test case must have both input and output fields")
            raise BadRequestException(message="Each question must have test cases")
        questions_data.append(question.model_dump())

    # Prepare exercise data
    exercise.name = body.name
    exercise.description = body.description
    exercise.deadline = body.deadline
    exercise.time = body.time
    exercise.topic = body.topic
    exercise.difficulty = body.difficulty
    exercise.type = body.type
    exercise.max_score = body.max_score
    exercise.questions = questions_data

    # Update the exercise
    updated_exercise = await exercises_controller.exercises_repository.update(
        where_=[Exercises.id == exercise_id],
        attributes={
            "name": exercise.name,
            "description": exercise.description,
            "deadline": exercise.deadline,
            "time": exercise.time,
            "topic": exercise.topic,
            "difficulty": exercise.difficulty,
            "type": exercise.type,
            "max_score": exercise.max_score,
            "questions": exercise.questions,
        },
        commit=True,
    )

    # Return the response
    return Ok(
        data=PutExerciseCodeResponse(
            exercise_id=updated_exercise.id,
            name=updated_exercise.name,
            description=updated_exercise.description,
            deadline=updated_exercise.deadline,
            time=updated_exercise.time,
            topic=updated_exercise.topic,
            difficulty=updated_exercise.difficulty,
            type=updated_exercise.type,
            max_score=updated_exercise.max_score,
            questions=[
                CodeModel(
                    question=q["question"],
                    testcases= [
                        TestCaseModel(
                            input=t["input"],
                            output=t["output"],
                        ).model_dump()
                    for t in q["testcases"]
                ]
                ).model_dump()  # Convert to dictionary
                for q in updated_exercise.questions
            ],
        ),
        message="Successfully created the exercise.",
    )
@router.delete("/code/{exercise_id}", response_model=Ok[ExerciseCodeResponse])
async def delete_exercise(
    exercise_id: UUID,
    token: str = Depends(oauth2_scheme),
    exercises_controller: ExercisesController = Depends(InternalProvider().get_exercises_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
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
        relations=[Exercises.course],
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
    # Return success response
    return Ok(
        data=ExerciseCodeResponse(
            exercise_id=exercise.id,
            name=exercise.name,
            description=exercise.description,
            deadline=exercise.deadline,
            time=exercise.time,
            topic=exercise.topic,
            difficulty=exercise.difficulty,
            type=exercise.type,
            max_score=exercise.max_score,
            course_id=exercise.course_id,
            questions=[
                CodeModel(
                    question=q["question"],
                    testcases= [
                        TestCaseModel(
                            input=t["input"],
                            output=t["output"],
                        ).model_dump()
                    for t in q["testcases"]
                ]
                ).model_dump()  # Convert to dictionary
                for q in exercise.questions
            ],
        ),
        message="Exercise successfully deleted.")
