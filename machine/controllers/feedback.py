from core.controller import BaseController
from machine.models import Feedback
from machine.repositories import FeedbackRepository 


class FeedbackController(BaseController[Feedback]):
    def __init__(self, feedback_repository: FeedbackRepository):
        super().__init__(model_class=Feedback, repository=feedback_repository)
        self.feedback_repository = feedback_repository