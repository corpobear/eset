from fastapi import FastAPI
from utils.ecls import ecls_manager
from contextlib import asynccontextmanager

    
    
@asynccontextmanager
async def lifespan(app):
    ecls_manager.initialize()
    try:
        yield
    finally:
        ecls_manager.shutdown()


def create_app():
    app = FastAPI(lifespan=lifespan)
    from endpoints.scan import router
    app.include_router(router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)	