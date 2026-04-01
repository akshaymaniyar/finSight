import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_tables

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="FinSight API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers import auth, sync, statements, transactions, analytics, chat, profile, categories, pdf  # noqa

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(profile.router, prefix="/api/profile", tags=["profile"])
app.include_router(categories.router, prefix="/api/categories", tags=["categories"])
app.include_router(sync.router, prefix="/api/sync", tags=["sync"])
app.include_router(statements.router, prefix="/api/statements", tags=["statements"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["transactions"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(pdf.router, prefix="/api/pdf", tags=["pdf"])


@app.on_event("startup")
def startup():
    logger.info("Creating database tables...")
    create_tables()
    logger.info("FinSight API ready")


@app.get("/")
def health_check():
    return {"status": "ok", "message": "FinSight API is running"}


@app.get("/api/health")
def api_health():
    return {"status": "ok"}
