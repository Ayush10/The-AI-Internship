import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import (
    Column, String, Integer, Text, DateTime, Boolean, ForeignKey, Index, create_engine,
    TypeDecorator, event,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.types import CHAR, TypeEngine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import json as _json

from config import DATABASE_URL

# --- Cross-DB UUID type ---
class UUID(TypeDecorator):
    """Platform-independent UUID type. Uses PostgreSQL UUID natively, CHAR(36) on SQLite."""
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect) -> TypeEngine:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value if isinstance(value, uuid.UUID) else uuid.UUID(value)
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            return uuid.UUID(str(value))
        return value


# --- Cross-DB JSON type ---
class JSONType(TypeDecorator):
    """Uses JSONB on PostgreSQL, TEXT with JSON serialization on SQLite."""
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect) -> TypeEngine:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB)
        return dialect.type_descriptor(Text)

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name != "postgresql":
            return _json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if dialect.name != "postgresql" and isinstance(value, str):
            return _json.loads(value)
        return value


Base = declarative_base()


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False, default="New Conversation")
    endpoint = Column(String(50), nullable=False)
    mode = Column(String(20), nullable=True)
    provider = Column(String(20), nullable=False)
    prompt_version = Column(Integer, nullable=True)
    course = Column(String(100), nullable=False, default="ai-engineering-bootcamp")
    assignment = Column(String(100), nullable=False, default="week1-fastapi-llm-api")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan",
                            order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_messages_conversation_id", "conversation_id"),
        Index("idx_messages_created_at", "conversation_id", "created_at"),
    )

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    meta = Column("metadata", JSONType(), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    conversation = relationship("Conversation", back_populates="messages")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("idx_users_fingerprint", "fingerprint"),
        Index("idx_users_email", "email"),
    )

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    fingerprint = Column(String(36), nullable=False, unique=True)
    message_count = Column(Integer, nullable=False, default=0)
    is_admin = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


# --- Engine setup ---
_DEFAULT_SQLITE = f"sqlite:///{Path(__file__).parent / 'app.db'}"
_db_url = DATABASE_URL or _DEFAULT_SQLITE

if _db_url.startswith("sqlite"):
    engine = create_engine(_db_url, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    engine = create_engine(_db_url, pool_pre_ping=True, pool_size=5)

SessionLocal = sessionmaker(bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
