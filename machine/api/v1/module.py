from typing import List,Dict
from core.repository.enum import ExerciseType
from core.response import Ok
from machine.models import *
from fastapi import APIRouter, Depends, Path
from machine.schemas.requests import *
from machine.schemas.responses.exercise import CodeExerciseBriefResponse
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
    recommend_quiz_question_controller: RecommendQuizQuestionController = Depends(InternalProvider().get_recommend_quiz_question_controller),
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

    # Create a list to store quiz responses
    quizzes_response = []
    
    # Process each quiz and get the question count
    for quiz in module.quizzes:
        # Get questions count for this quiz
        quiz_questions = await recommend_quiz_question_controller.recommend_quiz_question_repository.get_many(
            where_=[RecommendQuizQuestion.quiz_id == quiz.id],
        )
        question_count = len(quiz_questions)
        
        # Add quiz data with question count to response
        quizzes_response.append(
            QuizListResponse(
                id=quiz.id,
                name=quiz.name,
                description=quiz.description,
                status=quiz.status,
                score=quiz.score,
                max_score=quiz.max_score,
                time_limit=quiz.time_limit,
                duration=quiz.duration,
                question_count=question_count,  # Add question count here
            )
        )

    response_data = ModuleQuizResponse(
        module_id=module.id,
        title=module.title,
        objectives=module.objectives,
        quizzes=quizzes_response,
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
    analysis_results = None
    
    try:
        # Call the analysis function and capture results
        analysis_results = await analyze_and_return_issues(
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
        print(f"Error during analysis: {str(e)}")
        
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
        identified_issues=analysis_results.get("issues") if analysis_results else None,
        new_achievements=analysis_results.get("achievements") if analysis_results else None
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
    Analyze quiz results, update the issues_summary and achievements in student_courses, and return identified issues
    """
    # Only proceed with analysis if there are incorrect answers
    incorrect_answers = [q for q in questions_results if not q["is_correct"]]
    correct_answers = [q for q in questions_results if q["is_correct"]]
    
    # Check if all answers are correct or partial success
    all_correct = len(incorrect_answers) == 0 and len(questions_results) > 0
    high_score = len(incorrect_answers) / len(questions_results) <= 0.3 if questions_results else False
    
    # Get current issues summary and achievements from student_courses
    learning_path = await learning_paths_controller.learning_paths_repository.first(
        where_=[LearningPaths.id == recommend_lesson.learning_path_id],
    )
    
    student_course = await student_courses_controller.student_courses_repository.first(
        where_=[StudentCourses.course_id == learning_path.course_id, StudentCourses.student_id == user_id],
    )
    
    current_summary = student_course.issues_summary if student_course.issues_summary else {"common_issues": []}
    current_achievements = student_course.achievements if student_course.achievements else {"earned_achievements": []}
    
    # Generate achievements based on quiz performance and content
    new_achievements = []
    
    # Extract module-specific information
    module_topics = []
    if hasattr(module, 'objectives') and module.objectives:
        # Extract keywords for topic-specific achievements
        module_topics = module.objectives
    elif hasattr(module, 'title') and module.title:
        # Fallback to module title if objectives aren't available
        module_topics = [module.title]
    
    # Get topic-specific information from the questions
    question_topics = set()
    mastered_topics = set()
    
    # Find topics that were tested in the quiz and mastered by the student
    for q in questions_results:
        # Extract topic from question text or other fields
        topic = extract_topic_from_question(q)
        if topic:
            question_topics.add(topic)
            if q["is_correct"]:
                mastered_topics.add(topic)
    
    # Add module topics to our collection of topics
    if module_topics:
        question_topics.update(module_topics)
    
    # Create specific achievements based on performance
    now = datetime.now(timezone.utc).isoformat()
    
    if all_correct:
        # Perfect score achievement with specific module reference
        new_achievements.append({
            "type": "perfect_score",
            "description": f"Perfect Score: Mastered {module.title}",
            "earned_date": now,
            "related_topics": list(question_topics),
            "difficulty": "advanced" 
        })
        
        # Add topic mastery achievements for each topic covered
        for topic in mastered_topics:
            new_achievements.append({
                "type": "concept_mastery",
                "description": f"Mastered {topic} concepts",
                "earned_date": now,
                "related_topics": [topic],
                "difficulty": "advanced"
            })
            
    elif high_score:
        # High performance with specific module reference
        new_achievements.append({
            "type": "high_performance",
            "description": f"Expert Knowledge: {module.title}",
            "earned_date": now,
            "related_topics": list(question_topics),
            "difficulty": "intermediate"
        })
        
        # Add topic proficiency achievements for mastered topics
        for topic in mastered_topics:
            new_achievements.append({
                "type": "topic_proficiency",
                "description": f"Demonstrated proficiency in {topic}",
                "earned_date": now,
                "related_topics": [topic],
                "difficulty": "intermediate"
            })
    else:
        # Basic completion with specific module reference
        progress_percent = round((len(correct_answers) / len(questions_results)) * 100)
        new_achievements.append({
            "type": "quiz_completion",
            "description": f"Completed {module.title} Quiz ({progress_percent}%)",
            "earned_date": now,
            "related_topics": list(question_topics),
            "difficulty": "basic"
        })
        
        # Add achievement for consistent improvement if previous attempts were worse
        # This would require tracking previous attempts, which could be added in a future enhancement
    
    # Add streak achievements if student has completed multiple quizzes in a row
    # This would require tracking quiz completion history
    
    # Prepare data for AI analysis to identify issues and additional achievements
    prompt = prepare_analysis_prompt(
        quiz_id=quiz_id,
        module=module,
        recommend_lesson=recommend_lesson,
        questions_results=questions_results,
        current_summary=current_summary,
        current_achievements=current_achievements,
        all_correct=all_correct
    )
    
    ai_tool_provider = AIToolProvider()
    llm = ai_tool_provider.chat_model_factory(LLMModelName.GEMINI_PRO)
    
    llm.temperature = 0.3
    llm.max_output_tokens = 2000
    
    try:
        response = llm.invoke(prompt)
        
        if not response:
            print("Failed to get analysis from LLM")
            # Return default achievements even if LLM fails
            return {"issues": None, "achievements": new_achievements}
        
        response_text = response.content
        analysis_result = extract_json_from_response(response_text)
        
        # Check if analysis returned valid data
        if not analysis_result:
            print("Invalid response format from LLM, using default achievements")
            return {"issues": None, "achievements": new_achievements}
        
        # Process issues
        new_issues = analysis_result.get("common_issues", [])
        
        # Process achievements from LLM response
        llm_achievements = analysis_result.get("new_achievements", [])
        if llm_achievements:
            # Ensure LLM-generated achievements don't duplicate our content-specific ones
            # by comparing types and descriptions
            existing_desc = {achievement["description"] for achievement in new_achievements}
            for achievement in llm_achievements:
                if achievement["description"] not in existing_desc:
                    new_achievements.append(achievement)
        
        # Process resolved issues to achievements
        resolved_issues = analysis_result.get("resolved_issues", [])
        
        # Update issues_summary in student_courses
        updated_issues_summary = process_issues(current_summary, new_issues, resolved_issues)
        
        # Update achievements in student_courses
        updated_achievements = process_achievements(current_achievements, new_achievements, resolved_issues)
        
        # Update student_courses with both updated issues and achievements
        await student_courses_controller.student_courses_repository.update(
            where_=[StudentCourses.course_id == learning_path.course_id, StudentCourses.student_id == user_id],
            attributes={
                "issues_summary": updated_issues_summary,
                "achievements": updated_achievements
            },
            commit=True
        )
        
        # Return the newly identified issues and achievements for the API response
        return {
            "issues": new_issues if new_issues else None,
            "achievements": new_achievements if new_achievements else None
        }
        
    except Exception as e:
        print(f"Error during AI analysis: {str(e)}")
        # Return generated achievements even if an error occurs
        return {"issues": None, "achievements": new_achievements}
        

def extract_topic_from_question(question):
    """
    Extract the most likely topic from a question based on its content
    This is a simple implementation - could be enhanced with NLP or keyword extraction
    """
    if not question:
        return None
        
    # Try to extract topic from question text
    question_text = question.get("question_text", "")
    
    # List of common keywords that might appear in questions
    topic_keywords = {
        "algebra": ["equation", "variable", "solve for x", "linear", "quadratic"],
        "calculus": ["derivative", "integral", "limit", "differentiate", "integrate"],
        "geometry": ["triangle", "circle", "square", "angle", "perimeter", "area"],
        "statistics": ["mean", "median", "mode", "distribution", "probability"],
        "programming": ["code", "function", "variable", "loop", "algorithm"],
        "data structures": ["array", "list", "tree", "graph", "hash table"],
        "algorithms": ["sort", "search", "complexity", "big-o", "optimization"],
        "databases": ["SQL", "query", "table", "join", "index"],
        "network": ["protocol", "TCP/IP", "router", "packet", "HTTP"],
        "operating systems": ["process", "thread", "memory", "scheduling", "file system"]
    }
    
    # Check if any keywords are in the question text
    for topic, keywords in topic_keywords.items():
        if any(keyword.lower() in question_text.lower() for keyword in keywords):
            return topic
            
    # If no specific topic is found, return a generic topic based on question difficulty
    difficulty = question.get("difficulty", "").lower()
    if difficulty in ["hard", "advanced"]:
        return "advanced concepts"
    elif difficulty in ["medium", "intermediate"]:
        return "intermediate concepts"
    else:
        return "fundamental concepts"

def prepare_analysis_prompt(
    quiz_id, module, recommend_lesson, questions_results, current_summary, current_achievements, all_correct
):
    """
    Prepare the prompt for AI analysis with emphasis on specific, content-related achievements
    """
    # Extract information about incorrect answers
    incorrect_answers = [q for q in questions_results if not q["is_correct"]]
    correct_answers = [q for q in questions_results if q["is_correct"]]
    
    # Calculate performance metrics
    total_questions = len(questions_results)
    incorrect_count = len(incorrect_answers)
    correct_percentage = ((total_questions - incorrect_count) / total_questions) * 100
    
    # Identify specific topics and concepts from the questions
    question_topics = [q.get("question_text", "")[:50] + "..." for q in questions_results]
    
    # Extract module-specific information if available
    module_info = ""
    if hasattr(module, 'objectives') and module.objectives:
        module_info += f"\nModule Objectives: {json.dumps(module.objectives)}"
    if hasattr(module, 'title') and module.title:
        module_info += f"\nModule Title: {module.title}"
    
    # Extract any other contextual information that might help with specific achievements
    lesson_info = ""
    if hasattr(recommend_lesson, 'title') and recommend_lesson.title:
        lesson_info += f"\nLesson Title: {recommend_lesson.title}"
    if hasattr(recommend_lesson, 'learning_outcomes') and recommend_lesson.learning_outcomes:
        lesson_info += f"\nLearning Outcomes: {json.dumps(recommend_lesson.learning_outcomes)}"
    
    prompt = f"""
    ## Quiz Analysis Task
    
    ## Quiz Information
    - Quiz ID: {quiz_id}
    - Module Title: {module.title if hasattr(module, 'title') else 'N/A'}
    {module_info}
    
    ## Lesson Information
    - Lesson Title: {recommend_lesson.title if hasattr(recommend_lesson, 'title') else 'N/A'}
    {lesson_info}
    
    ## Quiz Results
    - Total Questions: {total_questions}
    - Incorrect Answers: {incorrect_count}
    - Correct Percentage: {correct_percentage:.1f}%
    - All Answers Correct: {all_correct}
    
    ## Question Topics
    {json.dumps(question_topics, indent=2)}
    
    ## Questions with Incorrect Answers
    {json.dumps(incorrect_answers, indent=2) if incorrect_answers else "No incorrect answers"}
    
    ## Current Issues Summary (for reference)
    {json.dumps(current_summary, indent=2)}
    
    ## Current Achievements Summary (for reference)
    {json.dumps(current_achievements, indent=2)}
    
    ## Task
    1. Analyze the quiz results to identify:
       - Common issues or misunderstandings from incorrect answers
       - SPECIFIC achievements earned based on the content of correct answers
       - Issues from the current issues summary that appear to be resolved
    
    2. Create HIGHLY SPECIFIC achievements that reference:
       - The exact module/lesson name (e.g., "Data Structures: Mastered Binary Trees")
       - Specific concepts or skills demonstrated (e.g., "Algorithm Time Complexity Expert")
       - The difficulty level of the mastered concepts
       - Connections to real-world applications when relevant
    
    3. Achievements should be diverse and recognize different aspects:
       - Concept mastery (specific topics the student has mastered)
       - Problem-solving skills (how they approached complex problems)
       - Learning milestones (significant progress in particular areas)
       - Application of knowledge (connecting concepts to practical scenarios)
    
    4. For resolved issues, determine which ones should be converted to achievements:
       - Compare quiz results with current issues summary
       - Identify issues that were previously problematic but are now solved
    
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
            }}
        ],
        "new_achievements": [
            {{
                "type": "concept_mastery",
                "description": "VERY SPECIFIC description referring to exact module/concept mastered",
                "earned_date": "{datetime.now(timezone.utc).isoformat()}",
                "related_topics": ["specific topic 1", "specific topic 2"],
                "difficulty": "basic/intermediate/advanced"
            }}
        ],
        "resolved_issues": [
            {{
                "type": "concept_misunderstanding", 
                "description": "Exact description from the issues_summary of an issue that has been resolved",
                "resolution_date": "{datetime.now(timezone.utc).isoformat()}"
            }}
        ]
    }}
    
    IMPORTANT REQUIREMENTS FOR SPECIFICITY:
    1. NEVER use generic descriptions like "High Performance on Quiz"
    2. ALWAYS include the specific module/lesson name in achievement descriptions
    3. ALWAYS reference specific concepts, algorithms, or skills in the descriptions
    4. Make achievements sound impressive and motivating but factual
    5. Create variable difficulty levels (basic/intermediate/advanced) based on content
    6. For perfect scores on difficult topics, make achievements particularly noteworthy
    
    Respond ONLY with the JSON. Do not include any other text.
    """
    
    return prompt

def process_issues(current_summary, new_issues, resolved_issues):
    """
    Update the issues summary by adding new issues and removing resolved ones
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
    
    # Find issues to remove (resolved issues)
    issues_to_remove = []
    for resolved in resolved_issues:
        key = (resolved.get("type", ""), resolved.get("description", ""))
        if key in existing_issues:
            issues_to_remove.append(existing_issues[key])
    
    # Remove resolved issues (in reverse order to avoid index issues)
    for index in sorted(issues_to_remove, reverse=True):
        current_summary["common_issues"].pop(index)
    
    # Process new issues
    for new_issue in new_issues:
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

def process_achievements(current_achievements, new_achievements, resolved_issues):
    """
    Update achievements by adding new ones, including those from resolved issues
    """
    if not isinstance(current_achievements, dict):
        current_achievements = {"earned_achievements": []}
    if "earned_achievements" not in current_achievements:
        current_achievements["earned_achievements"] = []
    
    # Create lookup dictionary for existing achievements
    existing_achievements = {}
    for i, achievement in enumerate(current_achievements["earned_achievements"]):
        key = (achievement.get("type", ""), achievement.get("description", ""))
        existing_achievements[key] = i
    
    # Process new achievements
    for achievement in new_achievements:
        key = (achievement.get("type", ""), achievement.get("description", ""))
        
        if key not in existing_achievements:
            # Only add if it doesn't already exist
            current_achievements["earned_achievements"].append(achievement)
    
    # Process resolved issues into achievements
    for resolved in resolved_issues:
        # Create an achievement for each resolved issue
        resolution_achievement = {
            "type": "issue_resolution",
            "description": f"Resolved: {resolved.get('description', '')}",
            "earned_date": resolved.get("resolution_date", datetime.now(timezone.utc).isoformat()),
            "related_topics": [],
            "difficulty": "intermediate"  # Default difficulty
        }
        
        key = (resolution_achievement.get("type", ""), resolution_achievement.get("description", ""))
        
        if key not in existing_achievements:
            # Only add if it doesn't already exist
            current_achievements["earned_achievements"].append(resolution_achievement)
    
    return current_achievements

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

@router.get("/{module_id}/coding-exercises", response_model=Ok[List[CodeExerciseBriefResponse]])
async def get_coding_exercises_brief(
    module_id: UUID = Path(..., title="Module ID"),
    exercises_controller: ExercisesController = Depends(InternalProvider().get_exercises_controller),
):
    exercises = await exercises_controller.get_many(
        where_=[Exercises.module_id == module_id, Exercises.type == ExerciseType.code],
    )

    return Ok(
        data=[CodeExerciseBriefResponse.model_validate(exercise) for exercise in exercises]
    )
