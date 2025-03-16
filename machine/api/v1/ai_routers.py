import json
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from openai import OpenAI
import os
import requests
from typing import Dict
from core.response import Ok
from fastapi import APIRouter
from core.settings import settings
from machine.services.workflows.ai_tool_provider import AIToolProvider, LLMModelName
from core.exceptions import *
from dotenv import load_dotenv
from fastapi_mail import FastMail
from machine.models import *
from machine.controllers import *
from machine.providers.internal import InternalProvider
from datetime import datetime, timedelta
from passlib.context import CryptContext
from machine.schemas.requests.auth import *
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends
from uuid import UUID
from core.utils.auth_utils import verify_token
from ...schemas.requests.ai import GenerateLearningPathRequest
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
load_dotenv()
from openai import OpenAI

import json
from typing import Dict, List, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from openai import OpenAI

class LargeInputProcessor:
    def __init__(self, 
                 provider="gemini", 
                 openai_model_name="gpt-4-turbo-preview", 
                 gemini_model_name="gemini-1.5-pro",
                 max_tokens_per_chunk=25000, 
                 openai_api_key=None,
                 gemini_api_key=None):
        
        self.provider = provider.lower()
        self.max_tokens_per_chunk = max_tokens_per_chunk
        
        # Initialize OpenAI client if required
        if self.provider == "openai" or self.provider == "both":
            self.openai_model_name = openai_model_name
            self.openai_client = OpenAI(api_key=openai_api_key)
        
        # Initialize Gemini client if required
        if self.provider == "gemini" or self.provider == "both":
            self.gemini_model_name = gemini_model_name
            self.gemini_client = ChatGoogleGenerativeAI(
                model=gemini_model_name,
                temperature=0.7,
                max_tokens=4000,
                timeout=None,
                max_retries=2,
                api_key=gemini_api_key
            )
        
    def estimate_token_count(self, text):
        """Rough estimation of token count (4 chars ≈ 1 token)"""
        return len(text) // 4
        
    def chunk_lessons(self, lessons: List[Dict], max_tokens: int) -> List[List[Dict]]:
        """Split lessons into chunks that fit within token limits"""
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for lesson in lessons:
            # Estimate tokens for this lesson
            lesson_json = json.dumps(lesson)
            lesson_tokens = self.estimate_token_count(lesson_json)
            
            # If adding this lesson would exceed the limit, start a new chunk
            if current_tokens + lesson_tokens > max_tokens and current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_tokens = 0
            
            # Add lesson to current chunk
            current_chunk.append(lesson)
            current_tokens += lesson_tokens
        
        # Add the last chunk if it's not empty
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks
        
    def generate_learning_path_in_chunks(
        self,
        student_name: str,
        course_name: str,
        professor_name: str,
        course_info: Dict,
        lessons: List[Dict],
        student_goal: str
    ) -> Dict:
        """Process large input by breaking lessons into manageable chunks"""
        
        # 1. Split lessons into chunks
        lesson_chunks = self.chunk_lessons(lessons, self.max_tokens_per_chunk // 2)  # Leave room for other parts of prompt
        
        # 2. Process each chunk and collect recommended lessons
        all_recommended_lessons = []
        
        for i, lesson_chunk in enumerate(lesson_chunks):
            chunk_info = f"Processing chunk {i+1} of {len(lesson_chunks)}"
            print(chunk_info)
            
            # Create prompt for this chunk only
            chunk_prompt = self.generate_chunk_prompt(
                student_name, 
                course_name, 
                professor_name, 
                course_info,
                lesson_chunk,
                student_goal,
                chunk_index=i,
                total_chunks=len(lesson_chunks)
            )
            
            # Get response for this chunk
            try:
                # First try with primary provider
                chunk_response = self.call_llm_api(chunk_prompt)
                
                # Extract recommended lessons from this chunk
                if "learning_path" in chunk_response and "recommend_lessons" in chunk_response["learning_path"]:
                    chunk_lessons = chunk_response["learning_path"]["recommend_lessons"]
                    all_recommended_lessons.extend(chunk_lessons)
                
            except Exception as e:
                print(f"Error processing chunk with primary provider: {str(e)}")
                
                # If we have both providers configured, try the alternative
                if self.provider == "both":
                    try:
                        # Toggle provider temporarily
                        temp_provider = "gemini" if self.provider == "openai" else "openai"
                        print(f"Retrying with {temp_provider}...")
                        
                        chunk_response = self.call_llm_api(chunk_prompt, override_provider=temp_provider)
                        
                        if "learning_path" in chunk_response and "recommend_lessons" in chunk_response["learning_path"]:
                            chunk_lessons = chunk_response["learning_path"]["recommend_lessons"]
                            all_recommended_lessons.extend(chunk_lessons)
                    
                    except Exception as backup_error:
                        print(f"Backup provider also failed: {str(backup_error)}")
                        # Continue with next chunk
            
        # 3. Final integration - create a comprehensive learning path
        if all_recommended_lessons:
            # Sort lessons by any relevant criteria (if needed)
            # This example sorts by title, but you might have a better criterion
            all_recommended_lessons.sort(key=lambda x: x.get("title", ""))
            
            # Create the final integrated response
            final_response = {
                "learning_path": {
                    "title": f"Personalized Learning Path for {student_goal}",
                    "description": f"Custom learning path for {student_name} to achieve: {student_goal}",
                    "recommend_lessons": all_recommended_lessons
                }
            }
            
            return final_response
        else:
            raise Exception("Failed to generate recommendations from any chunk")
    
    def generate_chunk_prompt(
        self,
        student_name: str,
        course_name: str,
        professor_name: str,
        course_info: Dict,
        lessons_chunk: List[Dict],
        student_goal: str,
        chunk_index: int,
        total_chunks: int
    ) -> str:
        """Generate a prompt for a specific chunk of lessons"""
        
        # Add context about chunking to help the model understand
        chunk_context = f"""
        # Learning Path Generation Task - Chunk {chunk_index + 1} of {total_chunks}
        
        ## Chunking Context
        You are analyzing a subset of lessons ({len(lessons_chunk)} out of total lessons) for a course.
        This is chunk {chunk_index + 1} of {total_chunks} being processed separately due to size limitations.
        Focus only on the lessons provided in this chunk when making recommendations.
        """
        
        prompt = f"""
        {chunk_context}

        ## Student Information
        - Student Name: {student_name}
        - Course: {course_name} (ID: {course_info.get('courseID', 'N/A')})
        - Professor: {professor_name}
        - Student's Learning Goal: "{student_goal}"

        ## Course Information
        - Start Date: {course_info.get('start_date')}
        - End Date: {course_info.get('end_date')}
        - Learning Outcomes: {json.dumps(course_info.get('learning_outcomes', []))}

        ## Available Lessons in This Chunk
        This chunk contains {len(lessons_chunk)} lessons. Here is detailed information about each lesson:

        {json.dumps(lessons_chunk, indent=2)}

        ## Task Requirements
        
        Please analyze ONLY these lessons and recommend any that will help the student achieve their stated goal.
        For each recommended lesson, provide:
        1. Recommended content that explains what to focus on
        2. An explanation of why this content is important for the student's goal
        3. 2-3 modules per lesson that break down the key concepts to master
        
        ## Output Format
        Provide your response in the following JSON format:
        """

        json_format = """
        {
          "learning_path": {
            "recommend_lessons": [
              {
                "title": "Lesson Title",
                "recommended_content": "Detailed explanation of what to focus on in this lesson...",
                "explain": "Explanation of why this content is important for the student's goal...",
                "modules": [
                  {
                    "title": "Module Title",
                    "objectives": ["Learning objective 1", "Learning objective 2", "Learning objective 3"]
                  },
                  {
                    "title": "Second Module Title",
                    "objectives": ["Another learning objective 1", "Another learning objective 2"]
                  }
                ]
              }
            ]
          }
        }
        """

        prompt += json_format

        return prompt
    
    def call_llm_api(self, prompt: str, override_provider: Optional[str] = None) -> Dict:
        """
        Call LLM API (OpenAI or Gemini) with a single chunk
        
        Args:
            prompt: Formatted prompt for the LLM API
            override_provider: Optionally override the configured provider
            
        Returns:
            Dictionary containing the parsed JSON response
        """
        # Determine which provider to use
        provider = override_provider if override_provider else self.provider
        
        if provider == "openai" or (provider == "both" and override_provider != "gemini"):
            return self._call_openai_api(prompt)
        elif provider == "gemini" or (provider == "both" and override_provider == "gemini"):
            return self._call_gemini_api(prompt)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def _call_openai_api(self, prompt: str) -> Dict:
        """
        Call OpenAI API with a single chunk, with improved error handling
        
        Args:
            prompt: Formatted prompt for the OpenAI API
            
        Returns:
            Dictionary containing the parsed JSON response
        """
        try:
            response = self.openai_client.chat.completions.create(
                model=self.openai_model_name,
                messages=[
                    {"role": "system", "content": "You are an expert educational AI assistant that creates personalized learning paths for computer science students."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000
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
                # This handles cases where the model returns Markdown code blocks or explanatory text
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
    
    def _call_gemini_api(self, prompt: str) -> Dict:
        """
        Call Google Gemini API via LangChain, with error handling
        
        Args:
            prompt: Formatted prompt for the Gemini API
            
        Returns:
            Dictionary containing the parsed JSON response
        """
        try:
            # Format messages for LangChain's ChatGoogleGenerativeAI
            messages = [
                {"role": "system", "content": "You are an expert educational AI assistant that creates personalized learning paths for computer science students."},
                {"role": "user", "content": prompt}
            ]
            
            # Convert to LangChain message format
            from langchain_core.messages import SystemMessage, HumanMessage
            lc_messages = [
                SystemMessage(content=messages[0]["content"]),
                HumanMessage(content=messages[1]["content"])
            ]
            
            # Invoke the Gemini model
            response = self.gemini_client.invoke(lc_messages)
            
            # Extract content from LangChain response
            response_text = response.content
            
            # Verify the content is not empty
            if not response_text or not response_text.strip():
                raise ValueError("Empty content received from Gemini API")
                
            # Log the raw response text for debugging
            print(f"Gemini response text length: {len(response_text)}")
            print(f"Gemini response text preview: {response_text[:100]}...")
            
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
                    print(f"Failed to parse JSON response from Gemini: {str(json_err)}")
                    print(f"Response text: {response_text}")
                    raise ValueError(f"Invalid JSON response from Gemini: {str(json_err)}")
            
        except Exception as e:
            print(f"Error calling Gemini API: {str(e)}")
            raise e



router = APIRouter(prefix="/ai", tags=["ai"])
@router.post("/generate-learning-path")
async def generate_learning_path(
    request: GenerateLearningPathRequest,
    token: str = Depends(oauth2_scheme),
    courses_controller: CoursesController = Depends(InternalProvider().get_courses_controller),
    student_courses_controller: StudentCoursesController = Depends(InternalProvider().get_studentcourses_controller),
    professor_controller: ProfessorController = Depends(InternalProvider().get_professor_controller),
    student_controller: StudentController = Depends(InternalProvider().get_student_controller),
    learning_path_controller: LearningPathsController = Depends(InternalProvider().get_learningpaths_controller),
    modules_controller: ModulesController = Depends(InternalProvider().get_modules_controller),
    recommend_lessons_controller: RecommendLessonsController = Depends(InternalProvider().get_recommendlessons_controller),
    documents_controller: DocumentsController = Depends(InternalProvider().get_documents_controller),
    extracted_text_controller: ExtractedTextController = Depends(InternalProvider().get_extracted_text_controller),
    lessons_controller: LessonsController = Depends(InternalProvider().get_lessons_controller),
):
    """
    Generate a personalized learning path for a student based on their goals and course content.
    
    Args:
        request: Contains course_id and student's learning goal
        Other parameters: Controllers for different database models
        
    Returns:
        Dict containing the generated learning path details
    """
    # Verify token
    payload = verify_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise BadRequestException(message="Your account is not authorized. Please log in again.")
    
    student = await student_controller.student_repository.first(where_=[Student.id == user_id])
    if not student:
        raise NotFoundException(message="Your account is not allowed to access this feature.")
    
    if not request.goal or not request.course_id:
        raise BadRequestException(message="Please provide course_id and goal.")
    
    # Fetch course details
    course = await courses_controller.courses_repository.first(where_=[Courses.id == request.course_id])
    if not course:
        raise NotFoundException(message="Course not found.")
    
    # Fetch professor information
    professor = await professor_controller.professor_repository.first(where_=[Professor.id == course.professor_id])
    if not professor:
        raise NotFoundException(message="Professor information not found.")
    
    # Fetch all lessons for the course
    lessons = await lessons_controller.lessons_repository.get_many(where_=[Lessons.course_id == request.course_id])
    if not lessons:
        raise NotFoundException(message="No lessons found for this course.")
    
    # Prepare data structure for all lessons with their documents and extracted text
    lessons_data = []
    for lesson in lessons:
        # Get documents for this lesson
        documents = await documents_controller.documents_repository.get_many(where_=[Documents.lesson_id == lesson.id])
        
        documents_data = []
        for document in documents:
            # Get extracted text for each document
            extracted = await extracted_text_controller.extracted_text_repository.first(
                where_=[ExtractedText.document_id == document.id]
            )
            
            # Only include documents with extracted text
            if extracted and extracted.extracted_content:
                documents_data.append({
                    "name": document.name,
                    "type": document.type,
                    "description": document.description,
                    "extracted_content": extracted.extracted_content
                })
        
        lessons_data.append({
            "id": str(lesson.id),
            "title": lesson.title,
            "description": lesson.description,
            "order": lesson.order,
            "learning_outcomes": lesson.learning_outcomes if lesson.learning_outcomes else [],
            "documents": documents_data
        })
    
    # Sort lessons by their order
    lessons_data.sort(key=lambda x: x["order"])
    
    # Calculate approximate timeframe for the learning path
    start_date = datetime.now()
    end_date = course.end_date if course.end_date else (start_date + timedelta(days=90))
    
    # Get API keys from environment variables
    #openai_api_key = os.getenv("OPENAI_API_KEY")
    gemini_api_key = os.getenv("GOOGLE_GENAI_API_KEY")
    
    # Initialize the processor with both providers for fallback capability
    processor = LargeInputProcessor(
        provider="gemini",  # Use both providers with fallback capability
        openai_model_name="gpt-4-turbo-preview",
        gemini_model_name="gemini-1.5-pro",
        max_tokens_per_chunk=25000,
        #openai_api_key=openai_api_key,
        gemini_api_key=gemini_api_key
    )
    
    try:
        # Call the processor to generate learning path
        parsed_response = processor.generate_learning_path_in_chunks(
            student_name=student.name,
            course_name=course.name,
            professor_name=f"{professor.fullname}",
            course_info={
                "id": str(course.id),
                "name": course.name,
                "learning_outcomes": course.learning_outcomes if course.learning_outcomes else [],
                "start_date": course.start_date.isoformat() if course.start_date else start_date.isoformat(),
                "end_date": course.end_date.isoformat() if course.end_date else end_date.isoformat(),
                "courseID": course.courseID
            },
            lessons=lessons_data,
            student_goal=request.goal
        )
        
        return Ok(parsed_response)
        
    except Exception as e:
        print(f"Error generating learning path: {str(e)}")
        raise ApplicationException(message=f"Failed to generate learning path: {str(e)}")
