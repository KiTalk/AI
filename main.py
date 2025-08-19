from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.naver_stt_settings import settings, logger
from routers import stt, health
from routers.logic_router import router as logic_router
from routers.logic_update_router import router as logic_update_router
from config.swagger_config import setup_swagger

# FastAPI 앱 생성
app = FastAPI(
    title="네이버 클로바 STT API",
    description="실시간 음성 인식 서비스 백엔드",
    version="1.0.0",
    docs_url="/swagger-ui",
    redoc_url="/redoc"
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

logger.info("FastAPI 애플리케이션이 초기화되었습니다.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
