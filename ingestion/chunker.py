import re
import hashlib


def get_content_hash(text: str) -> str:
    return hashlib.md5(text.strip().encode()).hexdigest()


def parse_md_sections(content: str, filename: str) -> list[dict]:
    lines = content.split("\n")
    sections = []
    current_title = filename
    current_lines = []

    for line in lines:
        if re.match(r'^#{1,3} ', line):
            if current_lines:
                sections.append({
                    "title": current_title,
                    "content": "\n".join(current_lines).strip()
                })
            current_title = line.lstrip("#").strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append({
            "title": current_title,
            "content": "\n".join(current_lines).strip()
        })

    return [s for s in sections if s["content"]]


def chunk_document(doc: dict, overlap_lines: int = 3) -> list[dict]:
    filename = doc["filename"]
    sections = parse_md_sections(doc["content"], filename)
    chunks = []

    for i, section in enumerate(sections):
        content = f"{section['title']}\n\n{section['content']}"

        if i > 0 and overlap_lines > 0:
            prev_lines = sections[i - 1]["content"].split("\n")
            overlap = "\n".join(prev_lines[-overlap_lines:])
            content = overlap + "\n" + content

        chunk = {
            "filename": filename,
            "section_title": section["title"],
            "chunk_index": i,
            "content": content,
            "content_hash": get_content_hash(content)
        }

        chunks.append(chunk)

    return chunks


def chunk_all_documents(documents: list[dict]) -> list[dict]:
    all_chunks = []

    for doc in documents:
        chunks = chunk_document(doc)
        all_chunks.extend(chunks)

    print(f"Total chunks: {len(all_chunks)}")
    return all_chunks