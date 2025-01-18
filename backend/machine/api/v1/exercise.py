from fastapi import APIRouter, Depends
from core.response import Ok
from machine.schemas.requests.exercise import  ExerciseRequest, QuestionModel, ExerciseCodeRequest, CodeModel, TestCaseModel
from machine.schemas.responses.exercise import  ExerciseQuizResponse, ExerciseCodeResponse
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
        if not all([question.question, question.answer, question.options, question.type]):
            raise BadRequestException(
                message=f"Invalid question data: {question.model_dump()}. All fields must be provided.",
            )
        question_data = {
            **question.model_dump(),
            "type": question.type.value, 
        }
        questions_data.append(question_data)

    # Prepare exercise data
    exercise_data = {
        "name": body.name,
        "description": body.description,
        "deadline": body.deadline,
        "time": body.time,
        "topic": body.topic,
        "attempts": body.attempts,
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
        data=ExerciseQuizResponse(
            exercise_id=created_exercise.id,
            name=created_exercise.name,
            description=created_exercise.description,
            deadline=created_exercise.deadline,
            time=created_exercise.time,
            topic=created_exercise.topic,
            attempts=created_exercise.attempts,
            difficulty=created_exercise.difficulty,
            type=created_exercise.type,
            max_score=created_exercise.max_score,
            course_id=created_exercise.course_id,
            questions=[
                QuestionModel(
                    question=q["question"],
                    answer=q["answer"],
                    options=q["options"],
                    type=q["type"],
                    score=q["score"],
                ).model_dump()  # Convert to dictionary
                for q in exercise_data["questions"]
            ],
        ),
        message="Successfully created the exercise.",
    )
@router.put("/quizzes/{exercise_id}", response_model=Ok[ExerciseQuizResponse])
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
    for question in body.questions:
        if not all([question.question, question.answer, question.options, question.type]):
            raise BadRequestException(
                message=f"Invalid question data: {question.model_dump()}. All fields must be provided.",
            )
        question_data = {
            **question.model_dump(),
            "type": question.type.value,  # Convert enum to string
        }
        questions_data.append(question_data)

    # Prepare updated exercise data
    exercise.name = body.name
    exercise.description = body.description
    exercise.deadline = body.deadline
    exercise.time = body.time
    exercise.topic = body.topic
    exercise.attempts = body.attempts
    exercise.difficulty = body.difficulty
    exercise.type = body.type
    exercise.max_score = body.max_score
    exercise.course_id = body.course_id
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
            "attempts": exercise.attempts,
            "difficulty": exercise.difficulty,
            "type": exercise.type,
            "max_score": exercise.max_score,
            "course_id": exercise.course_id,
            "questions": exercise.questions,
        },
        commit=True,
    )

    # Return the response
    return Ok(
        data=ExerciseQuizResponse(
            exercise_id=updated_exercise.id,
            name=updated_exercise.name,
            description=updated_exercise.description,
            deadline=updated_exercise.deadline,
            time=updated_exercise.time,
            topic=updated_exercise.topic,
            attempts=updated_exercise.attempts,
            difficulty=updated_exercise.difficulty,
            type=updated_exercise.type,
            max_score=updated_exercise.max_score,
            course_id=updated_exercise.course_id,
            questions=[
                QuestionModel(
                    question=q["question"],
                    answer=q["answer"],
                    options=q["options"],
                    type=q["type"],
                    score=q["score"],
                ).model_dump()  # Convert to dictionary
                for q in updated_exercise.questions
            ],
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
            attempts=exercise.attempts,
            difficulty=exercise.difficulty,
            type=exercise.type,
            max_score=exercise.max_score,
            course_id=exercise.course_id,
            questions=[
                QuestionModel(
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
        "attempts": body.attempts,
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
            attempts=created_exercise.attempts,
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
    exercise.attempts = body.attempts
    exercise.difficulty = body.difficulty
    exercise.type = body.type
    exercise.max_score = body.max_score
    exercise.course_id = body.course_id
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
            "attempts": exercise.attempts,
            "difficulty": exercise.difficulty,
            "type": exercise.type,
            "max_score": exercise.max_score,
            "course_id": exercise.course_id,
            "questions": exercise.questions,
        },
        commit=True,
    )

    # Return the response
    return Ok(
        data=ExerciseCodeResponse(
            exercise_id=updated_exercise.id,
            name=updated_exercise.name,
            description=updated_exercise.description,
            deadline=updated_exercise.deadline,
            time=updated_exercise.time,
            topic=updated_exercise.topic,
            attempts=updated_exercise.attempts,
            difficulty=updated_exercise.difficulty,
            type=updated_exercise.type,
            max_score=updated_exercise.max_score,
            course_id=updated_exercise.course_id,
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
            attempts=exercise.attempts,
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
