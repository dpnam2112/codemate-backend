from deepeval.metrics import GEval
from deepeval.models import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCaseParams

# metrics for learning path evaluation.
# the final score is calculated by the following formula:
# final_score = sum(w_i * s_i), where:
#   - w_i: weight of the metric i.
#   - s_i: score of the metric i, scaling from 0 to 1.
#
# == Weight selection ==:
#   - goal_alignment: 0.4
#   - explanation: 0.25
#   - ordering logic: 0.2
#   - module appropriateness: 0.15

def get_goal_alignment_metric(model: DeepEvalBaseLLM) -> GEval:
    return GEval(
        name="Goal Alignment",
        criteria="""
Evaluate how well the learning path recommended by AI aligns with the student's stated learning goal, given the available course content.

- Relevance to Goal:
  Are the selected lessons clearly essential to achieve the student's specific goal?
  Lessons that are tangential or only indirectly related should lower the score.

- Strategic Selection:
  Has the AI prioritized the most impactful and foundational lessons that directly support the goal?
  A focused, purposeful selection is preferred over a broad but unfocused path.

Focus on relevance and strategic prioritization of lessons toward the stated objective.
""",
        evaluation_params=[LLMTestCaseParams.CONTEXT, LLMTestCaseParams.ACTUAL_OUTPUT],
        model=model
    )


def get_explanation_quality_metric(model: DeepEvalBaseLLM) -> GEval:
    return GEval(
        name="Explanation Quality",
        criteria="""
Evaluate the quality and clarity of the explanations provided for each lesson recommendation in the learning path recommended by AI.
- Clarity: Are the explanations concise, specific, and easy to understand?
- Goal Linkage: Does each explanation explicitly state how the lesson contributes toward achieving the student's goal?
- Non-redundancy: Are the explanations more than just a repetition of the lesson titles, avoiding generic or vague wording?
Prioritize explanations that create clear, meaningful connections between lessons and goals.
""",
        evaluation_params=[LLMTestCaseParams.CONTEXT, LLMTestCaseParams.ACTUAL_OUTPUT],
        model=model
    )


def get_ordering_logic_metric(model: DeepEvalBaseLLM) -> GEval:
    return GEval(
        name="Ordering Logic",
        criteria="""
Evaluate whether the sequence of lessons in the learning path recommended by AI follows a logical and effective learning progression.
- Conceptual Progression: Does the learning path build from simpler concepts to more complex ideas? Are foundational lessons placed earlier than advanced ones?
- Misordering Penalty: Are there any lessons that are noticeably out of sequence, creating confusion or disrupting the learning flow?
""",
        evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.CONTEXT],
        model=model
    )


def get_module_appropriateness_metric(model: DeepEvalBaseLLM) -> GEval:
    return GEval(
        name="Module Appropriateness",
        criteria="""
Evaluate whether the modules recommended by AI under each lesson are relevant, appropriate in difficulty, and comprehensive.
- Relevance to Lesson and Goal: Do the modules directly support the main lesson and contribute to the student's goal?
- Difficulty Fit: Are the modules neither too simplistic nor overly advanced, relative to the goal's expected depth?
- Coverage Balance: Are the modules collectively covering the main aspects of the lesson without unnecessary redundancy or major omissions?
Focus on how well the modules serve the intended lesson purpose within the context of the student's goal.

""",
        evaluation_params=[LLMTestCaseParams.CONTEXT, LLMTestCaseParams.ACTUAL_OUTPUT],
        model=model
    )
