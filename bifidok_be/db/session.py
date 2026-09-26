"""
Database session management for Enterprise AI Sales Intelligence Platform.
Handles PostgreSQL connection with graceful SQLite fallback and session generator.
"""
import logging
import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .schema import Base

logger = logging.getLogger(__name__)

DEFAULT_SQLITE_URL = "sqlite:///./sales_intelligence.db"


def create_resilient_engine():
    """
    Initializes a SQLAlchemy engine using DATABASE_URL if available and reachable.
    Configured for Neon serverless PostgreSQL (pool_pre_ping, pool_recycle, 15s cold-start timeout).
    In strict production mode, fails fast instead of falling back to ephemeral SQLite.
    """
    db_url = os.getenv("DATABASE_URL")
    strict_prod = os.getenv("STRICT_PRODUCTION", "").lower() in ("true", "1") or os.getenv("ENVIRONMENT") == "production"

    if db_url:
        # Normalize legacy Heroku/AWS postgres:// scheme
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)

        try:
            connect_args = {}
            engine_kwargs = {}
            if "postgres" in db_url:
                connect_args["connect_timeout"] = 15
                if "sslmode" not in db_url:
                    connect_args["sslmode"] = "require"
                engine_kwargs["pool_pre_ping"] = True
                engine_kwargs["pool_recycle"] = 300
            elif "sqlite" in db_url:
                connect_args["check_same_thread"] = False

            test_engine = create_engine(db_url, connect_args=connect_args, **engine_kwargs)
            # Verify connectivity
            with test_engine.connect() as conn:
                pass
            logger.info("Successfully connected to primary DATABASE_URL")
            return test_engine
        except Exception as exc:
            if strict_prod:
                logger.error("CRITICAL: Failed to connect to production DATABASE_URL: %s", exc)
                raise RuntimeError(
                    f"Production database connection failed: {exc}. Refusing ephemeral SQLite fallback in strict production."
                ) from exc
            logger.warning(
                "Configured DATABASE_URL is unreachable or invalid (%s). "
                "Defaulting gracefully to %s",
                exc,
                DEFAULT_SQLITE_URL,
            )
    elif strict_prod:
        raise RuntimeError("STRICT_PRODUCTION is enabled but DATABASE_URL is not configured.")

    return create_engine(
        DEFAULT_SQLITE_URL,
        connect_args={"check_same_thread": False},
    )


engine = create_resilient_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(target_engine=None):
    """
    Creates all database tables defined in the schema.
    """
    bind_engine = target_engine or engine
    Base.metadata.create_all(bind=bind_engine)


# Call Base.metadata.create_all(bind=engine) on startup
init_db(engine)


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency generator for FastAPI routes or script contexts.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
