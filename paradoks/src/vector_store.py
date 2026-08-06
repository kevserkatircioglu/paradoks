"""Embeds chunks and writes them to the vector DB.

TODO: connect to Chroma / Qdrant / etc. Person B's retrieval code will
call embed() and upsert_chunks() with this same signature.
"""

from models import Chunk, DocStatus


class VectorStore:
    def __init__(self, collection_name: str = "telecom_standards"):
        self.collection_name = collection_name
        # TODO: init real client, e.g.
        # self.client = chromadb.PersistentClient(path="./chroma_db")
        # self.collection = self.client.get_or_create_collection(collection_name)

    def embed(self, text: str) -> list[float]:
        raise NotImplementedError

    def upsert_chunks(self, chunks: list[Chunk]) -> int:
        written = 0
        for chunk in chunks:
            if chunk.status == DocStatus.VOID:
                continue
            chunk.embedding = self.embed(chunk.text)
            # TODO: self.collection.upsert(...)
            written += 1
        return written
