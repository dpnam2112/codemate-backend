from core.repository import BaseRepository
from machine.models import LearningPaths, RecommendLessons
from sqlalchemy import select
class LearningPathsRepository(BaseRepository[LearningPaths]):
    async def update_learning_path_progress(self, learning_path_id: str):
        learning_path = await self.first(where_=[LearningPaths.id == learning_path_id])
        if not learning_path:
            return None
        
        result = await self.session.execute(
            select(RecommendLessons).where(RecommendLessons.learning_path_id == learning_path_id)
        )   
        recommend_lessons = result.scalars().all()
        progress_learning_path = 0
        for recommend_lesson in recommend_lessons:
            if recommend_lesson.progress is not None:
                progress_learning_path += recommend_lesson.progress
        progress_learning_path = round(progress_learning_path / len(recommend_lessons)) if recommend_lessons else 0
        learning_path.progress = progress_learning_path
        await self.session.commit()
        
        return learning_path