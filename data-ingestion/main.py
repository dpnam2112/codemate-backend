#!main.py
import nest_asyncio
from services.index_builder import build_pgvector_index
from settings import env_settings
from services.fs_manager import FSManager
from factories import get_embedding_instance, get_llm_instance
from services.parser import DocumentParser
from data import contextual_nodes
from llama_index.core.node_parser import SentenceSplitter
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)


nest_asyncio.apply()


def main() -> None:
    """Main function to parse documents, build indexes, and execute multimodal queries."""
    fs_manager = FSManager(protocol=env_settings.fsspec_protocol)
    try:
        text_llm = get_llm_instance("gpt-4o-mini")
    except Exception as e:
        print(f"Error initializing LLM or embedding model: {e}")
        return

    parser = DocumentParser(
        result_type=env_settings.llama_parse_result_type,
        llamaparse_api_key=env_settings.llamaparse_api_key
    )
    try:
        md_json_list = parser.parse_document(env_settings.pdf_path, env_settings.image_download_dir)
    except Exception as e:
        print(f"Error parsing document: {e}")
        return

    try:
        from services.index_builder import get_text_nodes, create_contextual_nodes, build_pgvector_index
        text_nodes = get_text_nodes(env_settings.image_download_dir, md_json_list, fs_manager)
    except Exception as e:
        print(f"Error generating text nodes: {e}")
        return

    try:
        contextual_nodes = create_contextual_nodes(text_nodes, text_llm)
        print("contextual_nodes:", contextual_nodes)
    except Exception as e:
        print(f"Error creating contextual nodes: {e}")
        return
    
    embed_model = get_embedding_instance("openai")

    index = build_pgvector_index(
        contextual_nodes,
        embed_model,
        env_settings.pgvector_connection_string,
        env_settings.pgvector_async_connection_string,
        table_name="multimodal_rag_test"
    )

    from services.multimodal_query_engine import MultimodalQueryEngine
    multimodal_llm = get_llm_instance("gpt-4o")
    query_engine_instance = MultimodalQueryEngine(
        retriever=index.as_retriever(similarity_top_k=3),
        multi_modal_llm=multimodal_llm,
    )

    query = (
        "Summary the transformer"
    )
    try:
        response = query_engine_instance.custom_query(query)
        print(f"Response with contextual retrieval:\n{response}\n")
    except Exception as e:
        print(f"Error during second query: {e}")
        return


if __name__ == "__main__":
    main()

