from core.repository import BaseRepository
from machine.models import Modules, RecommendQuizzes
from sqlalchemy import select
from uuid import UUID
class ModulesRepository(BaseRepository[Modules]):
    async def update_module_progress(self, module_id: UUID):
        module = await self.first(where_=[Modules.id == module_id])
        if not module:
            return None
        
        result = await self.session.execute(
            select(RecommendQuizzes).where(RecommendQuizzes.module_id == module_id)
        )
        quizzes = result.scalars().all()
        
        completed_quizzes = [q for q in quizzes if q.status == "completed" and q.score is not None]
        if not completed_quizzes:
            return module
        
        total_score = sum(q.score for q in completed_quizzes)
        module_progress = round(total_score / len(completed_quizzes))
        
        module.progress = module_progress
        await self.session.commit()
        
        return module