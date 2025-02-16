from .base import BaseRepository
from db_models import  DocumentCollection

class DocumentCollectionRepository(BaseRepository[DocumentCollection]): ...
