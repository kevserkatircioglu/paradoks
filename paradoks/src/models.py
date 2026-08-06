"""Shared schema between Person A (crawler) and Person B (RAG). Don't change field names/types without syncing."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DocStatus(str, Enum):
    PENDING = "pending"
    INDEXED = "indexed"
    BLOCKED = "blocked"        # paywalled / inaccessible, link kept only
    VOID = "void"               # marked "Void" in source doc
    UNRESOLVED = "unresolved"   # resolver chain found nothing


@dataclass
class Reference:
    raw_text: str
    org: str            # "3GPP", "IETF", "ATIS", "ETSI", "ITU-T", "GSMA"
    code: str            # "TS 23.041", "RFC 4960", "AD.26"
    title: str
    ref_number: Optional[int] = None


@dataclass
class ResolvedSource:
    reference: Reference
    status: DocStatus
    source_url: Optional[str] = None
    version: Optional[str] = None
    local_path: Optional[str] = None


@dataclass
class Chunk:
    text: str
    doc_org: str
    doc_code: str
    version: str
    clause: str
    clause_title: str
    status: DocStatus
    source_url: Optional[str] = None
    embedding: Optional[list[float]] = field(default=None, repr=False)

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "doc_org": self.doc_org,
            "doc_code": self.doc_code,
            "version": self.version,
            "clause": self.clause,
            "clause_title": self.clause_title,
            "status": self.status.value if isinstance(self.status, DocStatus) else self.status,
            "source_url": self.source_url,
        }
