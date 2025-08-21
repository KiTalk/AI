from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.naver_stt_settings import settings, logger
from routers import stt, health
from routers.logic_router import router as logic_router
from routers.logic_update_router import router as logic_update_router
from routers.order_at_once import router as order_at_once_router
from routers.order_retry import router as order_retry_router
from config.swagger_config import setup_swagger
from sentence_transformers import SentenceTransformer
from services.similarity_utils import set_model_getter
from config.config_cache import warmup_config_cache
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from database.simple_db import simple_menu_db

load_dotenv()

model = SentenceTransformer('jhgan/ko-sroberta-multitask')
set_model_getter(lambda: model)

@asynccontextmanager
async def lifespan(_: FastAPI):
    # 시작 시

    logger.info("🚀 FastAPI 애플리케이션 시작")

    # MySQL 연결 테스트 추가
    if simple_menu_db.test_connection():
        logger.info("✅ MySQL 데이터베이스 연결 성공")
    else:
        logger.error("❌ MySQL 데이터베이스 연결 실패")

    warmup_config_cache()
    logger.info("설정 캐시 예열 완료")
    yield

# FastAPI 앱 생성
app = FastAPI(
    title="네이버 클로바 STT API",
    description="실시간 음성 인식 서비스 백엔드",
    version="1.0.0",
    docs_url="/swagger-ui",
    redoc_url="/redoc",
    lifespan=lifespan
)

setup_swagger(app)

# CORS 설정 (프론트엔드와 통신을 위해)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(stt.router)
app.include_router(health.router)
app.include_router(logic_router)
app.include_router(logic_update_router)
app.include_router(order_at_once_router)
app.include_router(order_retry_router)

logger.info("FastAPI 애플리케이션이 초기화되었습니다.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)