"""
Queue + visited-set crawler. No depth limit -- visited_codes prevents
infinite loops, so the graph naturally stops once the document universe
is exhausted[cite: 3].
"""

from collections import deque

from models import DocStatus, Reference
from reference_parser import parse_references_section
from resolver import resolve
from fetcher import fetch_and_read


class Crawler:
    def __init__(self):
        # A double-ended queue (FIFO) to manage the list of references waiting to be processed[cite: 3].
        self.queue: deque[Reference] = deque()
        
        # A set to keep track of processed documents (org, code) to avoid infinite loops and redundant fetching[cite: 3].
        self.visited_codes: set[tuple[str, str]] = set()
        
        # Stores the metadata (ResolvedSource) for every reference encountered[cite: 3].
        self.results: list = []          
        
        # Maps (org, code) to the fully extracted text, which will later be passed to chunker.py[cite: 3].
        self.documents: dict = {}        

    def seed(self, seed_references: list[Reference]) -> None:
        """
        Initializes the crawler with a starting set of references (the root nodes of our document graph)[cite: 3].
        """
        for ref in seed_references:
            self.queue.append(ref)

    def run(self) -> list:
        """
        The main execution loop of the crawler. Processes the queue recursively until it is empty[cite: 3].
        Returns the list of all resolved sources (metadata)[cite: 3].
        """
        while self.queue:
            
            # 1. Take the next reference from the front of the queue (FIFO)[cite: 3]
            ref = self.queue.popleft()
            print(f"İşleniyor: {ref.org} {ref.code}")
            key = (ref.org, ref.code)
            
            # 2. Check if we have already processed this document to prevent infinite loops[cite: 3]
            if key in self.visited_codes:
                continue
            self.visited_codes.add(key)

            # 3. Resolve the reference into a tangible URL using our deterministic/search logic[cite: 3]
            resolved = resolve(ref)
            self.results.append(resolved)

            # 4. If the document is blocked (e.g., paywall) or cannot be resolved, skip downloading[cite: 3]
            if resolved.status in (DocStatus.BLOCKED, DocStatus.UNRESOLVED):
                continue
            if not resolved.source_url:
                continue

            # 5. Fetch and extract the text from the actual document file[cite: 3]
            text = fetch_and_read(resolved.source_url)
            if not text:
                continue

            # 6. Store the extracted text in memory for the chunking process later[cite: 3]
            self.documents[key] = text

            # 7. Parse the newly downloaded text to find *new* references inside it[cite: 3].
            # Any undiscovered references are appended to the queue to continue the recursive crawl[cite: 3].
            for new_ref in parse_references_section(text):
                if (new_ref.org, new_ref.code) not in self.visited_codes:
                    self.queue.append(new_ref)

        return self.results