"""Usage: python main.py --seed data/seeds/23041-k00.docx"""

import argparse
import sys

sys.path.insert(0, "src")

from crawler import Crawler
from vector_store import VectorStore


def main():
    parser = argparse.ArgumentParser(description="Runs the data pipeline from a seed document")
    parser.add_argument("--seed", required=True, help="Path to seed document (docx)")
    args = parser.parse_args()

    # TODO: extract text from seed doc, isolate References section,
    # pass to parse_references_section()
    print(f"TODO: process {args.seed} — extract-text integration missing")

    seed_refs = []

    crawler = Crawler()
    crawler.seed(seed_refs)
    results = crawler.run()
    print(f"{len(results)} references resolved.")

    store = VectorStore()
    # TODO: for each downloaded doc, build_chunks() then store.upsert_chunks()


if __name__ == "__main__":
    main()
