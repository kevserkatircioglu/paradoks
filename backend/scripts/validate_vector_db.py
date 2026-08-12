from pathlib import Path

import chromadb


DB_PATH = Path(__file__).resolve().parents[1] / "vector_db"
COLLECTION_NAME = "telecom_standards"


def main() -> None:
    print(f"Vector DB yolu: {DB_PATH}")

    if not DB_PATH.exists():
        print("HATA: vector_db klasörü bulunamadı.")
        return

    client = chromadb.PersistentClient(
        path=str(DB_PATH),
    )

    collections = client.list_collections()

    if not collections:
        print("HATA: Chroma içinde collection bulunamadı.")
        return

    collection_names = [
        collection.name
        for collection in collections
    ]

    print(
        "Bulunan collection'lar:",
        ", ".join(collection_names),
    )

    if COLLECTION_NAME not in collection_names:
        print(
            f"HATA: '{COLLECTION_NAME}' collection'ı bulunamadı."
        )
        return

    collection = client.get_collection(
        COLLECTION_NAME,
    )

    count = collection.count()

    print(
        f"Toplam kayıt sayısı: {count}"
    )

    if count == 0:
        print("HATA: Collection boş.")
        return

    sample = collection.get(
        limit=5,
        include=[
            "documents",
            "metadatas",
            "embeddings",
        ],
    )

    documents = sample.get("documents") or []
    metadatas = sample.get("metadatas") or []
    embeddings = sample.get("embeddings")

    print("\nİlk kayıtların kontrolü:\n")

    for index, metadata in enumerate(metadatas):
        print(f"--- Kayıt {index + 1} ---")

        print(
            "Org:",
            metadata.get("org"),
        )
        print(
            "Code:",
            metadata.get("code"),
        )
        print(
            "Version:",
            metadata.get("version"),
        )
        print(
            "Clause:",
            metadata.get("clause"),
        )
        print(
            "Status:",
            metadata.get("status"),
        )
        print(
            "Source URL:",
            metadata.get("source_url"),
        )

        if index < len(documents):
            document = documents[index] or ""

            print(
                "Metin örneği:",
                document[:200].replace(
                    "\n",
                    " ",
                ),
            )

        if embeddings is not None and index < len(embeddings):
            embedding = embeddings[index]

            print(
                "Embedding boyutu:",
                len(embedding),
            )

        print()

    indexed_count = collection.count(
        where={
            "status": "indexed",
        }
    )

    available_count = collection.count(
        where={
            "status": "available",
        }
    )

    print(
        f"Indexed kayıt sayısı: {indexed_count}"
    )
    print(
        f"Available kayıt sayısı: {available_count}"
    )

    print("\nVector DB doğrulaması tamamlandı.")


if __name__ == "__main__":
    main()