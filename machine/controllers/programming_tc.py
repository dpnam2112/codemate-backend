from typing import Any, Sequence, Optional
from core.controller.base import BaseController
from machine.models.coding_submission import ProgrammingTestCase
from machine.repositories.programming_tc import ProgrammingTestCaseRepository

class ProgrammingTestCaseController(BaseController[ProgrammingTestCase]):
    def __init__(self, repository: ProgrammingTestCaseRepository) -> None:
        super().__init__(ProgrammingTestCase, repository)

    async def get_many(self, limit: Optional[int] = None, offset: Optional[int] = None, **kwargs: Any) -> Sequence[ProgrammingTestCase]:
        return await self.repository.get_many(limit=limit, skip=offset, **kwargs)

