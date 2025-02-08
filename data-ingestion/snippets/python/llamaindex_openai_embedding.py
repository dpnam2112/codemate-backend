#!/usr/bin/env python
# coding: utf-8

# <a href="https://colab.research.google.com/github/run-llama/llama_index/blob/main/docs/docs/examples/embeddings/OpenAI.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>

# # OpenAI Embeddings

# If you're opening this Notebook on colab, you will probably need to install LlamaIndex 🦙.

# In[ ]:


get_ipython().run_line_magic('pip', 'install llama-index-embeddings-openai')


# In[ ]:


get_ipython().system('pip install llama-index')


# In[ ]:


import os

os.environ["OPENAI_API_KEY"] = "sk-..."


# In[ ]:


from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core import Settings

embed_model = OpenAIEmbedding(embed_batch_size=10)
Settings.embed_model = embed_model


# ## Using OpenAI `text-embedding-3-large` and `text-embedding-3-small`
# 
# Note, you may have to update your openai client: `pip install -U openai`

# In[ ]:


# get API key and create embeddings
from llama_index.embeddings.openai import OpenAIEmbedding

embed_model = OpenAIEmbedding(model="text-embedding-3-large")

embeddings = embed_model.get_text_embedding(
    "Open AI new Embeddings models is great."
)


# In[ ]:


print(embeddings[:5])


# In[ ]:


print(len(embeddings))


# In[ ]:


# get API key and create embeddings
from llama_index.embeddings.openai import OpenAIEmbedding

embed_model = OpenAIEmbedding(
    model="text-embedding-3-small",
)

embeddings = embed_model.get_text_embedding(
    "Open AI new Embeddings models is awesome."
)


# In[ ]:


print(len(embeddings))


# ## Change the dimension of output embeddings
# Note: Make sure you have the latest OpenAI client

# In[ ]:


# get API key and create embeddings
from llama_index.embeddings.openai import OpenAIEmbedding


embed_model = OpenAIEmbedding(
    model="text-embedding-3-large",
    dimensions=512,
)

embeddings = embed_model.get_text_embedding(
    "Open AI new Embeddings models with different dimensions is awesome."
)
print(len(embeddings))

