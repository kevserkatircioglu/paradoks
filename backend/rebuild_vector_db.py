import os
import shutil
import chromadb

SOURCE_PATH = "vector_db"
TARGET_PATH = "vector_db_clean"

SOURCE_COLLECTION = "telecom_standards"
TARGET_COLLECTION = "telecom_standards"

BATCH_SIZE = 500


print("Eski DB açılıyor...")

old_client = chromadb.PersistentClient(path=SOURCE_PATH)
old_collection = old_client.get_collection(SOURCE_COLLECTION)


# Daha önce yarım kalmış temiz DB varsa sil.
if os.path.exists(TARGET_PATH):
    print("Eski vector_db_clean siliniyor...")
    shutil.rmtree(TARGET_PATH)


print("Yeni DB oluşturuluyor...")

new_client = chromadb.PersistentClient(path=TARGET_PATH)
new_collection = new_client.create_collection(
    name=TARGET_COLLECTION
)


offset = 0
total = 0

while True:
    print(f"\nBatch okunuyor | offset={offset}")

    result = old_collection.get(
        limit=BATCH_SIZE,
        offset=offset,
        include=["embeddings", "documents", "metadatas"]
    )

    ids = result["ids"]

    if not ids:
        break

    embeddings = result["embeddings"]

    if hasattr(embeddings, "tolist"):
        embeddings = embeddings.tolist()

    new_collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=result["documents"],
        metadatas=result["metadatas"],
    )

    total += len(ids)
    offset += len(ids)

    print(f"Aktarıldı: {total}")

    if len(ids) < BATCH_SIZE:
        break


print("\n============================")
print("AKTARIM TAMAMLANDI")
print("Toplam aktarılan kayıt:", total)
print("Yeni DB:", TARGET_PATH)
print("============================")