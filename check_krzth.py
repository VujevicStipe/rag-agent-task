import chromadb

client = chromadb.PersistentClient(path="chroma_db")
col = client.get_collection("documents")
results = col.get(
    where={"filename": {"$eq": "krzth_monkey_document.md"}},
    include=["metadatas", "documents"]
)

print(f"Chunks: {len(results['ids'])}")
for i, m in enumerate(results["metadatas"]):
    print(f"\n[{i+1}] Section: {m['section_title']}")
    print(f"     Content preview: {results['documents'][i][:100]}...")