from sqlalchemy.ext.asyncio import AsyncSession
from core.repository.base import BaseRepository
from machine.models.coding_submission import ProgrammingTestCase

class ProgrammingTestCaseRepository(BaseRepository[ProgrammingTestCase]):
    def __init__(self, db_session: AsyncSession) -> None:
        super().__init__(ProgrammingTestCase, db_session)

