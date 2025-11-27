# redis_store.py
import os
import numpy as np
import redis
from typing import List, Dict
from redis.commands.search.field import TextField, TagField, VectorField, NumericField
from redis.commands.search.indexDefinition import IndexDefinition, IndexType

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD")  # optional

INDEX_NAME = os.environ.get("REDIS_INDEX_NAME", "idx:configs")
KEY_PREFIX = os.environ.get("REDIS_KEY_PREFIX", "cfg:")

r = redis.Redis(
    host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD, decode_responses=False
)

def create_index(dim: int):
    schema = (
        TextField("device_name"),
        TagField("vendor"),
        TagField("section_type"),
        TextField("section_id"),
        TextField("file_path"),
        NumericField("chunk_index"),
        TextField("text"),
        VectorField(
            "embedding",
            "HNSW",
            {
                "TYPE": "FLOAT32",
                "DIM": dim,
                "DISTANCE_METRIC": "COSINE",
            },
        ),
    )
    definition = IndexDefinition(prefix=[KEY_PREFIX], index_type=IndexType.HASH)
    try:
        r.ft(INDEX_NAME).create_index(schema, definition=definition)
        print(f"[INFO] Created Redis index {INDEX_NAME} (dim={dim})")
    except Exception as exc:
        print(f"[INFO] Index {INDEX_NAME} exists or creation failed: {exc}")

def _to_float32_bytes(vec: List[float]) -> bytes:
    return np.array(vec, dtype=np.float32).tobytes()

def store_sections(sections: List[Dict]):
    if not sections:
        return
    dim = len(sections[0]["embedding"])
    create_index(dim)

    pipe = r.pipeline(transaction=False)
    for s in sections:
        key = f"{KEY_PREFIX}{s['device_name']}:{s['section_type']}:{s['section_id']}:{s.get('chunk_index', 0)}"
        mapping = {
            "device_name": s["device_name"],
            "vendor": s["vendor"],
            "section_type": s["section_type"],
            "section_id": s["section_id"],
            "file_path": s["file_path"],
            "chunk_index": s.get("chunk_index", 0),
            "text": s["text"],
            "embedding": _to_float32_bytes(s["embedding"]),
        }
        pipe.hset(key, mapping=mapping)
    pipe.execute()
    print(f"[INFO] Stored {len(sections)} sections in Redis")
