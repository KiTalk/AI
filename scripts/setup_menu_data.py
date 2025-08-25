from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from qdrant_client.models import VectorParams, Distance, PointStruct

# Qdrant 클라이언트 연결
client = QdrantClient(url="http://qdrant:6333")

# SentenceTransformer 모델 사용
model = SentenceTransformer('jhgan/ko-sroberta-multitask')

# 메뉴 데이터 (더 많은 메뉴 추가)
menu_items = [
    # 커피 (1-12)
    {"menu_id": 1, "name": "아메리카노", "price": 4000, "popular": True, "temp": "hot"},
    {"menu_id": 2, "name": "아메리카노", "price": 4000, "popular": True, "temp": "ice"},
    {"menu_id": 3, "name": "카페라떼", "price": 4500, "popular": True, "temp": "hot"},
    {"menu_id": 4, "name": "카페라떼", "price": 4500, "popular": True, "temp": "ice"},
    {"menu_id": 5, "name": "바닐라 라떼", "price": 4700, "popular": True, "temp": "hot"},
    {"menu_id": 6, "name": "바닐라 라떼", "price": 4700, "popular": True, "temp": "ice"},
    {"menu_id": 7, "name": "카푸치노", "price": 5000, "popular": False, "temp": "hot"},
    {"menu_id": 8, "name": "카푸치노", "price": 5000, "popular": False, "temp": "ice"},
    {"menu_id": 9, "name": "카라멜 마키아토", "price": 4700, "popular": False, "temp": "hot"},
    {"menu_id": 10, "name": "카라멜 마키아토", "price": 4700, "popular": False, "temp": "ice"},
    {"menu_id": 11, "name": "카페모카", "price": 4700, "popular": False, "temp": "hot"},
    {"menu_id": 12, "name": "카페모카", "price": 4700, "popular": False, "temp": "ice"},

    # 기타 음료 (13-20)
    {"menu_id": 13, "name": "초코 라떼", "price": 4000, "popular": False, "temp": "hot"},
    {"menu_id": 14, "name": "초코 라떼", "price": 4000, "popular": False, "temp": "ice"},
    {"menu_id": 15, "name": "녹차 라떼", "price": 4000, "popular": False, "temp": "hot"},
    {"menu_id": 16, "name": "녹차 라떼", "price": 4000, "popular": False, "temp": "ice"},
    {"menu_id": 17, "name": "밀크티", "price": 4000, "popular": False, "temp": "hot"},
    {"menu_id": 18, "name": "밀크티", "price": 4000, "popular": False, "temp": "ice"},
    {"menu_id": 19, "name": "레몬에이드", "price": 4500, "popular": False, "temp": "ice"},
    {"menu_id": 20, "name": "자몽에이드", "price": 4500, "popular": False, "temp": "ice"},

    # 주스 (21-23)
    {"menu_id": 21, "name": "오렌지 주스", "price": 5000, "popular": False, "temp": "ice"},
    {"menu_id": 22, "name": "딸기 주스", "price": 5000, "popular": False, "temp": "ice"},
    {"menu_id": 23, "name": "키위 주스", "price": 5000, "popular": False, "temp": "ice"},

    # 차 (24-27)
    {"menu_id": 24, "name": "캐모마일 티", "price": 4000, "popular": False, "temp": "hot"},
    {"menu_id": 25, "name": "페퍼민트 티", "price": 4000, "popular": False, "temp": "hot"},
    {"menu_id": 26, "name": "유자차", "price": 4500, "popular": False, "temp": "hot"},
    {"menu_id": 27, "name": "레몬티", "price": 4500, "popular": False, "temp": "hot"},

    # 디저트 (28-33)
    {"menu_id": 28, "name": "치즈케이크", "price": 5500, "popular": False, "temp": "none"},
    {"menu_id": 29, "name": "티라미수", "price": 5500, "popular": False, "temp": "none"},
    {"menu_id": 30, "name": "마카롱 (3개)", "price": 5000, "popular": False, "temp": "none"},
    {"menu_id": 31, "name": "크루아상", "price": 4000, "popular": False, "temp": "none"},
    {"menu_id": 32, "name": "초코 머핀", "price": 3500, "popular": False, "temp": "none"},
    {"menu_id": 33, "name": "플레인 스콘", "price": 3500, "popular": False, "temp": "none"},

    # 스무디 (34-37)
    {"menu_id": 34, "name": "블루베리 요거트 스무디", "price": 5800, "popular": False, "temp": "ice"},
    {"menu_id": 35, "name": "망고 요거트 스무디", "price": 5800, "popular": False, "temp": "ice"},
    {"menu_id": 36, "name": "딸기 바나나 스무디", "price": 6000, "popular": False, "temp": "ice"},
    {"menu_id": 37, "name": "플레인 요거트 스무디", "price": 5500, "popular": False, "temp": "ice"},

    # 프라페 (38-39)
    {"menu_id": 38, "name": "말차 프라페", "price": 5500, "popular": False, "temp": "ice"},
    {"menu_id": 39, "name": "초콜릿 프라페", "price": 5500, "popular": False, "temp": "ice"},

    # 특색 라떼 (40-42)
    {"menu_id": 40, "name": "흑임자 라떼", "price": 5000, "popular": False, "temp": "hot"},
    {"menu_id": 41, "name": "흑임자 라떼", "price": 5500, "popular": False, "temp": "ice"},
    {"menu_id": 42, "name": "곡물 라떼", "price": 5000, "popular": False, "temp": "hot"},

    # 스페셜 티 (43-44)
    {"menu_id": 43, "name": "자몽 허니 블랙티", "price": 4800, "popular": False, "temp": "hot"},
    {"menu_id": 44, "name": "레몬 허니 블랙티", "price": 4800, "popular": False, "temp": "hot"},

    # 에이드 (45-46)
    {"menu_id": 45, "name": "블루 레몬 에이드", "price": 4800, "popular": False, "temp": "ice"},
    {"menu_id": 46, "name": "청포도 에이드", "price": 4800, "popular": False, "temp": "ice"},

    # 버블티 (47-48)
    {"menu_id": 47, "name": "흑당 버블 밀크티", "price": 5500, "popular": False, "temp": "ice"},
    {"menu_id": 48, "name": "제주 말차 버블 라떼", "price": 5800, "popular": False, "temp": "ice"}
]

# 메뉴 텍스트를 벡터로 변환
menu_names = [item["name"] for item in menu_items]
vectors = model.encode(menu_names)
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
       id=menu_item["menu_id"],
       vector=vectors[i].tolist(),
       payload={
           "menu_id": menu_item["menu_id"],
           "menu_item": menu_item["name"],
           "price": menu_item["price"],
           "popular": menu_item["popular"],
           "temp": menu_item["temp"]
       }
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