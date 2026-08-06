"""
Splits a large standard document into smaller, clause-based chunks (e.g., sections)[cite: 4].

3GPP-style (and generally most telecom standard) clause headings look like:
    9.1.3.4.2   Warning Message Delivery Procedure
    9.2.15      Void
"""

import re

from models import Chunk, DocStatus

# Regex to match clause numbers and their titles. 
# Matches formats like "1", "1.2", "9.1.3.4.2" followed by whitespace and the title text[cite: 4].
CLAUSE_HEADING = re.compile(r"^(\d+(?:\.\d+)*)\s*[\t ]\s*(.+)$")


def split_into_clauses(document_text: str) -> list[tuple[str, str, str]]:
    """
    Reads the document text line by line and groups the content under its respective clause heading[cite: 4].
    Returns a list of tuples containing: (clause_number, clause_title, body_text)[cite: 4].
    """
    lines = document_text.splitlines()
    clauses: list[tuple[str, str, list[str]]] = []
    current = None

    for line in lines:
        m = CLAUSE_HEADING.match(line.strip())
        if m:
            # If we find a new heading, save the previous clause (if any) before starting a new one[cite: 4].
            if current:
                clauses.append(current)
            # Initialize a new clause tracking structure: (number, title, list_of_body_lines)[cite: 4]
            current = (m.group(1), m.group(2), [])
        elif current:
            # If it's a regular text line, append it to the body of the current clause[cite: 4]
            current[2].append(line)

    # Don't forget to append the very last clause after the loop finishes[cite: 4]
    if current:
        clauses.append(current)

    # Join the list of body lines into a single string for each clause[cite: 4]
    return [(no, title, "\n".join(body).strip()) for no, title, body in clauses]


def build_chunks(
    document_text: str,
    doc_org: str,
    doc_code: str,
    version: str,
    source_url: str | None = None,
) -> list[Chunk]:
    """
    Takes the raw document text and its metadata, splits it into clauses, 
    and packages each clause into a structured Chunk object ready for the Vector Database[cite: 4].
    """
    chunks = []
    for clause_no, clause_title, body in split_into_clauses(document_text):
        # Identify deprecated/cancelled clauses. They usually contain "Void" in the title or body[cite: 4].
        is_void = clause_title.strip().lower().startswith("void") or body.strip().lower() == "void"
        
        chunks.append(
            Chunk(
                # If it's a void clause, don't store the text to save database space[cite: 4]
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