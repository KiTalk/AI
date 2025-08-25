import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from sentence_transformers import SentenceTransformer

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION = os.getenv("MENU_COLLECTION", "menu")
EMBED_MODEL = os.getenv("EMBED_MODEL", "jhgan/ko-sroberta-multitask")

if QDRANT_URL:
    qclient = QdrantClient(url=QDRANT_URL)
else:
    qclient = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

model = SentenceTransformer(EMBED_MODEL)

def ensure_collection():
    dim = model.get_sentence_embedding_dimension()
    names = [c.name for c in qclient.get_collections().collections]
    if COLLECTION not in names:
        qclient.recreate_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )

def _text(name: str, temp: str) -> str:
    return f"{name} {temp}"

def upsert_menu_point(*, id_: int, name: str, price: int, popular: bool, temp: str):
    ensure_collection()
    vec = model.encode([_text(name, temp)])[0].tolist()

    qclient.upsert(
        collection_name=COLLECTION,
        points=[{
            "id": id_,
            "vector": vec,
            "payload": {
                "id": id_,
                "name": name,
                "price": price,
                "popular": popular,
                "temp": temp,
            }
        }]
    )
