from contextlib import asynccontextmanager, contextmanager
import functools
import inspect

from collections.abc import AsyncGenerator
from typing import Callable, Generator
from core.settings import settings
from core.utils import singleton
from neo4j import AsyncSession as Neo4jAsyncSession, Session as Neo4jSession, AsyncGraphDatabase, GraphDatabase


@singleton
class Neo4jDBSessionProvider:
    """
    This provider handles database session management.
    This class is used to implement Dependency Injection/Inversion of Control.
    """

    def __init__(self):
        self._async_neo4j_driver = AsyncGraphDatabase.driver(
                    settings.NEO4J_URI,
                    auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
                )

        self._neo4j_driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
            )

    @asynccontextmanager
    async def get_neo4j_async_session(self) -> AsyncGenerator[Neo4jAsyncSession, None]:
        """Returns an async session for the Neo4j database."""
        async with self._async_neo4j_driver.session() as neo4j_db_session:
            yield neo4j_db_session

    @contextmanager
    def get_neo4j_session(self) -> Generator:
        """Returns a synchronous session for the Neo4j database."""
        with self._neo4j_driver.session() as session:
            yield session

    def inject_neo4j_async_session(self, argname: str):
        """Inject Neo4j Async Session to functions/methods."""
        def _decorator(callback: Callable):
            signature = inspect.signature(callback)

            if argname not in signature.parameters:
                raise ValueError(f"Callable object must support {argname} parameter.")

            @functools.wraps(callback)
            async def wrapper(*args, **kwargs):
                # Use provided neo4j_session if available; otherwise, create one
                if argname in kwargs:
                    # Use the existing session
                    return await callback(*args, **kwargs)
                else:
                    # Create a new session and inject it
                    async with self.get_neo4j_async_session() as neo4j_session:
                        kwargs[argname] = neo4j_session
                        return await callback(*args, **kwargs)

            return wrapper

        return _decorator

    def inject_neo4j_session(self, argname: str):
        """Inject Neo4j Async Session to functions/methods."""
        def _decorator(callback: Callable):
            signature = inspect.signature(callback)

            if argname not in signature.parameters:
                raise ValueError(f"Callable object must support {argname} parameter.")

            @functools.wraps(callback)
            def wrapper(*args, **kwargs):
                # Use provided neo4j_session if available; otherwise, create one
                if argname in kwargs:
                    # Use the existing session
                    return callback(*args, **kwargs)
                else:
                    # Create a new session and inject it
                    with self.get_neo4j_session() as neo4j_session:
                        kwargs[argname] = neo4j_session
                        return callback(*args, **kwargs)

            return wrapper

        return _decorator
