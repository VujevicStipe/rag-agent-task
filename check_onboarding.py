import chromadb

client = chromadb.PersistentClient(path="chroma_db")
col = client.get_collection("documents")

# Dohvati SVE dokumente
results = col.get(
    include=["metadatas"]
)

filenames = set()
for meta in results["metadatas"]:
    filenames.add(meta["filename"])

print("\n" + "=" * 60)
print(" ALL FILES IN ChromaDB")
print("=" * 60 + "\n")

for filename in sorted(filenames):
    count = sum(1 for m in results["metadatas"] if m["filename"] == filename)
    print(f"  {filename}: {count} chunks")

print(f"\nTotal: {len(results['ids'])} chunks\n")