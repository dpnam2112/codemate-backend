#!index_builder.py
import re
import time
from copy import deepcopy
from typing import List, Dict, Any
from llama_index.core.schema import TextNode
from llama_index.core import StorageContext, VectorStoreIndex, load_index_from_storage
from llama_index.vector_stores.postgres import PGVectorStore
from llama_index.core.llms import ChatMessage


def get_page_number(file_name: str) -> int:
    """Extract page number from a filename.

    Args:
        file_name: The filename containing page information.

    Returns:
        The extracted page number.
    """
    match = re.search(r"-page_(\d+)\.jpg$", file_name)
    return int(match.group(1)) if match else 0


def _get_sorted_image_files(image_dir: str, fs_manager: Any) -> List[str]:
    """Get image files sorted by page number using fsspec.

    Args:
        image_dir: The directory containing image files.
        fs_manager: An instance of FSManager.

    Returns:
        A list of sorted image file paths.
    """
    files = fs_manager.fs.glob(f"{image_dir}/*-page_*.jpg")
    sorted_files = sorted(files, key=get_page_number)
    return sorted_files


def get_text_nodes(image_dir: str, json_dicts: List[Dict], fs_manager: Any) -> List[TextNode]:
    """Generate text nodes by combining parsed markdown and image metadata.

    Args:
        image_dir: The directory containing image files.
        json_dicts: A list of dictionaries with parsed markdown content.
        fs_manager: An instance of FSManager.

    Returns:
        A list of TextNode objects.
    """
    image_files = _get_sorted_image_files(image_dir, fs_manager)
    md_texts = [d["md"] for d in json_dicts]
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


def create_contextual_nodes(nodes: List[TextNode], llm: Any) -> List[TextNode]:
    """Create contextual nodes by adding context metadata using an LLM.

    Args:
        nodes: A list of TextNode objects.
        llm: An LLM instance used to generate context.

    Returns:
        A list of modified TextNode objects with contextual metadata.
    """
    whole_doc_text = (
        "Here is the entire document.\n<document>\n{WHOLE_DOCUMENT}\n</document>"
    )
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
        new_response = llm.chat(messages, extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"})
        new_node.metadata["context"] = str(new_response)
        nodes_modified.append(new_node)
        print(f"Completed node {idx}, {time.time() - start_time}")
    return nodes_modified

def build_pgvector_index(
    nodes: List[TextNode],
    embed_model: Any,
    connection_string: str,
    async_connection_string: str,
    table_name: str
):
    """Build or load a pgvector-based vector store index.

    Args:
        nodes: A list of TextNode objects.
        embed_model: The embedding model instance.
        connection_string: PostgreSQL connection string for pgvector.
        table_name: The table name for storing vector data.
        index_id: The identifier for the index.

    Returns:
        A VectorStoreIndex object built using PGVectorStore.
    """
    vector_store = PGVectorStore(
        connection_string=connection_string,
        async_connection_string=async_connection_string,
        table_name=table_name,
        schema_name="codemate"
    )
    storage_context = StorageContext.from_defaults(
        vector_store=vector_store
    )
    index = VectorStoreIndex(nodes=nodes, embed_model=embed_model, show_progress=True, storage_context=storage_context)
    index.build_index_from_nodes(
        nodes=nodes
    )
    storage_context.persist("./storage")
    return index
