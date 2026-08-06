"""Parses reference lines into {org, code, title}.

Examples:
    [2]  3GPP TS 22.003: "Circuit Teleservices..."
    [12] ITU-T Recommendation X.210: "..."
    [25] GSMA AD.26: "Coding of Cell Broadcast Functions"
    [32] ETSI TS 102 900: "..."
    [33] IETF RFC 4960: "Stream Control Transmission Protocol"
    [47] ATIS-0700041: "WEA 3.0: Device-Based Geo-Fencing"

Note: source docx files sometimes use non-breaking space (\\xa0) instead
of a normal space between tokens. normalize_whitespace() handles that.
"""

import re
from typing import Optional

from models import Reference

PATTERNS: dict[str, re.Pattern] = {
    "3GPP":  re.compile(r"3GPP\s+(TS|TR)\s*(\d{2}\.\d{3})(?:\s+Version\s+[\d.]+)?", re.IGNORECASE),
    "ETSI":  re.compile(r"ETSI\s+(TS|EN|TR)\s*(\d{3}\s?\d{3})", re.IGNORECASE),
    "IETF":  re.compile(r"(?:IETF\s+)?RFC\s*(\d{3,5})", re.IGNORECASE),
    "ITU-T": re.compile(r"ITU-T\s+Rec(?:ommendation)?\.?\s*([A-Z]\.\d+)", re.IGNORECASE),
    "ATIS":  re.compile(r"ATIS-(\d{7}(?:\.v\d{3})?)", re.IGNORECASE),
    "GSMA":  re.compile(r"\bGSMA\s+([A-Z]{2}\.\d{1,3})\b"),
}

REF_LINE = re.compile(r"^\[(\d+)\]\s*(.+)$")
TITLE = re.compile(r'[""\"]([^""\"]+)[""\"]')


def normalize_whitespace(text: str) -> str:
    return text.replace("\xa0", " ").replace("\u200b", "")


def _extract_code(org: str, match: re.Match) -> str:
    groups = match.groups()
    if org in ("3GPP", "ETSI"):
        return f"{groups[0].upper()} {groups[1]}"
    if org in ("IETF", "ITU-T", "ATIS", "GSMA"):
        return groups[0]
    return match.group(0)


def parse_reference_line(line: str) -> Optional[Reference]:
    line = normalize_whitespace(line).strip()
    m = REF_LINE.match(line)
    if not m:
        return None

    ref_number = int(m.group(1))
    body = m.group(2).strip()

    if body.lower().startswith("void"):
        return None  # caller marks this as DocStatus.VOID

    for org, pattern in PATTERNS.items():
        match = pattern.search(body)
        if not match:
            continue
        code = _extract_code(org, match)
        title_match = TITLE.search(body)
        title = title_match.group(1) if title_match else ""
        return Reference(raw_text=line, org=org, code=code, title=title, ref_number=ref_number)

    # unknown org format -> add a new pattern to PATTERNS above
    return None


def parse_references_section(text: str) -> list[Reference]:
    refs = []
    for raw_line in text.splitlines():
        ref = parse_reference_line(raw_line)
        if ref:
            refs.append(ref)
    return refs
