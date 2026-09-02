from fastapi import FastAPI


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="Русь пролетарская",
        description="Интерактивная карта мест пролетарской истории и культуры.",
        version="0.1.0",
    )

    @application.get("/health", tags=["system"])
    async def health_check() -> dict[str, str]:
        """Confirm that the application is running."""
        return {"status": "ok"}

    return application

app = create_app()