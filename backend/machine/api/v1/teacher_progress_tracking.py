from typing import List
from core.response import Ok
from machine.models import *
from fastapi import APIRouter, Depends
from machine.schemas.requests import *
from machine.schemas.responses.progress_tracking import *
from machine.controllers import *
from machine.providers import InternalProvider
from core.exceptions import NotFoundException, BadRequestException
from fastapi.security import OAuth2PasswordBearer
from core.utils.auth_utils import verify_token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
router = APIRouter(prefix="/teacher_progress_tracking", tags=["teacher_progress_tracking"])

@router.get("/courses", response_model=Ok[GetCoursesListResponse])
async def get_courses(
    token: str = Depends(oauth2_scheme),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
):
    """
    Get the list of courses
    """
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    
    user = await professor_controller.professor_repository.first(where_=[Professor.id == user_id])
    
    if not user:  
        raise NotFoundException(message="Only professors have the permission to create lesson.")
    
    courses = await courses_controller.courses_repository.get_many(
        where_=[Courses.professor_id == user_id],
    )
    if not courses:
        raise NotFoundException(message="No courses found.")

    course_name_list = [
        CourseNameResponse(course_id=course.id, course_name=course.name)
        for course in courses
    ]
    return Ok(data=GetCoursesListResponse(course_name_list=course_name_list), message="Successfully fetched the course list.")
@router.get("/courses/{course_id}/exercises", response_model=Ok[GetExercisesListResponse])
async def get_exercises_name(
    course_id: UUID,
    token: str = Depends(oauth2_scheme),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
):
    """
    Get the list of courses
    """
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    
    user = await professor_controller.professor_repository.first(where_=[Professor.id == user_id])
    
    if not user:  
        raise NotFoundException(message="Only professors have the permission to create lesson.")
    
    courses = await courses_controller.courses_repository.first(
        where_=[Courses.id == course_id],
        relations=[Courses.exercises]
    )
    if not courses:
        raise NotFoundException(message="No courses found.")
    exercises_name_list =[]
    if courses.exercises:
        exercises_name_list = [
            ExerciseNameResponse(exercise_id=exercise.id, exercise_name=exercise.name)
            for exercise in courses.exercises
        ]

    return Ok(data=GetExercisesListResponse(exercises_name_list=exercises_name_list), message="Successfully fetched the course list.")

@router.get("/courses/{course_id}/grades", response_model=Ok[GetCourseGradesResponse])
async def get_grades(
    course_id: UUID,
    token: str = Depends(oauth2_scheme),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    student_courses_controller: StudentCoursesController = Depends(InternalProvider().get_studentcourses_controller),
    student_exercises_controller: StudentExercisesController = Depends(InternalProvider().get_studentexercises_controller),
    recommend_lessons_controller: RecommendLessonsController = Depends(InternalProvider().get_recommendlessons_controller),
    lessons_controller: LessonsController = Depends(InternalProvider().get_lessons_controller),
    learning_paths_controller: LearningPathsController = Depends(InternalProvider().get_learningpaths_controller),
    exercises_controller: ExercisesController = Depends(InternalProvider().get_exercises_controller),
):
    """
    Get the grades for a course
    """
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    user = await professor_controller.professor_repository.first(where_=[Professor.id == user_id])

    if not user:
        raise NotFoundException(message="Only professors have the permission to get grades.")

    course = await courses_controller.courses_repository.first(
        where_=[Courses.id == course_id],
        relations=[Courses.student_courses, Courses.exercises, Courses.professor],
    )
    if not course:
        raise NotFoundException(message="No courses found.")
    if not course.professor_id == user_id:
        raise BadRequestException(message="You are not authorized to access the grades course.")
    student_courses = await student_courses_controller.student_courses_repository.get_many(
        where_=[StudentCourses.course_id == course_id]
    )
    if not student_courses:
        raise NotFoundException(message="No students found in the course.")

    students_list = []

    for student_course in student_courses:
        student = await student_controller.student_repository.first(
            where_=[Student.id == student_course.student_id]
        )
        student_id = student.id
        student_name = student.name

        learning_path_progress = await learning_paths_controller.learning_paths_repository.first(
            where_=[LearningPaths.course_id == course_id, LearningPaths.student_id == student_id]
        )
        learning_path = None
        if learning_path_progress:
            recommend_lessons = await recommend_lessons_controller.recommend_lessons_repository.get_many(
                where_=[RecommendLessons.learning_path_id == learning_path_progress.id]
            )
            lessons = []
            if recommend_lessons:
                for recommend_lesson in recommend_lessons:
                    lesson = await lessons_controller.lessons_repository.first(
                        where_=[Lessons.id == recommend_lesson.lesson_id]
                    )
                    if lesson:
                        lessons.append(LessonInLearningPath(
                            lesson_id=recommend_lesson.id,
                            lesson_name=lesson.title,
                            description=lesson.description,
                            progress=recommend_lesson.progress,
                        ))

            learning_path = LearningPathProgressInCourse(
                    learning_path_id=learning_path_progress.id,
                    progress=learning_path_progress.progress,
                    objective=learning_path_progress.objective,
                    lessons=lessons,
            )

        exercises = await exercises_controller.exercises_repository.get_many(
            where_=[Exercises.course_id == course_id],
        )
        exercise_student = []
        for exercise in exercises:
            student_exercise = await student_exercises_controller.student_exercises_repository.first(
                where_=[StudentExercises.exercise_id == exercise.id, StudentExercises.student_id == student_id],
            )
            if not student_exercise:
                score = 0
            else:
                score = student_exercise.score
            exercise_student.append(ExeriseStudentProgressInCourse(
                exercise_id=exercise.id,
                exercise_name=exercise.name,
                score=score,
            ))

        total_score = sum(exercise.score for exercise in exercise_student)
        average_score = total_score / len(exercise_student) if exercise_student else 0.0

        students_list.append(StudentProgressInCourse(
            student_id=student_id,
            student_name=student_name,
            exercises=exercise_student,
            learning_path=learning_path,
            average_score=average_score,
        ))

    return Ok(data=GetCourseGradesResponse(students_list=students_list), message="Successfully fetched the grades course.")

@router.get("/courses/{course_id}/exercises/{exercise_id}/grades", response_model=Ok[GetExerciseGradesResponse])
async def get_exercise_grades(
    course_id: UUID,
    exercise_id: UUID,
    token: str = Depends(oauth2_scheme),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    student_courses_controller: StudentCoursesController = Depends(InternalProvider().get_studentcourses_controller),
    student_exercises_controller: StudentExercisesController = Depends(InternalProvider().get_studentexercises_controller),
    exercises_controller: ExercisesController = Depends(InternalProvider().get_exercises_controller),
):
    """
    Get the grades for a course
    """
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")

    user = await professor_controller.professor_repository.first(where_=[Professor.id == user_id])

    if not user:
        raise NotFoundException(message="Only professors have the permission to get grades.")

    course = await courses_controller.courses_repository.first(
        where_=[Courses.id == course_id],
        relations=[Courses.student_courses, Courses.exercises],
    )
    if not course:
        raise NotFoundException(message="No courses found.")
    
    if course.professor_id != user_id:
        raise BadRequestException(message="You are not authorized to access the grades course.")
    
    student_courses = await student_courses_controller.student_courses_repository.get_many(
        where_=[StudentCourses.course_id == course_id]
    )
    if not student_courses:
        raise NotFoundException(message="No students found in the course.")

    students_list = []

    for student_course in student_courses:
        student = await student_controller.student_repository.first(
            where_=[Student.id == student_course.student_id]
        )
        student_id = student.id
        student_name = student.name

        exercise = await exercises_controller.exercises_repository.first(
            where_=[Exercises.id == exercise_id],
        )
        student_exercise = await student_exercises_controller.student_exercises_repository.first(
            where_=[StudentExercises.exercise_id == exercise.id, StudentExercises.student_id == student_id],
        )
        if not student_exercise:
            score = 0
            question_answers = []
        else:
            score = student_exercise.score
            question_answers = [
                AnswerQuizExercise(
                    question=answer.get('question', '') if isinstance(answer, dict) else '',
                    answers=answer.get('answers', []) if isinstance(answer, dict) else []
                ) for answer in (student_exercise.answer or [])
            ]
        
        students_list.append(StudentProgressInExercise(
            student_id=student_id,
            student_name=student_name,
            score=score,
            date=student_exercise.completion_date,
            question_answers=question_answers,
        ))

    return Ok(data=GetExerciseGradesResponse(students_list=students_list,type='quiz'), message="Successfully fetched the grades exercise.")
