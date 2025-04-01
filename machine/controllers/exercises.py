from uuid import UUID

from sqlalchemy import select
from core.controller import BaseController
from core.exceptions.base import NotFoundException
from machine.models import Exercises
from machine.models.coding_assistant import CodingConversation, Conversation, Message
from machine.repositories import ExercisesRepository
from core.db import Transactional


class ExercisesController(BaseController[Exercises]):
    def __init__(self, exercises_repository: ExercisesRepository):
        super().__init__(model_class=Exercises, repository=exercises_repository)
        self.exercises_repository = exercises_repository

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
        stmt = select(Message).where(Message.conversation_id == conversation.id)
        result = await session.execute(stmt)
        messages = result.scalars().all()

        return messages

    @Transactional()
    async def push_coding_assistant_message(
        self, user_id: UUID, coding_exercise_id: UUID, content: str, role: str = "user"
    ):
        """
        Push a new message into the coding assistant conversation.
        
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
