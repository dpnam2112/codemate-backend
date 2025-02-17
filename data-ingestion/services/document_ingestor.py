import os
import re
import shutil
import tempfile
import time
from copy import deepcopy
from typing import Any, Dict, List, Optional

from fsspec.spec import AbstractFileSystem
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.base.embeddings.base import Embedding
from llama_index.core.schema import TextNode
from llama_index.core.llms import LLM, ChatMessage
from llama_index.core.vector_stores.types import VectorStore
from llama_index.multi_modal_llms.openai.base import MultiModalLLM
from llama_index.vector_stores.postgres import PGVectorStore
from logger import syslog
from services.parser import DocumentParser


class DocumentIngestor:
    """Class responsible for ingesting documents into a vector store.

    This class reads documents from an abstract file system, parses them to extract
    markdown and image data, converts the parsed output into text nodes (and then contextual nodes),
    and finally indexes these nodes into an injected vector store.

    Attributes:
        vector_store (Any): The injected vector store instance with an `add()` method.
        fs (AbstractFileSystem): The file system used to access stored documents.
        parser (DocumentParser): The parser instance for document processing.
        text_llm (Any): LLM instance used for processing text nodes.
        multimodal_llm (Any): LLM instance used for processing multimodal data.
    """

    def __init__(
        self,
        vector_store: PGVectorStore,
        fs: AbstractFileSystem,
        llamaparse_api_key: str,
        text_llm: LLM,
        multimodal_llm: MultiModalLLM,
        embed_model: Embedding
    ) -> None:
        """Initialize the DocumentIngestor.

        Args:
            vector_store (Any): The vector store where parsed nodes will be indexed.
            fs (AbstractFileSystem): The file system used to retrieve stored documents.
            llamaparse_api_key (str): API key for initializing the document parser.
            text_llm (Optional[Any]): LLM for processing text nodes.
            multimodal_llm (Optional[Any]): LLM for processing multimodal data.
        """
        self.vector_store = vector_store
        self.fs = fs
        self.parser = DocumentParser(result_type="markdown", llamaparse_api_key=llamaparse_api_key)
        self.text_llm = text_llm
        self.multimodal_llm = multimodal_llm
        self.embed_model = embed_model

    def ingest(self, file_key: str):
        """Ingest a stored document into the vector store.

        This method performs the following steps:
          1. Reads the document from the abstract file system.
          2. Writes the file to a temporary location.
          3. Creates a temporary directory for downloading parsed images.
          4. Parses the document to extract markdown content and images.
          5. Generates text nodes and then contextual nodes using the configured text LLM.
          6. Indexes the nodes into the injected vector store.

        Args:
            file_key (str): The key/path of the document in the abstract file system.

        Returns:
            VectorStoreIndex (str): The vector store index.

        Raises:
            Exception: If any step of the ingestion process fails.
        """
        with self.fs.open(file_key, mode="rb") as remote_file:
            file_content = remote_file.read()

        file_extension = os.path.splitext(file_key)[1] or ".pdf"

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            tmp_file.write(file_content)
            tmp_file_path = tmp_file.name

        image_download_dir = tempfile.mkdtemp(prefix="images_")
        try:
            md_json_list = self.parser.parse_document(tmp_file_path, image_download_dir)
            text_nodes = self._get_text_nodes(image_download_dir, md_json_list)
            contextual_nodes = self._create_contextual_nodes(text_nodes)

            index = VectorStoreIndex.from_vector_store(embed_model=self.embed_model, vector_store=self.vector_store)
            index.build_index_from_nodes(
                nodes=contextual_nodes
            )

            index.build_index_from_nodes(contextual_nodes)
            return index
        finally:
            try:
                os.remove(tmp_file_path)
            except Exception:
                pass
            try:
                shutil.rmtree(image_download_dir, ignore_errors=True)
            except Exception:
                pass

    def _get_text_nodes(self, image_dir: str, json_dicts: List[Dict]) -> List[TextNode]:
        """Generate text nodes from parsed markdown and image data.

        Args:
            image_dir (str): The directory containing image files.
            json_dicts (List[Dict]): Parsed markdown data.

        Returns:
            List[TextNode]: A list of text nodes.
        """
        image_files = self._get_sorted_image_files(image_dir)
        md_texts = [d["md"] for d in json_dicts if "md" in d]
        nodes: List[TextNode] = []
        for idx, md_text in enumerate(md_texts):
            metadata = {
                "page_num": idx + 1,
                "image_path": image_files[idx] if idx < len(image_files) else "",
                "parsed_text_markdown": md_text,
            }
            node = TextNode(text="", metadata=metadata)
            nodes.append(node)
        return nodes

    def _get_sorted_image_files(self, image_dir: str) -> List[str]:
        """Get image files sorted by page number.

        Args:
            image_dir (str): The directory containing image files.

        Returns:
            List[str]: Sorted list of image file paths.
        """
        def get_page_number(file_name: str) -> int:
            """Extract page number from a filename."""
            match = re.search(r"-page_(\d+)\.jpg$", file_name)
            return int(match.group(1)) if match else 0

        files = self.fs.glob(f"{image_dir}/*-page_*.jpg")
        sorted_files = sorted(files, key=get_page_number)
        return sorted_files

    def _create_contextual_nodes(self, nodes: List[TextNode]) -> List[TextNode]:
        """Enhance text nodes with contextual information using the text-only LLM.

        This method uses the configured text LLM to add context metadata to each node.

        Args:
            nodes (List[TextNode]): A list of text nodes.

        Returns:
            List[TextNode]: A list of contextualized text nodes.

        Raises:
            Exception: If the text LLM is not configured.
        """
        if not self.text_llm:
            raise Exception("Text LLM is not configured for contextualization.")

        whole_doc_text = "Here is the entire document.\n<document>\n{WHOLE_DOCUMENT}\n</document>"
        chunk_text = (
            "Here is the chunk we want to situate within the whole document\n<chunk>\n{CHUNK_CONTENT}\n</chunk>\n"
            "Please give a short succinct context to situate this chunk within the overall document for "
            "the purposes of improving search retrieval of the chunk. Answer only with the succinct context and nothing else."
        )

        nodes_modified: List[TextNode] = []
        doc_text = "\n".join([n.get_content(metadata_mode="all") for n in nodes])
        for idx, node in enumerate(nodes):
            start_time = time.time()
            new_node = deepcopy(node)
            messages = [
                ChatMessage(role="system", content="You are a helpful AI Assistant."),
                ChatMessage(
                    role="user",
                    content=[
                        {
                            "text": whole_doc_text.format(WHOLE_DOCUMENT=doc_text),
                            "block_type": "text",
                            "cache_control": {"type": "ephemeral"},
                        },
                        {
                            "text": chunk_text.format(CHUNK_CONTENT=node.get_content(metadata_mode="all")),
                            "block_type": "text",
                        },
                    ],
                ),
            ]
            new_response = self.text_llm.chat(messages, extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"})
            new_node.metadata["context"] = str(new_response)
            nodes_modified.append(new_node)
            syslog.debug(f"Completed node {idx} in {time.time() - start_time:.2f} seconds")
        return nodes_modified

