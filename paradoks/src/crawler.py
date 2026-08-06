"""Queue + visited-set crawler. No depth limit — visited_codes prevents
infinite loops, so the graph naturally stops once the document universe
is exhausted.
"""

from collections import deque

from models import DocStatus, Reference
from reference_parser import parse_references_section
from resolver import resolve


class Crawler:
    def __init__(self):
        self.queue: deque[Reference] = deque()
        self.visited_codes: set[tuple[str, str]] = set()
        self.results: list = []

    def seed(self, seed_references: list[Reference]) -> None:
        for ref in seed_references:
            self.queue.append(ref)

    def run(self) -> list:
        while self.queue:
            ref = self.queue.popleft()
            key = (ref.org, ref.code)
            if key in self.visited_codes:
                continue
            self.visited_codes.add(key)

            resolved = resolve(ref)
            self.results.append(resolved)

            if resolved.status in (DocStatus.BLOCKED, DocStatus.UNRESOLVED):
                continue

            # TODO: download resolved.source_url, extract text, parse its
            # References section, push new refs onto the queue
            # doc_text = download_and_extract(resolved.source_url)
            # for new_ref in parse_references_section(doc_text):
            #     if (new_ref.org, new_ref.code) not in self.visited_codes:
            #         self.queue.append(new_ref)

        return self.results
