from fastapi import FastAPI
from endpoints import router as base_router
from settings import env_settings

app = FastAPI(
    title="Document ingestion service",
    description="A simple FastAPI microservice template with Swagger documentation configuration",
    version="1.0.0",
    # Customize the URL paths for documentation endpoints:
    docs_url="/docs",      # Swagger UI will be available at /swagger
    redoc_url="/redoc",       # ReDoc documentation will be available at /redoc
    openapi_url="/openapi.json",  # The OpenAPI schema will be available at /openapi.json
    # Optional: customize Swagger UI parameters (e.g., disable model expansion)
    swagger_ui_parameters={"defaultModelsExpandDepth": -1}
)
app.include_router(base_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host=env_settings.host,
        port=env_settings.port,
        reload=env_settings.debug
    )

