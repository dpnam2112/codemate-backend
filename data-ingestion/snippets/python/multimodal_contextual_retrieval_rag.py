#!/usr/bin/env python
# coding: utf-8

# # Contextual Retrieval for Multimodal RAG
# 
# <a href="https://colab.research.google.com/github/run-llama/llama_parse/blob/main/examples/multimodal/multimodal_contextual_retrieval_rag.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>
# 
# In this cookbook we show you how to build a multimodal RAG pipeline with **contextual retrieval**.
# 
# Contextual retrieval was initially introduced in this Anthropic [blog post](https://www.anthropic.com/news/contextual-retrieval). The high-level intuition is that every chunk is given a concise summary of where that chunk fits in with respect to the overall summary of the document. This allows insertion of high-level concepts/keywords that enable this chunk to be better retrieved for different types of queries.
# 
# These LLM calls are expensive. Contextual retrieval depends on **prompt caching** in order to be efficient.
# 
# In this notebook, we use Claude 3.5-Sonnet to generate contextual summaries. We cache the document as text tokens, but generate contextual summaries by feeding in the parsed text chunk. 
# 
# We feed both the text and image chunks into the final multimodal RAG pipeline to generate the response.
# 
# ![mm_rag_diagram](./multimodal_contextual_retrieval_rag_img.png)

# ## Setup

# In[ ]:


import nest_asyncio

nest_asyncio.apply()


# ### Setup Observability
# 
# We setup an integration with LlamaTrace (integration with Arize).
# 
# If you haven't already done so, make sure to create an account here: https://llamatrace.com/login. Then create an API key and put it in the `PHOENIX_API_KEY` variable below.

# In[ ]:


get_ipython().system('pip install -U llama-index-callbacks-arize-phoenix')


# In[ ]:


# setup Arize Phoenix for logging/observability
import llama_index.core
import os

PHOENIX_API_KEY = "<PHOENIX_API_KEY>"
os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"api_key={PHOENIX_API_KEY}"
llama_index.core.set_global_handler(
    "arize_phoenix", endpoint="https://llamatrace.com/v1/traces"
)


# ### Load Data
# 
# Here we load the [ICONIQ 2024 State of AI Report](https://cdn.prod.website-files.com/65e1d7fb19a3e64b5c36fb38/66eb856e019e59758ef73759_ICONIQ%20Analytics%20%2B%20Insights%20-%20State%20of%20AI%20Sep24.pdf).

# In[ ]:


get_ipython().system('mkdir data')
get_ipython().system('mkdir data_images_iconiq')
get_ipython().system('wget "https://cdn.prod.website-files.com/65e1d7fb19a3e64b5c36fb38/66eb856e019e59758ef73759_ICONIQ%20Analytics%20%2B%20Insights%20-%20State%20of%20AI%20Sep24.pdf" -O data/iconiq_report.pdf')


# ### Model Setup
# 
# Setup models that will be used for downstream orchestration.

# In[ ]:


import os

# replace with your Anthropic API key
os.environ["ANTHROPIC_API_KEY"] = "sk-..."
# replace with your VoyageAI key
os.environ["VOYAGE_API_KEY"] = ""


# In[ ]:


from llama_index.llms.anthropic import Anthropic
from llama_index.embeddings.voyageai import VoyageEmbedding
from llama_index.core import Settings


llm = Anthropic(model="claude-3-5-sonnet-20240620")
embed_model = VoyageEmbedding(model_name="voyage-3")

Settings.llm = llm
Settings.embed_model = embed_model


# ## Use LlamaParse to Parse Text and Images
# 
# In this example, use LlamaParse to parse both the text and images from the document.
# 
# We parse out the text with LlamaParse premium.
# 
# **NOTE**: The report has 40 pages, and at ~5c per page, this will cost you $2. Just a heads up!

# In[ ]:


from llama_parse import LlamaParse


parser = LlamaParse(
    result_type="markdown",
    premium_mode=True,
    # invalidate_cache=True
)


# In[ ]:


print(f"Parsing text...")
md_json_objs = parser.get_json_result("data/iconiq_report.pdf")
md_json_list = md_json_objs[0]["pages"]


# In[ ]:


print(md_json_list[10]["md"])


# In[ ]:


image_dicts = parser.get_images(md_json_objs, download_path="data_images_iconiq")


# ## Build Multimodal Index
# 
# In this section we build the multimodal index over the parsed deck. 
# 
# We do this by creating **text** nodes from the document that contain metadata referencing the original image path.
# 
# In this example we're indexing the text node for retrieval. The text node has a reference to both the parsed text as well as the image screenshot.

# #### Get Text Nodes

# In[ ]:


from llama_index.core.schema import TextNode
from typing import Optional


# In[ ]:


# get pages loaded through llamaparse
import re


def get_page_number(file_name):
    match = re.search(r"-page_(\d+)\.jpg$", str(file_name))
    if match:
        return int(match.group(1))
    return 0


def _get_sorted_image_files(image_dir):
    """Get image files sorted by page."""
    raw_files = [
        f for f in list(Path(image_dir).iterdir()) if f.is_file() and "-page" in str(f)
    ]
    sorted_files = sorted(raw_files, key=get_page_number)
    return sorted_files


# In[ ]:


from copy import deepcopy
from pathlib import Path


# attach image metadata to the text nodes
def get_text_nodes(image_dir, json_dicts):
    """Split docs into nodes, by separator."""
    nodes = []

    image_files = _get_sorted_image_files(image_dir)
    md_texts = [d["md"] for d in json_dicts]

    for idx, md_text in enumerate(md_texts):
        chunk_metadata = {"page_num": idx + 1}
        chunk_metadata["image_path"] = str(image_files[idx])
        chunk_metadata["parsed_text_markdown"] = md_texts[idx]
        node = TextNode(
            text="",
            metadata=chunk_metadata,
        )
        nodes.append(node)

    return nodes


# In[ ]:


# this will split into pages
text_nodes = get_text_nodes(image_dir="data_images_iconiq", json_dicts=md_json_list)


# In[ ]:


print(text_nodes[0].get_content(metadata_mode="all"))


# #### Add Contextual Summaries
# 
# In this section we implement the key step in contextual retrieval - attaching metadata to each chunk that situates it within the overall document context.
# 
# We take advantage of prompt caching by feeding in the static document as prefix tokens, and only swap out the "header" tokens.

# In[ ]:


from copy import deepcopy
from llama_index.core.llms import ChatMessage
from llama_index.core.prompts import ChatPromptTemplate
import time


whole_doc_text = """\
Here is the entire document.
<document>
{WHOLE_DOCUMENT}
</document>"""

chunk_text = """\
Here is the chunk we want to situate within the whole document
<chunk>
{CHUNK_CONTENT}
</chunk>
Please give a short succinct context to situate this chunk within the overall document for \
the purposes of improving search retrieval of the chunk. Answer only with the succinct context and nothing else."""


def create_contextual_nodes(nodes, llm):
    """Function to create contextual nodes for a list of nodes"""
    nodes_modified = []

    # get overall doc_text string
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
                        "type": "text",
                        "cache_control": {"type": "ephemeral"},
                    },
                    {
                        "text": chunk_text.format(
                            CHUNK_CONTENT=node.get_content(metadata_mode="all")
                        ),
                        "type": "text",
                    },
                ],
            ),
        ]

        new_response = llm.chat(
            messages, extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"}
        )
        new_node.metadata["context"] = str(new_response)

        nodes_modified.append(new_node)
        print(f"Completed node {idx}, {time.time() - start_time}")

    return nodes_modified


# In[ ]:


new_text_nodes = create_contextual_nodes(text_nodes, llm)


# #### Build Index
# 
# Once the text nodes are ready, we feed into our vector store index abstraction, which will index these nodes into a simple in-memory vector store (of course, you should definitely check out our 40+ vector store integrations!)

# In[ ]:


import os
from llama_index.core import (
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)

if not os.path.exists("storage_nodes_iconiq"):
    index = VectorStoreIndex(new_text_nodes, embed_model=embed_model)
    # save index to disk
    index.set_index_id("vector_index")
    index.storage_context.persist("./storage_nodes_iconiq")
else:
    # rebuild storage context
    storage_context = StorageContext.from_defaults(persist_dir="storage_nodes_iconiq")
    # load index
    index = load_index_from_storage(storage_context, index_id="vector_index")

retriever = index.as_retriever()


# #### Build Baseline Index
# 
# Build a baseline index with the text nodes without summarized context.

# In[ ]:


if not os.path.exists("storage_nodes_iconiq_base"):
    base_index = VectorStoreIndex(text_nodes, embed_model=embed_model)
    # save index to disk
    base_index.set_index_id("vector_index")
    base_index.storage_context.persist("./storage_nodes_iconiq_base")
else:
    # rebuild storage context
    storage_context = StorageContext.from_defaults(
        persist_dir="storage_nodes_iconiq_base"
    )
    # load index
    base_index = load_index_from_storage(storage_context, index_id="vector_index")


# ## Build Multimodal Query Engine
# 
# We now use LlamaIndex abstractions to build a **custom query engine**. In contrast to a standard RAG query engine that will retrieve the text node and only put that into the prompt (response synthesis module), this custom query engine will also load the image document, and put both the text and image document into the response synthesis module.

# In[ ]:


from llama_index.core.query_engine import CustomQueryEngine, SimpleMultiModalQueryEngine
from llama_index.core.retrievers import BaseRetriever
from llama_index.multi_modal_llms.openai import OpenAIMultiModal
from llama_index.core.schema import ImageNode, NodeWithScore, MetadataMode
from llama_index.core.prompts import PromptTemplate
from llama_index.core.base.response.schema import Response
from typing import Optional


gpt_4o = OpenAIMultiModal(model="gpt-4o", max_new_tokens=4096)

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
    """Custom multimodal Query Engine.

    Takes in a retriever to retrieve a set of document nodes.
    Also takes in a prompt template and multimodal model.

    """

    qa_prompt: PromptTemplate
    retriever: BaseRetriever
    multi_modal_llm: OpenAIMultiModal

    def __init__(self, qa_prompt: Optional[PromptTemplate] = None, **kwargs) -> None:
        """Initialize."""
        super().__init__(qa_prompt=qa_prompt or QA_PROMPT, **kwargs)

    def custom_query(self, query_str: str):
        # retrieve text nodes
        nodes = self.retriever.retrieve(query_str)
        # create ImageNode items from text nodes
        image_nodes = [
            NodeWithScore(node=ImageNode(image_path=n.metadata["image_path"]))
            for n in nodes
        ]

        # create context string from text nodes, dump into the prompt
        context_str = "\n\n".join(
            [r.get_content(metadata_mode=MetadataMode.LLM) for r in nodes]
        )
        fmt_prompt = self.qa_prompt.format(context_str=context_str, query_str=query_str)

        # synthesize an answer from formatted text and images
        llm_response = self.multi_modal_llm.complete(
            prompt=fmt_prompt,
            image_documents=[image_node.node for image_node in image_nodes],
        )
        return Response(
            response=str(llm_response),
            source_nodes=nodes,
            metadata={"text_nodes": nodes, "image_nodes": image_nodes},
        )

        return response


# In[ ]:


query_engine = MultimodalQueryEngine(
    retriever=index.as_retriever(similarity_top_k=3), multi_modal_llm=gpt_4o
)
base_query_engine = MultimodalQueryEngine(
    retriever=base_index.as_retriever(similarity_top_k=3), multi_modal_llm=gpt_4o
)


# ## Try out Queries
# 
# Let's try out some questions against the slide deck in this multimodal RAG pipeline.

# In[ ]:


response = query_engine.query(
    "which departments/teams use genAI the most and how are they using it?"
)
print(str(response))


# In[ ]:


base_response = base_query_engine.query(
    "which departments/teams use genAI the most and how are they using it?"
)
print(str(base_response))


# **NOTE**: the relevant page numbers are 32-38. The response with contextual retrieval retrieves the slide detailing IT use cases, hence giving a more detailed response on the IT side.

# In[ ]:


get_source_page_nums(response)
get_source_page_nums(base_response)


# In[ ]:


# look at an example retrieved source node
print(response.source_nodes[0].get_content(metadata_mode="all"))


# In this next question, the same sources are retrieved with and without contextual retrieval, and the answer is correct for both approaches. This is thanks for LlamaParse Premium's ability to comprehend graphs.

# In[ ]:


query = "what are relevant insights from the 'deep dive on infrastructure' section in terms of model preferences, cost, deployment environments?"

response = query_engine.query(query)
print(str(response))


# In[ ]:


base_response = base_query_engine.query(query)
print(str(base_response))


# In[ ]:


get_source_page_nums(response)
get_source_page_nums(base_response)


# In[ ]:


# look at an example retrieved source node
print(response.source_nodes[2].get_content(metadata_mode="all"))

