from loguru import logger
from typing import Optional
from llama_index.core.query_engine import CustomQueryEngine
from llama_index.core.retrievers import BaseRetriever
from llama_index.multi_modal_llms.openai import OpenAIMultiModal
from llama_index.core.schema import ImageNode, NodeWithScore, MetadataMode
from llama_index.core.prompts import PromptTemplate
from llama_index.core.base.response.schema import Response

QA_PROMPT_TMPL = """\
Below we give parsed text from slides in two different formats, as well as the image.

---------------------
{context_str}
---------------------
Given the context information and not prior knowledge, answer the query. Explain whether you got the answer
from the parsed markdown or raw text or image, and if there's discrepancies, and your reasoning for the final answer.

Query: {query_str}
Answer: """
QA_PROMPT = PromptTemplate(QA_PROMPT_TMPL)

class MultimodalQueryEngine(CustomQueryEngine):
    """Custom multimodal Query Engine that integrates text and image inputs for querying.

    Args:
        retriever: A BaseRetriever instance for document retrieval.
        multi_modal_llm: An OpenAIMultiModal instance for generating responses.
        qa_prompt: An optional prompt template.
    """


    qa_prompt: PromptTemplate
    retriever: BaseRetriever
    multi_modal_llm: OpenAIMultiModal

    def __init__(self, qa_prompt: Optional[PromptTemplate] = None, **kwargs) -> None:
        """Initialize."""
        super().__init__(qa_prompt=qa_prompt or QA_PROMPT, **kwargs)

    def custom_query(self, query_str: str) -> Response:
        """Execute a custom query combining text and image inputs.

        Args:
            query_str: The query string.

        Returns:
            A Response object with the answer and source nodes.
        """
        nodes = self.retriever.retrieve(query_str)
        image_nodes = [
            NodeWithScore(node=ImageNode(image_path=n.metadata["image_path"]))
            for n in nodes
        ]
        context_str = "\n\n".join(
            [r.get_content(metadata_mode=MetadataMode.LLM) for r in nodes]
        )
        fmt_prompt = self.qa_prompt.format(context_str=context_str, query_str=query_str)
        logger.debug("Prompt: ", fmt_prompt)
        llm_response = self.multi_modal_llm.complete(
            prompt=fmt_prompt,
            image_documents=[image_node.node for image_node in image_nodes],
        )
        return Response(
            response=str(llm_response),
            source_nodes=nodes,
            metadata={"text_nodes": nodes, "image_nodes": image_nodes},
        )

