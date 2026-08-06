"""
Embeds text chunks into vector representations and writes them to the Vector Database.
Uses ChromaDB (PersistentClient) under 'backend/vector_db' with 'intfloat/multilingual-e5-small'.
"""

import os
import chromadb
from sentence_transformers import SentenceTransformer
from models import Chunk, DocStatus
from tqdm import tqdm  # İlerleme çubuğu kütüphanesini ekledik!


class VectorStore:
    def __init__(self, collection_name: str = "telecom_standards"):
        self.collection_name = collection_name
        
        # Ensure the backend/vector_db directory exists as requested by teammate
        db_path = os.path.join("backend", "vector_db")
        os.makedirs(db_path, exist_ok=True)
        
        # Initialize local persistent ChromaDB client at the specified path
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(collection_name)
        
        # Initialize the exact multilingual embedding model requested by teammate
        self.model = SentenceTransformer("intfloat/multilingual-e5-small")

    def embed(self, text: str) -> list[float]:
        """
        Converts human-readable text into a dense vector array (embeddings) 
        using the intfloat/multilingual-e5-small model.
        """
        # For E5 models, prefixing text with "passage: " is recommended for documents
        formatted_text = f"passage: {text}"
        embedding = self.model.encode(formatted_text).tolist()
        return embedding

    def upsert_chunks(self, chunks: list[Chunk]) -> int:
        """
        Processes a list of chunks, generates their embeddings, and inserts/updates 
        them in the Vector Database (ChromaDB). Skips void/deprecated chunks.
        """
        written = 0
        
        # tqdm ile for döngüsünü sarıyoruz ki ekranda ilerleme çubuğu çıksın
        for i, chunk in enumerate(tqdm(chunks, desc="Vektörler Veritabanına Yazılıyor", unit="chunk")):
            # Skip clauses marked as "Void" to save DB space and prevent retrieving obsolete info
            if chunk.status == DocStatus.VOID:
                continue
                
            # Generate the vector embedding for the text content
            chunk.embedding = self.embed(chunk.text)
            
            # Execute database insertion with exact metadata fields expected by teammate
            self.collection.upsert(
                ids=[f"chunk_{i}_{hash(chunk.text)}"],
                embeddings=[chunk.embedding],
                documents=[chunk.text],
                metadatas=[{
                    "org": chunk.doc_org or "",
                    "code": chunk.doc_code or "",
                    "version": chunk.version or "Latest",
                    "clause": chunk.clause or "",
                    "status": str(chunk.status.value) if hasattr(chunk.status, "value") else str(chunk.status),
                    "source_url": chunk.source_url or ""
                }]
            )
            
            written += 1
        return written