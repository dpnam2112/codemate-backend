# EduMind (CodeMate) Project

EduMind (CodeMate) is a FastAPI-based application designed to manage educational content and user interactions. This project is structured to follow best practices in software development, ensuring maintainability, scalability, and testability. 

## Folder Description

- **backend/core**: Contains core functionalities and configurations such as database setup, custom exceptions, and settings.
  - **db.py**: Database connection and session management.
  - **exceptions.py**: Custom exception classes.
  - **fastapi/middlewares**: Middleware for SQLAlchemy session management.
  - **repository/enum.py**: Enumeration types used in repositories.
  - **response/api_response.py**: Standardized API response models.
  - **settings.py**: Application settings and configurations.

- **backend/machine**: Contains the main application logic, including APIs, controllers, models, providers, and repositories.
  - **api**: API endpoints organized by version.
    - **v1**: Version 1 of the API.
      - **courses.py**: Endpoints related to courses.
      - **dashboard.py**: Endpoints related to the dashboard.
      ...
  - **controllers**: Business logic for handling requests.
    - **courses.py**: Controller for course-related operations.
    ...
  - **models**: SQLAlchemy models representing database tables.
    - **courses.py**: Model for the courses table.
    - **student_courses.py**: Model for the student_courses table.
    ...
  - **providers**: Dependency injection providers.
    - **internal.py**: Provides instances of controllers and repositories.
  - **repositories**: Data access layer for interacting with the database.
    - **courses.py**: Repository for course-related operations.
    ...
  - **schemas**: Pydantic models for request and response validation.
    - **requests**: Request models.
      - **courses.py**: Request model for course-related operations.
      ...
    - **responses**: Response models.
      - **courses.py**: Response model for course-related operations.
      ...
  - **server.py**: FastAPI application setup and configuration.

- **backend/main.py**: Entry point for the application.

- **migrations**: Alembic migrations for database schema management.
  - **env.py**: Alembic environment configuration.
  - **versions**: Directory for migration scripts.

- **pyproject.toml**: Poetry configuration file.

## Prerequisites

- Python 3.12
- Poetry

## Installation

1. Clone the repository:
   ```sh
   git clone https://github.com/PhamThi1710/EduMind.git
   cd backend

## Running the Project (Make sure you have moved to the backend folder already)

This project uses [Poetry](https://python-poetry.org/) for dependency management. To run the project, follow these steps:

1. **Install Poetry**:
    ```sh
    curl -sSL https://install.python-poetry.org | python3 -
    ```

2. **Install Dependencies**:
    ```sh
    poetry install
    ```

3. **Run the Project**:
    ```sh
    poetry run python main.py
    ```
The application will be available at http://127.0.0.1:8080 / http://localhost:8080 
