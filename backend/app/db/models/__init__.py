"""Model registry.

Every mapped class must be imported here: `app.db.base` imports this package for
its side effects, and Alembic autogenerate only sees tables that are registered
on `Base.metadata` by import time.
"""

from app.db.models.chunk import Chunk
from app.db.models.citation import Citation
from app.db.models.conversation import Conversation
from app.db.models.document import Document, DocumentRelation
from app.db.models.enums import (
    CitationVerificationStatus,
    Court,
    DocumentStatus,
    DocumentType,
    Jurisdiction,
    LegalArea,
    MessageRole,
    RelationType,
    RetrievalSource,
    VerificationStatus,
)
from app.db.models.message import Message
from app.db.models.usage import UsageLog
from app.db.models.user import User

__all__ = [
    # Tables
    "Chunk",
    "Citation",
    "Conversation",
    "Document",
    "DocumentRelation",
    "Message",
    "UsageLog",
    "User",
    # Enums
    "CitationVerificationStatus",
    "Court",
    "DocumentStatus",
    "DocumentType",
    "Jurisdiction",
    "LegalArea",
    "MessageRole",
    "RelationType",
    "RetrievalSource",
    "VerificationStatus",
]
