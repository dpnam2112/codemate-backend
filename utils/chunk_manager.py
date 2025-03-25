import json
from typing import Dict, List, Any, Optional, Callable
import re
from core.settings import settings
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from openai import OpenAI

def get_gemini_api_key():
    return settings.GEMINI_API_KEY

api_key = get_gemini_api_key()
if api_key:
    genai.configure(api_key=api_key)

class ChunkingManager:
    def __init__(self, 
                 provider: str = "gemini",
                 openai_model_name: str = "gpt-4-turbo-preview",
                 gemini_model_name: str = "gemini-1.5-pro",
                 max_tokens_per_chunk: int = 15000,  # Reduced from 25000
                 openai_api_key: Optional[str] = None,
                 temperature: float = 0.7,
                 max_output_tokens: int = 8000):  # Increased from 4000
        self.provider = provider.lower()
        self.max_tokens_per_chunk = max_tokens_per_chunk
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        
        if self.provider in ["openai", "both"]:
            self.openai_model_name = openai_model_name
            self.openai_client = OpenAI(api_key=openai_api_key)
        
        if self.provider in ["gemini", "both"]:
            self.gemini_model_name = gemini_model_name
            self.gemini_client = ChatGoogleGenerativeAI(
                model=gemini_model_name,
                temperature=temperature,
                max_tokens=max_output_tokens,
                timeout=None,
                max_retries=2,
                api_key=get_gemini_api_key()
            )
    
    def estimate_token_count(self, text: str) -> int:
        return len(text) // 4
    
    def chunk_data(self, data: List[Dict], max_tokens: int, token_estimation_field: Optional[str] = None) -> List[List[Dict]]:
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for item in data:
            if token_estimation_field and token_estimation_field in item:
                item_tokens = self.estimate_token_count(str(item[token_estimation_field])) + \
                            self.estimate_token_count(json.dumps({k: v for k, v in item.items() if k != token_estimation_field}))
            else:
                item_tokens = self.estimate_token_count(json.dumps(item))
            
            if current_tokens + item_tokens > max_tokens and current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_tokens = 0
            
            if item_tokens > max_tokens:
                print(f"Warning: Item exceeds max token size ({item_tokens} > {max_tokens}). Including as single chunk.")
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = []
                    current_tokens = 0
                chunks.append([item])
                continue
            
            current_chunk.append(item)
            current_tokens += item_tokens
        
        if current_chunk:
            chunks.append(current_chunk)
        return chunks
    
    def process_in_chunks(self, 
                         data: List[Dict],
                         prompt_generator: Callable[[List[Dict], int, int], str],
                         result_extractor: Callable[[Any], Dict],
                         token_estimation_field: Optional[str] = None,
                         system_message: str = "You are a helpful AI assistant") -> Dict:
        effective_max_tokens = self.max_tokens_per_chunk // 2  # Still leaves room for response
        data_chunks = self.chunk_data(data, effective_max_tokens, token_estimation_field)
        
        combined_result = {
            "recommend_lessons": [],
            "modules": []
        }
        
        for i, data_chunk in enumerate(data_chunks):
            print(f"Processing chunk {i+1} of {len(data_chunks)}")
            chunk_prompt = prompt_generator(data_chunk, i, len(data_chunks))
            
            try:
                chunk_response = self.call_llm_api(chunk_prompt, system_message)
                chunk_results = result_extractor(chunk_response)
                
                if not chunk_results:
                    print(f"Warning: No valid results from chunk {i+1}")
                    continue
                
                if i == 0:
                    for key in ["learning_path_start_date", "learning_path_end_date", 
                              "learning_path_objective", "learning_path_progress", 
                              "student_id", "course_id"]:
                        if key in chunk_results:
                            combined_result[key] = chunk_results[key]
                
                if "recommend_lessons" in chunk_results:
                    combined_result["recommend_lessons"].extend(chunk_results["recommend_lessons"])
                if "modules" in chunk_results:
                    combined_result["modules"].extend(chunk_results["modules"])
                    
            except Exception as e:
                print(f"Error in chunk {i+1}: {str(e)}")
                if self.provider == "both":
                    # Fallback logic remains unchanged
                    pass
        
        return combined_result
    
    def call_llm_api(self, prompt: str, system_message: str, override_provider: Optional[str] = None) -> Any:
        provider = override_provider or self.provider
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
        try:
            generation_config = {
                "temperature": self.temperature,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": self.max_output_tokens,
                "response_mime_type": "application/json"  # Force JSON output
            }
            
            model = genai.GenerativeModel(
                model_name=self.gemini_model_name,
                generation_config=generation_config
            )
            
            # Append instruction to ensure complete JSON
            prompt += "\n\nEnsure the response is a complete, valid JSON object. Do not truncate or leave incomplete structures."
            
            chat_session = model.start_chat(history=[])
            chat_session.send_message(system_message)
            response = chat_session.send_message(prompt)
            response_text = response.text.strip()
            
            if not response_text:
                raise ValueError("Empty response from Gemini API")
            
            print(f"Gemini response text length: {len(response_text)}")
            print(f"Gemini response text preview: {response_text[:100]}...")
            
            try:
                return json.loads(response_text)
            except json.JSONDecodeError as e:
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```|(\{[\s\S]*\})', response_text)
                if json_match:
                    json_str = json_match.group(1) or json_match.group(2)
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        # Fallback: Ask the model to fix the JSON
                        fix_prompt = f"The following JSON is malformed: {response_text}\nPlease provide a corrected, complete version."
                        fix_response = chat_session.send_message(fix_prompt)
                        return json.loads(fix_response.text.strip())
                else:
                    raise ValueError(f"Invalid JSON from Gemini: {str(e)}")
                    
        except Exception as e:
            print(f"Error calling Gemini API: {str(e)}")
            raise