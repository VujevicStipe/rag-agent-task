import chromadb

client = chromadb.PersistentClient(path="chroma_db")
col = client.get_collection("documents")
results = col.get(include=["metadatas"])

filenames = set()
for m in results["metadatas"]:
    filenames.add(m["filename"])

print(f"Total chunks: {len(results['ids'])}")
print(f"\nUnique files in ChromaDB ({len(filenames)}):")
for f in sorted(filenames):
    count = sum(1 for m in results["metadatas"] if m["filename"] == f)
    print(f"  {f}: {count} chunks")