

"""
Document collection resource.

Each collection can be trreated as a separate knowledge base that is fed to the LLM.
A collection can have multiple documents uploaded by the client. There is an ingestion pipeline to
ingest documents to a vector database.
"""

from fastapi import APIRouter, Depends, Query

from providers.services import ServiceProvider
from schemas.responses.document_collection import DocumentCollectionResponse
from services.document_collection import DocumentCollectionService
from schemas.requests.document_collection import CreateDocumentCollectionRequest

router = APIRouter(prefix="/document-collections")

@router.get("", tags=["V1"])
async def ping():
    return {"message": "API version 1"}

@router.post("", response_model=DocumentCollectionResponse)
async def create_collection(
    req_body: CreateDocumentCollectionRequest,
    document_collection_service: DocumentCollectionService = Depends(ServiceProvider().get_document_collection_service)
):
    """
    Create a new collection and the index associated with it.
    The index is stored in PostgresQL internally.
    Use LlamaIndex to create an index. Use collection's name/collection id for the table name.
    """
    # TODO
    collection = await document_collection_service.create_document_collection(
            req_body.name, req_body.description
        )
    return DocumentCollectionResponse.model_validate(collection)

@router.post("{id_}/documents")
async def ingest_documents():
    """
    Ingest a document to the collection.
    This endpoint takes a file as input, add the file to the file system using fsspec (why? since I
    want to make it easier to switch between local filesystem and s3). Finally, ingest the document
    to the vector database.
    If there is a file already ingested (this can be achieved by checking the hash of the file),
    this endpoint does nothing.
    """

@router.get("/{id_}")
async def get_collection_metadata():
    """
    Return metadata of the collection.
    """

@router.get("{id_}:query")
async def query():
    """
    Send the client's query to the LLM, then the LLM will return a response based on the data in the
    knowledge base.
    """
