"""
Fetches a document from a URL and extracts its text content[cite: 5].

Does NOT persist files to disk long-term -- downloads into memory
(or a temp file, cleaned up after), extracts text, returns the string[cite: 5].
Supports pdf, docx, and plain html pages[cite: 5].
"""

import io
import zipfile
import requests
from bs4 import BeautifulSoup

# Pretend to be a legitimate browser/crawler so websites don't block the request[cite: 5]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; standards-crawler/1.0)"}
TIMEOUT = 30


def fetch_and_read(url: str) -> str | None:
    """
    Main entry point. Takes a URL, downloads the payload, identifies the file type,
    and routes it to the appropriate text extraction function.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    except requests.RequestException:
        return None

    # Ensure the download was actually successful
    if resp.status_code != 200:
        return None

    content_type = resp.headers.get("Content-Type", "").lower()
    lower_url = url.lower()

    # Route to the correct parser based on file extension or HTTP Content-Type headers[cite: 5]
    if lower_url.endswith(".pdf") or "application/pdf" in content_type:
        return _read_pdf(resp.content)
    if lower_url.endswith(".docx") or "wordprocessingml" in content_type:
        return _read_docx(resp.content)
    if lower_url.endswith(".zip"):
        return _read_zip(resp.content)  # 3GPP publishes zipped docx files[cite: 5]
    
    # Fallback: if it's not a document, treat it as a standard HTML webpage[cite: 5]
    return _read_html(resp.text)


def _read_pdf(raw_bytes: bytes) -> str:
    """
    Loads raw PDF bytes directly into memory (BytesIO) and extracts text page by page.
    """
    import pdfplumber
    text_parts = []
    # io.BytesIO tricks pdfplumber into thinking it's reading a real file from the disk
    with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
        for page in pdf.pages:
            text_parts.append(page.extract_text() or "")
    return "\n".join(text_parts)


def _read_docx(raw_bytes: bytes) -> str:
    """
    Loads raw DOCX bytes into memory and extracts text from all paragraphs.
    """
    import docx
    doc = docx.Document(io.BytesIO(raw_bytes))
    return "\n".join(p.text for p in doc.paragraphs)


def _read_zip(raw_bytes: bytes) -> str:
    """
    Specifically designed for 3GPP archives. Opens the zip in memory, 
    finds the internal DOCX file, and extracts its text[cite: 5].
    """
    with zipfile.ZipFile(io.BytesIO(raw_bytes)) as z:
        # Find the first file inside the zip that ends with .docx[cite: 5]
        docx_names = [n for n in z.namelist() if n.lower().endswith(".docx")]
        if not docx_names:
            return ""
        # Open that inner file and pass it to our DOCX reader[cite: 5]
        with z.open(docx_names[0]) as f:
            return _read_docx(f.read())


def _read_html(html: str) -> str:
    """
    Parses plain HTML using BeautifulSoup and extracts human-readable text,
    stripping away all tags.
    """
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator="\n", strip=True)