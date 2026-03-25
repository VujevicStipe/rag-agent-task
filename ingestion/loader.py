import os
from pathlib import Path


def load_documents(documents_dir: str) -> list[dict]:
    docs = []
    path = Path(documents_dir)

    for filepath in sorted(path.glob("*.md")):
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        docs.append({
            "filename": filepath.name,
            "content": content
        })
        print(f"Loaded: {filepath.name}")

    print(f"\nTotal documents loaded: {len(docs)}")
    return docs