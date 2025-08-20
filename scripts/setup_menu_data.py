from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from qdrant_client.models import VectorParams, Distance, PointStruct

# Qdrant 클라이언트 연결
client = QdrantClient(url="http://localhost:6333")

# SentenceTransformer 모델 사용
model = SentenceTransformer('jhgan/ko-sroberta-multitask')

# 메뉴 데이터 (더 많은 메뉴 추가)
menu_items = [
    # 기본 커피류
    {"name": "아메리카노", "price": 4000, "popular": True, "temp": "hot"},
    {"name": "아메리카노", "price": 4000, "popular": True, "temp": "ice"},
    {"name": "카페라떼", "price": 4500, "popular": True, "temp": "hot"},
    {"name": "카페라떼", "price": 4500, "popular": True, "temp": "ice"},
    {"name": "바닐라 라떼", "price": 4700, "popular": True, "temp": "hot"},
    {"name": "바닐라 라떼", "price": 4700, "popular": True, "temp": "ice"},

    # 기타 커피류
    {"name": "카푸치노", "price": 5000, "popular": False, "temp": "hot"},
    {"name": "카푸치노", "price": 5000, "popular": False, "temp": "ice"},
    {"name": "카라멜 마끼아또", "price": 4700, "popular": False, "temp": "hot"},
    {"name": "카라멜 마끼아또", "price": 4700, "popular": False, "temp": "ice"},
    {"name": "카페모카", "price": 4700, "popular": False, "temp": "hot"},
    {"name": "카페모카", "price": 4700, "popular": False, "temp": "ice"},
    {"name": "초코 라떼", "price": 4000, "popular": False, "temp": "hot"},
    {"name": "초코 라떼", "price": 4000, "popular": False, "temp": "ice"},
    {"name": "녹차 라떼", "price": 4000, "popular": False, "temp": "hot"},
    {"name": "녹차 라떼", "price": 4000, "popular": False, "temp": "ice"},

    # 차/음료류
    {"name": "밀크티", "price": 4000, "popular": False, "temp": "hot"},
    {"name": "밀크티", "price": 4000, "popular": False, "temp": "ice"},
    {"name": "레몬에이드", "price": 4500, "popular": False, "temp": "ice"},
    {"name": "자몽에이드", "price": 4500, "popular": False, "temp": "ice"},
    {"name": "오렌지 주스", "price": 5000, "popular": False, "temp": "ice"},
    {"name": "딸기 주스", "price": 5000, "popular": False, "temp": "ice"},
    {"name": "키위 주스", "price": 5000, "popular": False, "temp": "ice"},
    {"name": "캐모마일 티", "price": 4000, "popular": False, "temp": "hot"},
    {"name": "캐모마일 티", "price": 4000, "popular": False, "temp": "ice"},
    {"name": "페퍼민트 티", "price": 4000, "popular": False, "temp": "hot"},
    {"name": "페퍼민트 티", "price": 4000, "popular": False, "temp": "ice"},
    {"name": "유자차", "price": 4500, "popular": False, "temp": "hot"},
    {"name": "유자차", "price": 4500, "popular": False, "temp": "ice"},
    {"name": "레몬티", "price": 4500, "popular": False, "temp": "hot"},
    {"name": "레몬티", "price": 4500, "popular": False, "temp": "ice"},

    # 디저트류
    {"name": "치즈케이크", "price": 5500, "popular": False, "temp": "none"},
    {"name": "티라미수", "price": 5500, "popular": False, "temp": "none"},
    {"name": "마카롱 (3개)", "price": 5000, "popular": False, "temp": "none"},
    {"name": "크루아상", "price": 4000, "popular": False, "temp": "none"},
    {"name": "초코 머핀", "price": 3500, "popular": False, "temp": "none"},
    {"name": "플레인 스콘", "price": 3500, "popular": False, "temp": "none"},

    # 스무디/프라페류
    {"name": "블루베리 요거트 스무디", "price": 5800, "popular": False, "temp": "ice"},
    {"name": "망고 요거트 스무디", "price": 5800, "popular": False, "temp": "ice"},
    {"name": "딸기 바나나 스무디", "price": 6000, "popular": False, "temp": "ice"},
    {"name": "플레인 요거트 스무디", "price": 5500, "popular": False, "temp": "ice"},
    {"name": "말차 프라페", "price": 5500, "popular": False, "temp": "ice"},
    {"name": "초콜릿 프라페", "price": 5500, "popular": False, "temp": "ice"},

    # 특색 라떼류
    {"name": "흑임자 라떼", "price": 5000, "popular": False, "temp": "hot"},
    {"name": "흑임자 라떼", "price": 5000, "popular": False, "temp": "ice"},
    {"name": "고구마 라떼", "price": 5000, "popular": False, "temp": "hot"},
    {"name": "고구마 라떼", "price": 5000, "popular": False, "temp": "ice"},
    {"name": "곡물 라떼", "price": 5000, "popular": False, "temp": "hot"},
    {"name": "곡물 라떼", "price": 5000, "popular": False, "temp": "ice"},

    # 특색 음료류
    {"name": "자몽 허니 블랙티", "price": 4800, "popular": False, "temp": "hot"},
    {"name": "자몽 허니 블랙티", "price": 4800, "popular": False, "temp": "ice"},
    {"name": "레몬 허니 블랙티", "price": 4800, "popular": False, "temp": "hot"},
    {"name": "레몬 허니 블랙티", "price": 4800, "popular": False, "temp": "ice"},
    {"name": "블루 레몬 에이드", "price": 4800, "popular": False, "temp": "ice"},
    {"name": "청포도 에이드", "price": 4800, "popular": False, "temp": "ice"},
    {"name": "흑당 버블 밀크티", "price": 5500, "popular": False, "temp": "ice"},
    {"name": "제주 말차 버블 라떼", "price": 5800, "popular": False, "temp": "ice"}
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
       id=i,
       vector=vectors[i].tolist(),
       payload={
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