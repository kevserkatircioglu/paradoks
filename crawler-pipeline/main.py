"""
Usage:

python main.py \
    --seed data/seeds/23041-k00.docx \
    --output-db backend/vector_db_v2

Full rebuild i├ğin:

python main.py \
    --seed data/seeds/23041-k00.docx \
    --output-db backend/vector_db_v2 \
    --reset
"""

import argparse
import os
import re
import shutil
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"

sys.path.insert(
    0,
    str(SRC_DIR),
)


from crawler import Crawler
from vector_store import VectorStore
from reference_parser import (
    parse_references_section,
)
from chunker import build_chunks


def read_local_docx(
    file_path: str | Path,
) -> str:
    """
    Local DOCX dosyas─▒ndaki paragraph metinlerini okur.
    """

    import docx

    doc = docx.Document(
        str(file_path)
    )

    return "\n".join(
        paragraph.text
        for paragraph in doc.paragraphs
    )


def extract_references_text(
    full_text: str,
) -> str:
    """
    3GPP seed dok├╝man─▒ndaki References b├Âl├╝m├╝n├╝ ay─▒r─▒r.
    """

    match = re.search(
        r"\[1\]\s+",
        full_text,
    )

    if not match:
        return full_text

    start_idx = match.start()

    end_idx = full_text.find(
        "1.2\tAbbreviations",
        start_idx,
    )

    if end_idx == -1:
        end_idx = full_text.find(
            "1.2 Abbreviations",
            start_idx,
        )

    if end_idx == -1:
        return full_text[
            start_idx:
        ]

    return full_text[
        start_idx:end_idx
    ]


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Recursive telecom standard crawler "
            "and Vector DB builder"
        )
    )

    parser.add_argument(
        "--seed",
        required=True,
        help="Seed DOCX path",
    )

    parser.add_argument(
        "--output-db",
        default="backend/vector_db_v2",
        help=(
            "Yeni Chroma DB yolu. "
            "Default: backend/vector_db_v2"
        ),
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help=(
            "Output DB varsa rebuild ├Âncesi "
            "tamamen sil."
        ),
    )

    args = parser.parse_args()

    # -----------------------------------------------------
    # PATHLER
    # -----------------------------------------------------
    seed_path = Path(
        args.seed
    )

    if not seed_path.is_absolute():
        seed_path = (
            BASE_DIR / seed_path
        )

    output_db = Path(
        args.output_db
    )

    if not output_db.is_absolute():
        output_db = (
            BASE_DIR / output_db
        )

    # -----------------------------------------------------
    # SEED KONTROL├£
    # -----------------------------------------------------
    if not seed_path.exists():
        print(
            f"ERROR: Seed bulunamad─▒: "
            f"{seed_path}"
        )
        sys.exit(1)

    print("=" * 70)
    print("PARADOKS DATA PIPELINE")
    print("=" * 70)

    print(
        "Seed:",
        seed_path.resolve(),
    )

    print(
        "Yeni DB:",
        output_db.resolve(),
    )

    # -----------------------------------------------------
    # DB G├£VENL─░─Ş─░
    # -----------------------------------------------------
    if output_db.exists():
        if args.reset:
            print()
            print(
                "[DB] Eski test/rebuild DB "
                "siliniyor..."
            )

            shutil.rmtree(
                output_db
            )

        else:
            print()
            print(
                "ERROR: Output DB zaten var."
            )

            print(
                "S─▒f─▒rdan olu┼şturmak i├ğin "
                "--reset kullan."
            )

            sys.exit(1)

    # -----------------------------------------------------
    # 1. SEED
    # -----------------------------------------------------
    print()
    print(
        "1. Seed document okunuyor..."
    )

    seed_text = read_local_docx(
        seed_path
    )

    # -----------------------------------------------------
    # 2. REFERENCES
    # -----------------------------------------------------
    print(
        "2. References b├Âl├╝m├╝ ├ğ─▒kar─▒l─▒yor..."
    )

    ref_section_text = (
        extract_references_text(
            seed_text
        )
    )

    # -----------------------------------------------------
    # 3. PARSE
    # -----------------------------------------------------
    print(
        "3. Seed references parse ediliyor..."
    )

    seed_refs = (
        parse_references_section(
            ref_section_text
        )
    )

    print(
        f"   Seed reference say─▒s─▒: "
        f"{len(seed_refs)}"
    )

    # -----------------------------------------------------
    # 4. RECURSIVE CRAWLER
    # -----------------------------------------------------
    print()
    print(
        "4. Recursive crawler ba┼şl─▒yor..."
    )

    crawler = Crawler()

    crawler.seed(
        seed_refs
    )

    results = crawler.run()

    print()
    print(
        "Crawler tamamland─▒."
    )

    print(
        "Toplam i┼şlenen reference:",
        len(results),
    )

    print(
        "Ba┼şar─▒yla indirilen document:",
        len(crawler.documents),
    )

    # -----------------------------------------------------
    # RESOLVED METADATA MAP
    #
    # (org, code)
    #   Ôåô
    # version
    # source_url
    # -----------------------------------------------------
    resolved_map = {}

    for resolved in results:
        reference = (
            resolved.reference
        )

        key = (
            reference.org,
            reference.code,
        )

        resolved_map[key] = (
            resolved
        )

    # -----------------------------------------------------
    # 5. VECTOR STORE
    # -----------------------------------------------------
    print()
    print(
        "5. Yeni Vector DB olu┼şturuluyor..."
    )

    store = VectorStore(
        db_path=output_db,
        collection_name="telecom_standards",
    )

    total_chunks_written = 0

    total_documents = len(
        crawler.documents
    )

    document_counter = 0

    # -----------------------------------------------------
    # 6. CHUNK + EMBED + UPSERT
    # -----------------------------------------------------
    for key in list(
        crawler.documents.keys()
    ):
        document_counter += 1

        org, code = key

        print()
        print("=" * 70)

        print(
            f"[DOC] "
            f"{document_counter}/"
            f"{total_documents}"
        )

        print(
            f"[DOC] {org} {code}"
        )

        text = crawler.documents.pop(
            key
        )

        resolved = resolved_map.get(
            key
        )

        version = "Latest"
        source_url = None

        if resolved is not None:
            if resolved.version:
                version = (
                    resolved.version
                )

            if resolved.source_url:
                source_url = (
                    resolved.source_url
                )

        chunks = build_chunks(
            document_text=text,
            doc_org=org,
            doc_code=code,
            version=version,
            source_url=source_url,
        )

        print(
            "[DOC] Olu┼şturulan chunk:",
            len(chunks),
        )

        written = store.upsert_chunks(
            chunks
        )

        total_chunks_written += (
            written
        )

        print(
            "[DOC] DB'ye yaz─▒lan:",
            written,
        )

        print(
            "[TOTAL] ┼Şu ana kadar:",
            total_chunks_written,
        )

    # -----------------------------------------------------
    # SONU├ç
    # -----------------------------------------------------
    print()
    print("=" * 70)
    print("PIPELINE TAMAMLANDI")
    print("=" * 70)

    print(
        "Toplam document:",
        total_documents,
    )

    print(
        "Toplam yaz─▒lan chunk:",
        total_chunks_written,
    )

    print(
        "Vector DB:",
        output_db.resolve(),
    )

    print("=" * 70)


if __name__ == "__main__":
    main()
