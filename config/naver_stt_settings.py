import os
import logging
from dotenv import load_dotenv

load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Settings:
    def __init__(self):
        # 네이버 API 설정
        self.NAVER_CLIENT_ID: str = os.getenv('NAVER_CLIENT_ID')
        self.NAVER_CLIENT_SECRET: str = os.getenv('NAVER_CLIENT_SECRET')

        # API 설정
        self.NAVER_STT_URL: str = "https://naveropenapi.apigw.ntruss.com/recog/v1/stt"

        # Qdrant 설정
        self.QDRANT_HOST: str = os.getenv('QDRANT_HOST', 'localhost')
        self.QDRANT_PORT: int = int(os.getenv('QDRANT_PORT', '6333'))
        self.QDRANT_API_KEY: str | None = os.getenv('QDRANT_API_KEY', None)

        # CORS 설정
        cors_env = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5173')
        self.CORS_ORIGINS: list[str] = [o.strip() for o in cors_env.split(',') if o.strip()]

        # 파일 업로드 제한
        self.MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
        self.MIN_FILE_SIZE: int = 10000  # 10KB

        # 지원 언어
        self.SUPPORTED_LANGUAGES: list[str] = ['Kor', 'Eng', 'Jpn', 'Chn']

        # 음성 주문 설정
        self.VOICE_ORDER_CONFIDENCE_THRESHOLD: float = 0.6
        self.MAX_MENU_CANDIDATES: int = 5

    def validate(self):
        if not self.NAVER_CLIENT_ID or not self.NAVER_CLIENT_SECRET:
            raise ValueError("NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET을 .env 파일에 설정해주세요.")
        return True

# 전역 설정 인스턴스
settings = Settings()
