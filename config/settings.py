import os
import logging
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Settings:
    """애플리케이션 설정"""
    
    # 네이버 API 설정
    NAVER_CLIENT_ID: str = os.getenv('NAVER_CLIENT_ID')
    NAVER_CLIENT_SECRET: str = os.getenv('NAVER_CLIENT_SECRET')
    
    # API 설정
    NAVER_STT_URL: str = "https://naveropenapi.apigw.ntruss.com/recog/v1/stt"
    
    # CORS 설정
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173"]
    
    # 파일 업로드 제한
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    MIN_FILE_SIZE: int = 10000  # 10KB
    
    # 지원 언어
    SUPPORTED_LANGUAGES: list = ['Kor', 'Eng', 'Jpn', 'Chn']
    
    def validate(self):
        """설정 유효성 검사"""
        if not self.NAVER_CLIENT_ID or not self.NAVER_CLIENT_SECRET:
            raise ValueError("NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET을 .env 파일에 설정해주세요.")
        return True

# 전역 설정 인스턴스
settings = Settings()
