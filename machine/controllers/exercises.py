from uuid import UUID

from openai import AsyncOpenAI, OpenAI
from sqlalchemy import select
from core.controller import BaseController
from core.exceptions.base import NotFoundException
from machine.models import Exercises
from machine.models.coding_assistant import CodingConversation, Conversation, Message
from machine.repositories import ExercisesRepository
from core.db import Transactional


class ExercisesController(BaseController[Exercises]):
    def __init__(
        self, exercises_repository: ExercisesRepository, llm_client: AsyncOpenAI
    ):
        super().__init__(
            model_class=Exercises, repository=exercises_repository
        )
        self.exercises_repository = exercises_repository
        self.llm_client = llm_client

    @Transactional()
    async def get_coding_assistant_conversation_messages(
        self, user_id: UUID, coding_exercise_id: UUID
    ):
        # Retrieve the exercise record
        exercise = await self.repository.first(where_=[Exercises.id == coding_exercise_id])
        if not exercise:
            raise NotFoundException(message="Exercise not found.")
        
        session = self.repository.session

        # Ensure the exercise has an associated conversation
        if not getattr(exercise, "conversation_id", None):
            conversation = Conversation()
            session.add(conversation)
            # Flush to get an ID assigned to the new conversation
            await session.flush()
            exercise.conversation_id = conversation.id
        else:
            conversation = await session.get(Conversation, exercise.conversation_id)
            if not conversation:
                conversation = Conversation()
                session.add(conversation)
                await session.flush()
                exercise.conversation_id = conversation.id

        # Check for a coding conversation linking this user and conversation
        stmt = select(CodingConversation).where(
            CodingConversation.user_id == user_id,
            CodingConversation.conversation_id == conversation.id
        )
        result = await session.execute(stmt)
        coding_conv = result.scalars().first()

        if not coding_conv:
            # Create a new coding conversation if none exists
            coding_conv = CodingConversation(user_id=user_id, conversation_id=conversation.id)
            session.add(coding_conv)
            await session.flush()

        # Retrieve all messages for the conversation
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.asc())
        )
        result = await session.execute(stmt)
        messages = result.scalars().all()

        return messages

    @Transactional()
    async def push_coding_assistant_message(
        self, user_id: UUID, coding_exercise_id: UUID, content: str, role: str = "user"
    ):
        return await self._push_coding_assistant_message(
            user_id, coding_exercise_id, content, role
        )

    async def _push_coding_assistant_message(
        self, user_id: UUID, coding_exercise_id: UUID, content: str, role: str = "user"
    ):
        """
        Push a new message into the coding assistant conversation but not in transaction.
        
        Args:
            user_id (UUID): The ID of the user sending the message.
            coding_exercise_id (UUID): The ID of the coding exercise.
            content (str): The content of the message.
            role (str): The role of the sender (e.g., "user" or "assistant"). Default is "user".
            
        Returns:
            Message: The newly created message.
        """
        session = self.repository.session

        # Retrieve the exercise record
        exercise = await self.repository.first(where_=[Exercises.id == coding_exercise_id])
        if not exercise:
            raise NotFoundException(message="Exercise not found.")

        # Ensure the exercise has an associated conversation
        if not getattr(exercise, "conversation_id", None):
            conversation = Conversation()
            session.add(conversation)
            await session.flush()
            exercise.conversation_id = conversation.id
        else:
            conversation = await session.get(Conversation, exercise.conversation_id)
            if not conversation:
                conversation = Conversation()
                session.add(conversation)
                await session.flush()
                exercise.conversation_id = conversation.id

        # Ensure there is a coding conversation linking the user and the conversation
        stmt = select(CodingConversation).where(
            CodingConversation.user_id == user_id,
            CodingConversation.conversation_id == conversation.id
        )
        result = await session.execute(stmt)
        coding_conv = result.scalars().first()

        if not coding_conv:
            coding_conv = CodingConversation(user_id=user_id, conversation_id=conversation.id)
            session.add(coding_conv)
            await session.flush()

        # Create and add the new message to the conversation
        new_message = Message(
            role=role,
            content=content,
            conversation_id=conversation.id
        )
        session.add(new_message)
        await session.flush()  # Flush to assign an ID if needed

        return new_message

    async def invoke_coding_assistant(
        self,
        user_id: UUID,
        coding_exercise_id: UUID,
        content: str,
        user_solution: str,
        history_length=10
    ):
        """
        Invoke the Coding Assistant agent powered by LLM and stream the response.
        
        Steps:
        1. Push the user's message.
        2. Retrieve the last HISTORY_LENGTH messages from the conversation.
        3. Retrieve the problem description from the exercise record.
        4. Construct a system prompt with guardrails, incorporating the problem description
           and the user's solution.
        5. Invoke the LLM's Chat Completions API in streaming mode.
        6. Stream back the chunks while accumulating the full response.
        7. After streaming completes, persist the assistant's reply to the DB.
        
        Args:
            user_id (UUID): The ID of the user.
            coding_exercise_id (UUID): The ID of the coding exercise.
            content (str): The new user message.
            user_solution (str): The user's current work/solution attempt.
            
        Yields:
            Streaming response chunks.
        """
        # Push the user's new message.
        await self.push_coding_assistant_message(user_id, coding_exercise_id, content, role="user")

        # Retrieve the exercise record to get the problem description.
        exercise = await self.repository.first(where_=[Exercises.id == coding_exercise_id])
        problem_description = exercise.description if exercise and hasattr(exercise, "description") else "No description provided."

        # Retrieve conversation history.
        messages = await self.get_coding_assistant_conversation_messages(user_id, coding_exercise_id)
        # Keep only the last HISTORY_LENGTH messages.
        history = messages[-history_length:] if len(messages) > history_length else messages

        # Build the messages payload for the LLM.
        llm_messages = []
        # System prompt with educational guardrails and contextual information.
        system_prompt = (
            "You are a coding assistant designed for educational purposes. "
            "Your role is to help learners understand coding concepts and solve problems safely. "
            "Do not provide instructions for harmful or unsafe actions. "
            "Ensure your explanations are clear, accurate, and supportive. "
            "Problem description: {problem_description}. "
            "User's solution attempt: {user_solution}."
        ).format(problem_description=problem_description, user_solution=user_solution)
        llm_messages.append({"role": "system", "content": system_prompt})
        # Append the conversation history.
        for msg in history:
            llm_messages.append({"role": msg.role, "content": msg.content})
        # Optionally, add the current user message if it isn't already in history.
        if not history or history[-1].role != "user" or history[-1].content != content:
            llm_messages.append({"role": "user", "content": content})

        # Invoke the LLM via the Chat Completions API in streaming mode.
        response = await self.llm_client.chat.completions.create(
            model="gemini-2.0-flash",
            messages=llm_messages,
            stream=True,
        )

        assistant_reply = ""
        # Stream response chunks to the caller.
        async for chunk in response:
            # Extract the content delta (structure similar to OpenAI delta responses).
            delta = chunk.choices[0].delta
            content_chunk = delta.content

            if content_chunk is not None:
                assistant_reply += content_chunk
                yield content_chunk

        # Persist the assistant's full reply after streaming completes.
        await self.push_coding_assistant_message(user_id, coding_exercise_id, assistant_reply, role="assistant")

