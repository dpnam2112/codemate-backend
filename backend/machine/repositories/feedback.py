from sqlalchemy import Select
from core.repository.base import BaseRepository
from machine.models import Feedback

class FeedbackRepository(BaseRepository[Feedback]):...