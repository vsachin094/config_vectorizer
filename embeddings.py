# embeddings.py
from typing import List, Dict
from openai import OpenAI

client = OpenAI()  # requires OPENAI_API_KEY env var

EMBED_MODEL = "text-embedding-3-small"

def embed_sections(sections: List[Dict], batch_size: int = 64) -> List[Dict]:
    if not sections:
        return sections

    for i in range(0, len(sections), batch_size):
        batch = sections[i : i + batch_size]
        texts = [s["text"] for s in batch]
        resp = client.embeddings.create(
            model=EMBED_MODEL,
            input=texts,
        )
        for s, d in zip(batch, resp.data):
            s["embedding"] = d.embedding
    return sections
