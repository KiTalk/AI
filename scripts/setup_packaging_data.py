from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from qdrant_client.models import VectorParams, Distance, PointStruct

# Qdrant 클라이언트 연결
client = QdrantClient(url="http://localhost:6333")

# SentenceTransformer 모델 사용 (메뉴와 동일한 모델)
model = SentenceTransformer('jhgan/ko-sroberta-multitask')

# 포장 옵션 데이터
packaging_items = [
    "포장 테이크아웃 가져가서",
    "매장 여기서 먹고"
]

# 포장 텍스트를 벡터로 변환
vectors = model.encode(packaging_items)
print(f"포장 옵션 벡터 차원: {len(vectors[0])}")

# 벡터 설정
vector_params = VectorParams(
    size=len(vectors[0]),
    distance=Distance.COSINE
)

# 기존 컬렉션 삭제 (있다면)
try:
    client.delete_collection(collection_name="packaging_options")
    print("기존 포장 옵션 컬렉션 삭제됨")
except Exception as e:
    print(f"기존 컬렉션 삭제 시도: {e}")

# 새 컬렉션 생성
try:
    client.create_collection(
        collection_name="packaging_options",
        vectors_config=vector_params
    )
    print("새 포장 옵션 컬렉션 생성 완료")
except Exception as e:
    print(f"컬렉션 생성 오류: {e}")
    exit()

# 포장 옵션 데이터 삽입
points = []
packaging_types = ["포장", "매장식사"]

for i, packaging_item in enumerate(packaging_items):
    point = PointStruct(
        id=i,
        vector=vectors[i].tolist(),
        payload={
            "packaging_item": packaging_item,
            "type": packaging_types[i]
        }
    )
    points.append(point)

try:
    client.upsert(
        collection_name="packaging_options",
        points=points
    )
    print(f"{len(packaging_items)}개 포장 옵션 삽입 완료")
except Exception as e:
    print(f"데이터 삽입 오류: {e}")
    exit()

# 삽입 확인
try:
    collection_info = client.get_collection(collection_name="packaging_options")
    print(f"포장 옵션 컬렉션 포인트 수: {collection_info.points_count}")
except Exception as e:
    print(f"확인 중 오류: {e}")

print("포장 옵션 데이터 설정 완료!")
