from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from qdrant_client.models import VectorParams, Distance, PointStruct

client = QdrantClient(url="http://qdrant:6333")
model = SentenceTransformer("jhgan/ko-sroberta-multitask")

PACKAGING_DATA = [
    {
        "type": "포장",
        "aliases": [
            "포장", "포장해주세요", "테이크아웃", "가지고 갈게요", "take out",
            "가져가", "가져갈게요", "갖고 갈게요", "나가서 먹을게요", "포장해줘"
        ],
    },
    {
        "type": "매장식사",
        "aliases": [
            "매장", "여기서 먹고 갈게요", "먹고 갈게요", "먹고",
            "여기서", "매장에서 먹을게요", "앉아서 먹을게요",
        ],
    },
]

COL = "packaging_options"

try:
    client.delete_collection(collection_name=COL)
except Exception:
    pass

client.create_collection(
    collection_name=COL,
    vectors_config=VectorParams(size=768, distance=Distance.COSINE),
)

points = []
pid = 0
for item in PACKAGING_DATA:
    ptype = item["type"]
    for phrase in item["aliases"]:
        vec = model.encode([phrase])[0].tolist()
        points.append(
            PointStruct(
                id=pid,
                vector=vec,
                payload={
                    "type": ptype,
                    "alias": phrase
                },
            )
        )
        pid += 1

client.upsert(collection_name=COL, points=points)

info = client.get_collection(collection_name=COL)
print(f"[OK] {COL} 업서트 완료. points={info.points_count}")
