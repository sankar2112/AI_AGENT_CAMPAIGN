import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import Base, engine
from .routers import analytics, campaigns, customers, stream
from .services import engine as campaign_engine
from .services.bedrock import nova_client

logging.basicConfig(level=logging.INFO)

settings = get_settings()
app = FastAPI(title="BFSI AI Agent Campaign Platform", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(customers.router)
app.include_router(campaigns.router)
app.include_router(campaigns.runs_router)
app.include_router(analytics.router)
app.include_router(stream.router)


@app.on_event("startup")
async def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    campaign_engine.bind_loop(asyncio.get_running_loop())


@app.get("/api/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "llm_provider": nova_client.provider,
        "model_id": settings.bedrock_model_id,
        "region": settings.aws_region,
    }
