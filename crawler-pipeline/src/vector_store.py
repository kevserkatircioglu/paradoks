"""
Embeds text chunks into vector representations and writes them
to the Vector Database.

Uses ChromaDB with intfloat/multilingual-e5-small.
"""

import hashlib
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from models import Chunk, DocStatus


EMBEDDING_BATCH_SIZE = 8
UPSERT_BATCH_SIZE = 256


class VectorStore:
    def __init__(
        self,
        db_path: str | Path,
        collection_name: str = "telecom_standards",
    ):
        self.collection_name = collection_name

        self.db_path = Path(db_path)

        self.db_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        print(
            f"[VECTOR] DB yolu: "
            f"{self.db_path.resolve()}"
        )

        self.client = chromadb.PersistentClient(
            path=str(self.db_path)
        )

        self.collection = (
            self.client.get_or_create_collection(
                collection_name
            )
        )

        print(
            "[VECTOR] Embedding modeli y├╝kleniyor..."
        )

        self.model = SentenceTransformer(
            "intfloat/multilingual-e5-small"
        )

    def embed(
        self,
        text: str,
    ) -> list[float]:
        """
        Tek bir metni E5 passage embedding'ine ├ğevirir.
        """

        formatted_text = (
            f"passage: {text}"
        )

        return self.model.encode(
            formatted_text
        ).tolist()

    def _build_chunk_id(
        self,
        chunk: Chunk,
    ) -> str:
        """
        Ayn─▒ chunk i├ğin her ├ğal─▒┼şt─▒rmada ayn─▒ ID ├╝retir.
        """

        identity = "|".join(
            [
                chunk.doc_org or "",
                chunk.doc_code or "",
                chunk.version or "",
                chunk.clause or "",
                chunk.text or "",
            ]
        )

        digest = hashlib.sha256(
            identity.encode("utf-8")
        ).hexdigest()

        return f"chunk_{digest}"

    def upsert_chunks(
        self,
        chunks: list[Chunk],
    ) -> int:
        """
        Chunk'lar─▒ batch olarak embed eder ve ChromaDB'ye yazar.

        VOID ve bo┼ş chunk'lar indexlenmez.
        """

        valid_chunks: list[Chunk] = []

        for chunk in chunks:
            if chunk.status == DocStatus.VOID:
                continue

            clean_text = (
                chunk.text or ""
            ).strip()

            if not clean_text:
                continue

            valid_chunks.append(
                chunk
            )

        if not valid_chunks:
            return 0

        print(
            f"[VECTOR] Ge├ğerli chunk: "
            f"{len(valid_chunks)}"
        )

        # ---------------------------------------------
        # 1. Embeddingleri batch olu┼ştur
        # ---------------------------------------------
        formatted_texts = [
            f"passage: {chunk.text.strip()}"
            for chunk in valid_chunks
        ]

        embeddings = self.model.encode(
            formatted_texts,
            batch_size=EMBEDDING_BATCH_SIZE,
            show_progress_bar=True,
        ).tolist()

        # ---------------------------------------------
        # 2. Chroma batch upsert
        # ---------------------------------------------
        written = 0

        for start in tqdm(
            range(
                0,
                len(valid_chunks),
                UPSERT_BATCH_SIZE,
            ),
            desc="Chroma batch upsert",
            unit="batch",
        ):
            end = (
                start + UPSERT_BATCH_SIZE
            )

            batch_chunks = valid_chunks[
                start:end
            ]

            batch_embeddings = embeddings[
                start:end
            ]

            ids = []
            documents = []
            metadatas = []

            for chunk in batch_chunks:
                clean_text = (
                    chunk.text or ""
                ).strip()

                ids.append(
                    self._build_chunk_id(
                        chunk
                    )
                )

                documents.append(
                    clean_text
                )

                status = (
                    chunk.status.value
                    if hasattr(
                        chunk.status,
                        "value",
                    )
                    else str(chunk.status)
                )

                metadatas.append(
                    {
                        "org": (
                            chunk.doc_org
                            or ""
                        ),
                        "code": (
                            chunk.doc_code
                            or ""
                        ),
                        "version": (
                            chunk.version
                            or "Latest"
                        ),
                        "clause": (
                            chunk.clause
                            or ""
                        ),
                        "clause_title": (
                            chunk.clause_title
                            or ""
                        ),
                        "status": status,
                        "source_url": (
                            chunk.source_url
                            or ""
                        ),
                    }
                )

            self.collection.upsert(
                ids=ids,
                embeddings=batch_embeddings,
                documents=documents,
                metadatas=metadatas,
            )

            written += len(
                batch_chunks
            )

        return written
