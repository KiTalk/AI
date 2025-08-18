from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from qdrant_client.models import VectorParams, Distance, PointStruct

# Qdrant 클라이언트 연결
client = QdrantClient(url="http://localhost:6333")

# SentenceTransformer 모델 사용
model = SentenceTransformer('jhgan/ko-sroberta-multitask')

# 메뉴 데이터 (더 많은 메뉴 추가)
menu_items = [
    {"name": "떡볶이", "price": 4000},
    {"name": "김밥", "price": 3000},
    {"name": "라면", "price": 3500}
]

# 메뉴 텍스트를 벡터로 변환
vectors = model.encode(menu_items)
print(f"벡터 차원: {len(vectors[0])}")

# 벡터 설정
vector_params = VectorParams(
   size=len(vectors[0]),
   distance=Distance.COSINE
)

# 기존 컬렉션 삭제 (있다면)
try:
   client.delete_collection(collection_name="menu")
   print("기존 컬렉션 삭제됨")
except Exception as e:
   print(f"기존 컬렉션 삭제 시도: {e}")

# 새 컬렉션 생성
try:
   client.create_collection(
       collection_name="menu",
       vectors_config=vector_params
   )
   print("새 컬렉션 생성 완료")
except Exception as e:
   print(f"컬렉션 생성 오류: {e}")
   exit()

# 메뉴 데이터 삽입
points = []
for i, menu_item in enumerate(menu_items):
   point = PointStruct(
       id=i,
       vector=vectors[i].tolist(),
       payload={"menu_item": menu_item["name"], "price": menu_item["price"]}
   )
   points.append(point)

try:
   client.upsert(
       collection_name="menu",
       points=points
   )
   print(f"{len(menu_items)}개 메뉴 항목 삽입 완료")
except Exception as e:
   print(f"데이터 삽입 오류: {e}")
   exit()

# 삽입 확인
try:
   collection_info = client.get_collection(collection_name="menu")
   print(f"컬렉션 포인트 수: {collection_info.points_count}")
except Exception as e:
   print(f"확인 중 오류: {e}")

print("메뉴 데이터 설정 완료!")