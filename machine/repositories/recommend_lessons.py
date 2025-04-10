from core.repository import BaseRepository
from machine.models import RecommendLessons, Modules
from sqlalchemy import select
class RecommendLessonsRepository(BaseRepository[RecommendLessons]):
    async def update_recommend_lesson_progress(self, lesson_id: str):
        lesson = await self.first(where_=[RecommendLessons.id == lesson_id])
        if not lesson:
            return None
        
        result = await self.session.execute(
            select(Modules).where(Modules.recommend_lesson_id == lesson_id)
        )   
        modules = result.scalars().all()
        progress_recommend_lesson = 0
        for module in modules:
            if module.progress is not None:
                progress_recommend_lesson += module.progress
        progress_recommend_lesson = round(progress_recommend_lesson / len(modules)) if modules else 0
        lesson.progress = progress_recommend_lesson
        await self.session.commit()
        
        return lesson
