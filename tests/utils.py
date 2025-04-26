def build_course_context(path: dict) -> str:
    """
    Build a concise context string for the evaluator.
    Includes:
    - Course name and description
    - List of all available lessons (title + description)
    This represents the static structure of the course.
    """
    course_name = path["course"].get("name", "Unnamed Course")
    course_desc = path["course"].get("description", "No course description provided.")

    context_lines = [f"Course: {course_name}", f"Description: {course_desc}", "", "Available Lessons:"]
    lessons_seen = set()

    for rec in path.get("recommended_lessons", []):
        lesson = rec.get("lesson")
        if not lesson:
            continue
        title = lesson.get("title", "Untitled Lesson")
        desc = lesson.get("description", "No description provided.")
        if title not in lessons_seen:
            context_lines.append(f"- {title}: {desc}")
            lessons_seen.add(title)

    return "\n".join(context_lines)


def build_llm_learning_path_output(path: dict) -> str:
    """
    Generate a verbose and clearly formatted recommended learning path output.
    Includes:
    - Lesson title and explanation
    - For each lesson, modules with clearly labeled titles and objectives
    """
    lines = ["Learning Path constructed from the course's lessons by the system:\n"]
    for i, rec in enumerate(path["recommended_lessons"]):
        lesson_title = rec.get("lesson", {}).get("title", "Untitled Lesson")
        explanation = rec.get("explanation", "No explanation provided.").strip()
        lines.append(f"{i + 1}. Lesson: {lesson_title}")
        lines.append(f"   Explanation: {explanation}")
        modules = rec.get("modules", [])
        if modules:
            lines.append("   Modules:")
            for j, mod in enumerate(modules):
                mod_title = mod.get("title", f"Module {j + 1}")
                mod_objectives = mod.get("objectives")
                lines.append(f"     - Title: {mod_title}")
                lines.append(f"       Objectives: {mod_objectives}")
        lines.append("")
    return "\n".join(lines)
