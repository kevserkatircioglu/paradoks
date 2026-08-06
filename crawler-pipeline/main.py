"""Usage: python main.py --seed data/seeds/23041-k00.docx"""

import argparse
import sys
import os
import re

sys.path.insert(0, "src")

from crawler import Crawler
from vector_store import VectorStore
from reference_parser import parse_references_section
from chunker import build_chunks

def read_local_docx(file_path: str) -> str:
    """Reads a local .docx file and extracts its text."""
    import docx
    doc = docx.Document(file_path)
    return "\n".join(p.text for p in doc.paragraphs)

def extract_references_text(full_text: str) -> str:
    """Extracts only the 'References' section from the text (skipping the table of contents)."""
    match = re.search(r"\[1\]\s+", full_text)
    if not match:
        return full_text
        
    start_idx = match.start()
    
    end_idx = full_text.find("1.2\tAbbreviations", start_idx)
    if end_idx == -1:
        end_idx = full_text.find("1.2 Abbreviations", start_idx)
        
    if end_idx == -1:
        return full_text[start_idx:]
        
    return full_text[start_idx:end_idx]

def main():
    parser = argparse.ArgumentParser(description="Runs the data pipeline from a seed document")
    parser.add_argument("--seed", required=True, help="Path to seed document (docx)")
    args = parser.parse_args()

    if not os.path.exists(args.seed):
        print(f"Error: Seed file '{args.seed}' not found!")
        sys.exit(1)

    print(f"1. Reading seed document: {args.seed}")
    seed_text = read_local_docx(args.seed)
    
    print("2. Extracting 'References' section...")
    ref_section_text = extract_references_text(seed_text)
    
    print("3. Parsing references...")
    seed_refs = parse_references_section(ref_section_text)
    print(f"   Found {len(seed_refs)} references in the seed document.")

    print("4. Starting Crawler, this may take a while...")
    crawler = Crawler()
    crawler.seed(seed_refs)
    
    results = crawler.run()
    print(f"   Crawler finished. Processed a total of {len(results)} references.")

    print("5. Chunking downloaded texts and writing to Vector Database...")
    store = VectorStore()
    total_chunks_written = 0
    total_documents = len(crawler.documents)
    
    # Get all keys (reference codes) into a list
    for key in list(crawler.documents.keys()):
        org, code = key
        
        # Pop the text from RAM to free up memory instantly (Garbage collection)
        text = crawler.documents.pop(key)
        
        chunks = build_chunks(
            document_text=text,
            doc_org=org,
            doc_code=code,
            version="Latest", 
            source_url=None
        )
        
        # Write chunks permanently to the database
        written = store.upsert_chunks(chunks)
        total_chunks_written += written

    print(f"\nProcess completed! Vector database created successfully.")
    print(f"Total documents read/downloaded: {total_documents}")
    print(f"Total chunks written to database: {total_chunks_written}")

if __name__ == "__main__":
    main()