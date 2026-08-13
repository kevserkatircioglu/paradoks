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
            "[VECTOR] Embedding modeli yükleniyor..."
        )

        self.model = SentenceTransformer(
            "intfloat/multilingual-e5-small"
        )

    def embed(
        self,
        text: str,
    ) -> list[float]:
        """
        Tek bir metni E5 passage embedding'ine çevirir.
        """

        clean_text = (
            text or ""
        ).strip()

        formatted_text = (
            f"passage: {clean_text}"
        )

        return self.model.encode(
            formatted_text
        ).tolist()

    def _build_chunk_id(
        self,
        chunk: Chunk,
    ) -> str:
        """
        Aynı içerik ve metadata kombinasyonu için
        her çalıştırmada aynı deterministic ID üretir.

        Baştaki/sondaki gereksiz boşluklar normalize edilir.
        """

        identity = "|".join(
            [
                (
                    chunk.doc_org
                    or ""
                ).strip(),
                (
                    chunk.doc_code
                    or ""
                ).strip(),
                (
                    chunk.version
                    or ""
                ).strip(),
                (
                    chunk.clause
                    or ""
                ).strip(),
                (
                    chunk.text
                    or ""
                ).strip(),
            ]
        )

        digest = hashlib.sha256(
            identity.encode(
                "utf-8"
            )
        ).hexdigest()

        return f"chunk_{digest}"

    def _prepare_unique_chunks(
        self,
        chunks: list[Chunk],
    ) -> list[tuple[str, Chunk]]:
        """
        VOID, boş ve duplicate chunk'ları temizler.

        Dönen yapı:
            [
                (chunk_id, chunk),
                ...
            ]

        Aynı deterministic ID yalnızca bir kez tutulur.
        """

        unique_chunks: list[
            tuple[str, Chunk]
        ] = []

        seen_ids: set[str] = set()

        void_count = 0
        empty_count = 0
        duplicate_count = 0

        for chunk in chunks:
            # -----------------------------------------
            # VOID
            # -----------------------------------------
            if chunk.status == DocStatus.VOID:
                void_count += 1
                continue

            # -----------------------------------------
            # BOŞ METİN
            # -----------------------------------------
            clean_text = (
                chunk.text
                or ""
            ).strip()

            if not clean_text:
                empty_count += 1
                continue

            # Metni normalize edilmiş haliyle tut.
            chunk.text = clean_text

            # -----------------------------------------
            # DETERMINISTIC ID
            # -----------------------------------------
            chunk_id = (
                self._build_chunk_id(
                    chunk
                )
            )

            # -----------------------------------------
            # DUPLICATE
            # -----------------------------------------
            if chunk_id in seen_ids:
                duplicate_count += 1
                continue

            seen_ids.add(
                chunk_id
            )

            unique_chunks.append(
                (
                    chunk_id,
                    chunk,
                )
            )

        print(
            f"[VECTOR] Gelen chunk: "
            f"{len(chunks)}"
        )

        if void_count:
            print(
                f"[VECTOR] VOID atlandı: "
                f"{void_count}"
            )

        if empty_count:
            print(
                f"[VECTOR] Boş chunk atlandı: "
                f"{empty_count}"
            )

        if duplicate_count:
            print(
                f"[VECTOR] Duplicate atlandı: "
                f"{duplicate_count}"
            )

        print(
            f"[VECTOR] Unique geçerli chunk: "
            f"{len(unique_chunks)}"
        )

        return unique_chunks

    def upsert_chunks(
        self,
        chunks: list[Chunk],
    ) -> int:
        """
        Chunk'ları temizler, deterministic ID'ye göre
        duplicate kayıtları kaldırır, batch olarak embed eder
        ve ChromaDB'ye yazar.

        VOID, boş ve aynı ID'ye sahip duplicate chunk'lar
        indexlenmez.
        """

        # -------------------------------------------------
        # 1. VALIDATION + DEDUP
        # -------------------------------------------------
        unique_chunks = (
            self._prepare_unique_chunks(
                chunks
            )
        )

        if not unique_chunks:
            return 0

        # -------------------------------------------------
        # 2. EMBEDDINGLERİ BATCH OLUŞTUR
        # -------------------------------------------------
        formatted_texts = [
            f"passage: {chunk.text}"
            for chunk_id, chunk
            in unique_chunks
        ]

        embeddings = self.model.encode(
            formatted_texts,
            batch_size=EMBEDDING_BATCH_SIZE,
            show_progress_bar=True,
        ).tolist()

        # -------------------------------------------------
        # 3. CHROMA BATCH UPSERT
        # -------------------------------------------------
        written = 0

        for start in tqdm(
            range(
                0,
                len(unique_chunks),
                UPSERT_BATCH_SIZE,
            ),
            desc="Chroma batch upsert",
            unit="batch",
        ):
            end = (
                start
                + UPSERT_BATCH_SIZE
            )

            batch_items = (
                unique_chunks[
                    start:end
                ]
            )

            batch_embeddings = (
                embeddings[
                    start:end
                ]
            )

            ids: list[str] = []
            documents: list[str] = []
            metadatas: list[dict] = []

            for (
                chunk_id,
                chunk,
            ) in batch_items:
                clean_text = (
                    chunk.text
                    or ""
                ).strip()

                ids.append(
                    chunk_id
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
                    else str(
                        chunk.status
                    )
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

            # Ek güvenlik:
            # Bu noktada batch içinde duplicate ID
            # bulunmaması gerekir.
            if len(ids) != len(set(ids)):
                raise RuntimeError(
                    "Chroma upsert öncesi batch içinde "
                    "duplicate chunk ID tespit edildi."
                )

            self.collection.upsert(
                ids=ids,
                embeddings=batch_embeddings,
                documents=documents,
                metadatas=metadatas,
            )

            written += len(
                batch_items
            )

        return written
