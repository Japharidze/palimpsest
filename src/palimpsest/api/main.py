from contextlib import asynccontextmanager

from fastapi import FastAPI
from psycopg_pool import ConnectionPool

from palimpsest.agent.graph import build_graph
from palimpsest.api.routes import router
from palimpsest.config import settings
from palimpsest.embedding import OllamaEmbedder
from palimpsest.llm import build_llm


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.shared_objects = {}

    pool = ConnectionPool(settings.db_url, min_size=2, max_size=10)
    embedder = OllamaEmbedder(settings.embedding_model)

    app.state.pool = pool
    app.state.embedder = embedder

    agent_model = build_llm(settings.agent_provider, settings.agent_model, settings.anthropic_api_key)
    app.state.agent = build_graph(pool, embedder, agent_model)

    yield

    pool.close()

app = FastAPI(lifespan=lifespan)

app.include_router(router)
