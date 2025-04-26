from deepeval.metrics import GEval
from deepeval.models import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCaseParams

def get_goal_alignment_metric(model: DeepEvalBaseLLM) -> GEval:
    return GEval(
        name="Goal Alignment",
        criteria="""
Evaluate how well the learning path aligns with the student's learning goal within the course scope.

1. Relevance to Goal: 
   - Are the selected lessons clearly contributing to achieving the goal?
2. Strategic Selection: 
   - Are the most impactful lessons prioritized given the course scope?
""",
        evaluation_params=[LLMTestCaseParams.CONTEXT, LLMTestCaseParams.ACTUAL_OUTPUT],
        model=model
    )


def get_explanation_quality_metric(model: DeepEvalBaseLLM) -> GEval:
    return GEval(
        name="Explanation Quality",
        criteria="""
Evaluate the clarity and relevance of the explanations given for each lesson in the learning path.

1. Clarity: Are the explanations clear and specific?
2. Goal Linkage: Do they explain how the lesson supports the student's goal?
3. Non-redundancy: Do they avoid restating the lesson title or being overly generic?
""",
        evaluation_params=[LLMTestCaseParams.CONTEXT, LLMTestCaseParams.ACTUAL_OUTPUT],
        model=model
    )


def get_ordering_logic_metric(model: DeepEvalBaseLLM) -> GEval:
    return GEval(
        name="Ordering Logic",
        criteria="""
Evaluate whether the order of the lessons in the learning path follows a logical learning progression.

1. Conceptual Progression: Do lessons build upon each other from simple to complex?
2. Misordering Penalty: Are any lessons clearly out of place?
""",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.CONTEXT],
        model=model
    )


def get_module_appropriateness_metric(model: DeepEvalBaseLLM) -> GEval:
    return GEval(
        name="Module Appropriateness",
        criteria="""
Evaluate the relevance and difficulty fit of the modules provided within each lesson of the learning path.

1. Relevance to Lesson and Goal: Are modules clearly supporting the lesson and the goal?
2. Difficulty Fit: Are modules appropriate to the expected depth implied by the goal?
3. Coverage Balance: Are modules well-distributed and avoid redundancy?
""",
        evaluation_params=[LLMTestCaseParams.CONTEXT, LLMTestCaseParams.ACTUAL_OUTPUT],
        model=model
    )
