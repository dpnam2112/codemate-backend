from core.repository import BaseRepository
from machine.models import RecommendQuizzes
from machine.models import RecommendQuizQuestion
class RecommendQuizzesRepository(BaseRepository[RecommendQuizzes]):...
class RecommendQuizQuestionRepository(BaseRepository[RecommendQuizQuestion]):...