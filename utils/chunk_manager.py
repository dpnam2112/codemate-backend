import json
from typing import Dict, List, Any, Optional, Union, Callable
import math
import os
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from openai import OpenAI
from core.settings import settings
# Single place to get the API key - prioritize environment variable
def get_gemini_api_key():
    return settings.GEMINI_API_KEY

# Configure the native Google AI library only if we have a key
api_key = get_gemini_api_key()
if api_key:
    genai.configure(api_key=api_key)
class ChunkingManager:
    """
    A reusable class for handling chunking of large inputs for AI processing,
    with support for multiple LLM providers and automatic fallback.
    """
        
    def __init__(self, 
                provider: str = "gemini",
                openai_model_name: str = "gpt-4-turbo-preview",
                gemini_model_name: str = "gemini-1.5-pro",
                max_tokens_per_chunk: int = 25000,
                openai_api_key: Optional[str] = None,
                temperature: float = 0.7,
                max_output_tokens: int = 4000):
        """
        Initialize the ChunkingManager with provider settings and token limits.
        
        Args:
            provider: AI provider to use ("gemini", "openai", or "both" for fallback capability)
            openai_model_name: Model name for OpenAI calls
            gemini_model_name: Model name for Gemini calls
            max_tokens_per_chunk: Maximum tokens per chunk (will be divided by 2 to leave room for response)
            openai_api_key: API key for OpenAI
            temperature: Temperature setting for generation
            max_output_tokens: Maximum tokens for model response
        """
        self.provider = provider.lower()
        self.max_tokens_per_chunk = max_tokens_per_chunk
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        
        # Initialize OpenAI client if required
        if self.provider == "openai" or self.provider == "both":
            self.openai_model_name = openai_model_name
            self.openai_client = OpenAI(api_key=openai_api_key)
        
        # Initialize Gemini client if required
        if self.provider == "gemini" or self.provider == "both":
            self.gemini_model_name = gemini_model_name
            # Use the centralized API key management
            gemini_api_key = get_gemini_api_key()
            self.gemini_client = ChatGoogleGenerativeAI(
                model=gemini_model_name,
                temperature=temperature,
                max_tokens=max_output_tokens,
                timeout=None,
                max_retries=2,
                api_key=gemini_api_key
            )
    
    def estimate_token_count(self, text: str) -> int:
        """
        Roughly estimate token count based on character count.
        
        Args:
            text: The text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        return len(text) // 4
    
    def chunk_data(self, 
                  data: List[Dict], 
                  max_tokens: int,
                  token_estimation_field: Optional[str] = None) -> List[List[Dict]]:
        """
        Split a list of dictionaries into chunks that fit within token limits.
        
        Args:
            data: List of dictionaries to chunk
            max_tokens: Maximum tokens per chunk
            token_estimation_field: Optional specific field to use for estimation (e.g., 'extracted_content')
                                   If None, the entire dictionary is used
            
        Returns:
            List of chunked data
        """
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for item in data:
            # Estimate tokens for this item
            if token_estimation_field and token_estimation_field in item:
                # If we're estimating based on a specific field
                item_tokens = self.estimate_token_count(str(item[token_estimation_field]))
                # Add small overhead for the rest of the object
                item_tokens += self.estimate_token_count(json.dumps({k: v for k, v in item.items() if k != token_estimation_field}))
            else:
                # Otherwise estimate based on the whole object
                item_json = json.dumps(item)
                item_tokens = self.estimate_token_count(item_json)
            
            # If adding this item would exceed the limit, start a new chunk
            if current_tokens + item_tokens > max_tokens and current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_tokens = 0
            
            # If a single item is larger than max_tokens, we need to handle it differently
            # Either by splitting it further or including it alone in a chunk
            if item_tokens > max_tokens:
                print(f"Warning: Item exceeds maximum token size ({item_tokens} > {max_tokens}). Including as a single item chunk.")
                # If current chunk has items, add it to chunks first
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = []
                    current_tokens = 0
                
                # Add this oversized item as its own chunk
                chunks.append([item])
                continue
            
            # Add item to current chunk
            current_chunk.append(item)
            current_tokens += item_tokens
        
        # Add the last chunk if it's not empty
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks
    
    def process_in_chunks(self, 
                         data: List[Dict],
                         prompt_generator: Callable[[List[Dict], int, int], str],
                         result_extractor: Callable[[Dict], List[Any]],
                         token_estimation_field: Optional[str] = None,
                         system_message: str = "You are a helpful AI assistant") -> List[Any]:
        """
        Process large input by breaking into manageable chunks, calling an AI model,
        and combining results.
        
        Args:
            data: List of dictionaries to process in chunks
            prompt_generator: Function that takes (chunk_data, chunk_index, total_chunks) and returns a prompt string
            result_extractor: Function that extracts relevant results from the model response
            token_estimation_field: Optional field name to use for token estimation
            system_message: System message to use for the AI calls
            
        Returns:
            Combined results from all chunks
        """
        # 1. Split data into chunks
        effective_max_tokens = self.max_tokens_per_chunk // 2  # Leave room for other parts of prompt
        data_chunks = self.chunk_data(data, effective_max_tokens, token_estimation_field)
        
        # 2. Process each chunk and collect results
        all_results = []
        
        for i, data_chunk in enumerate(data_chunks):
            chunk_info = f"Processing chunk {i+1} of {len(data_chunks)}"
            print(chunk_info)
            
            # Generate prompt for this chunk
            chunk_prompt = prompt_generator(data_chunk, i, len(data_chunks))
            
            # Get response for this chunk
            try:
                # First try with primary provider
                chunk_response = self.call_llm_api(chunk_prompt, system_message)
                
                # Extract results from this chunk
                chunk_results = result_extractor(chunk_response)
                if chunk_results:
                    all_results.extend(chunk_results)
                else:
                    print(f"Warning: No valid results extracted from chunk {i+1}")
                
            except Exception as e:
                print(f"Error processing chunk with primary provider: {str(e)}")
                
                # If we have both providers configured, try the alternative
                if self.provider == "both":
                    try:
                        # Toggle provider temporarily
                        temp_provider = "gemini" if self.provider == "openai" else "openai"
                        print(f"Retrying with {temp_provider}...")
                        
                        chunk_response = self.call_llm_api(chunk_prompt, system_message, override_provider=temp_provider)
                        
                        chunk_results = result_extractor(chunk_response)
                        if chunk_results:
                            all_results.extend(chunk_results)
                        else:
                            print(f"Warning: No valid results extracted from chunk {i+1} with backup provider")
                    
                    except Exception as backup_error:
                        print(f"Backup provider also failed: {str(backup_error)}")
                        # Continue with next chunk
        
        return all_results
    
    def call_llm_api(self, prompt: str, system_message: str, override_provider: Optional[str] = 'gemini') -> Dict:
        """
        Call LLM API (OpenAI or Gemini) with a single chunk
        
        Args:
            prompt: Formatted prompt for the LLM API
            system_message: System message to use for the AI call
            override_provider: Optionally override the configured provider
            
        Returns:
            Dictionary containing the parsed JSON response
        """
        # Determine which provider to use
        provider = override_provider if override_provider else self.provider
        
        if provider == "openai" or (provider == "both" and override_provider != "gemini"):
            return self._call_openai_api(prompt, system_message)
        elif provider == "gemini" or (provider == "both" and override_provider == "gemini"):
            return self._call_gemini_api(prompt, system_message)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def _call_openai_api(self, prompt: str, system_message: str) -> Dict:
        """
        Call OpenAI API with a single chunk, with improved error handling
        
        Args:
            prompt: Formatted prompt for the OpenAI API
            system_message: System message to use for the AI call
            
        Returns:
            Dictionary containing the parsed JSON response
        """
        try:
            response = self.openai_client.chat.completions.create(
                model=self.openai_model_name,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_output_tokens
            )
            
            # Verify we have a response and it has content
            if not response or not response.choices or len(response.choices) == 0:
                raise ValueError("Empty response received from OpenAI API")
                
            response_text = response.choices[0].message.content
            
            # Verify the content is not empty
            if not response_text or not response_text.strip():
                raise ValueError("Empty content received from OpenAI API")
                
            # Log the raw response text for debugging (optional)
            print(f"OpenAI response text length: {len(response_text)}")
            print(f"OpenAI response text preview: {response_text[:100]}...")
            
            # Try to parse JSON with better error handling
            try:
                return json.loads(response_text)
            except json.JSONDecodeError as json_err:
                # Check if response contains valid JSON embedded within other text
                import re
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```|(\{[\s\S]*\})', response_text)
                if json_match:
                    json_str = json_match.group(1) or json_match.group(2)
                    return json.loads(json_str)
                else:
                    print(f"Failed to parse JSON response from OpenAI: {str(json_err)}")
                    print(f"Response text: {response_text}")
                    raise ValueError(f"Invalid JSON response from OpenAI: {str(json_err)}")
            
        except Exception as e:
            print(f"Error calling OpenAI API: {str(e)}")
            
            # For token limit errors, provide more specific information
            if "tokens" in str(e).lower() and "exceed" in str(e).lower():
                print("Token limit exceeded. Consider reducing chunk size or prompt length.")
            
            raise e  # Re-raise to allow fallback to other provider if available



    def _call_gemini_api(self, prompt: str, system_message: str) -> Dict:
        """
        Call Google Gemini API with error handling, send a prompt and system message,
        and return the response as a dictionary.

        Args:
            prompt: Formatted prompt for the Gemini API
            system_message: System message to use for the AI call

        Returns:
            Dictionary containing the parsed JSON response
        """
        try:
            # Set up the model and generation config
            generation_config = {
                "temperature": self.temperature,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": self.max_output_tokens,
                "response_mime_type": "text/plain",
            }

            # Get the API key from the same centralized function
            api_key = get_gemini_api_key()
            if not api_key:
                raise ValueError("Gemini API key not found in environment variables")
            
            # Configure the model with the API key
            model = genai.GenerativeModel(
                model_name=self.gemini_model_name, 
                generation_config=generation_config
            )
            
            # Start a chat session with an empty history
            chat_session = model.start_chat(history=[])
            
            # Prepare system and human messages for the chat session
            chat_session.send_message(system_message)
            response = chat_session.send_message(prompt)
            # Get the response text from the model's response
            response_text = response.text.strip()

            # If the response is empty or invalid, raise an error
            if not response_text:
                raise ValueError("Empty content received from Gemini API")

            # Log the raw response text for debugging purposes
            print(f"Gemini response text length: {len(response_text)}")
            print(f"Gemini response text preview: {response_text[:100]}...")

            # Attempt to parse the response as JSON
            try:
                return json.loads(response_text)
            except json.JSONDecodeError as json_err:
                # In case the response contains embedded JSON in non-JSON format, try to extract it
                import re
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```|(\{[\s\S]*\})', response_text)
                if json_match:
                    json_str = json_match.group(1) or json_match.group(2)
                    return json.loads(json_str)
                else:
                    print(f"Failed to parse JSON response from Gemini: {str(json_err)}")
                    print(f"Response text: {response_text}")
                    raise ValueError(f"Invalid JSON response from Gemini: {str(json_err)}")

        except Exception as e:
            print(f"Error calling Gemini API: {str(e)}")
            raise e
