from core.utils.decorators import singleton
from machine.services.code_exercise_assistant import CodeExerciseAssistantService

@singleton
class ServiceProvider:
    def __init__(self): pass

    def get_code_exercise_assistant_service(self):
        return CodeExerciseAssistantService()
