"""Splits a document into clause-based chunks.

3GPP-style clause headings look like:
    9.1.3.4.2   Warning Message Delivery Procedure
    9.2.15      Void
"""

import re

from models import Chunk, DocStatus

CLAUSE_HEADING = re.compile(r"^(\d+(?:\.\d+)*)\s*[\t ]\s*(.+)$")


def split_into_clauses(document_text: str) -> list[tuple[str, str, str]]:
    lines = document_text.splitlines()
    clauses: list[tuple[str, str, list[str]]] = []
    current = None

    for line in lines:
        m = CLAUSE_HEADING.match(line.strip())
        if m:
            if current:
                clauses.append(current)
            current = (m.group(1), m.group(2), [])
        elif current:
            current[2].append(line)

    if current:
        clauses.append(current)

    return [(no, title, "\n".join(body).strip()) for no, title, body in clauses]


def build_chunks(
    document_text: str,
    doc_org: str,
    doc_code: str,
    version: str,
    source_url: str | None = None,
) -> list[Chunk]:
    chunks = []
    for clause_no, clause_title, body in split_into_clauses(document_text):
        is_void = clause_title.strip().lower().startswith("void") or body.strip().lower() == "void"
        chunks.append(
            Chunk(
                text="" if is_void else body,
                doc_org=doc_org,
                doc_code=doc_code,
                version=version,
                clause=clause_no,
                clause_title=clause_title,
                status=DocStatus.VOID if is_void else DocStatus.INDEXED,
                source_url=source_url,
            )
        )
    return chunks
