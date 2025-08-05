import requests
from config.settings import settings, logger
from models.stt_models import STTResponse

class NaverSTTService:
    """네이버 STT 서비스"""
    
    def __init__(self):
        # 설정 유효성 검사
        settings.validate()
        
        self.client_id = settings.NAVER_CLIENT_ID
        self.client_secret = settings.NAVER_CLIENT_SECRET
        self.api_url = settings.NAVER_STT_URL
        
        self.headers = {
            'X-NCP-APIGW-API-KEY-ID': self.client_id,
            'X-NCP-APIGW-API-KEY': self.client_secret,
            'Content-Type': 'application/octet-stream'
        }

    def convert_speech_to_text(self, audio_data: bytes, lang: str = 'Kor') -> dict:
        """음성 데이터를 텍스트로 변환"""
        try:
            params = {'lang': lang}
            response = requests.post(
                self.api_url,
                headers=self.headers,
                params=params,
                data=audio_data,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "text": result.get('text', ''),
                    "confidence": result.get('confidence', 0)
                }
            else:
                logger.error(f"STT API 오류: {response.status_code}, {response.text}")
                return {
                    "success": False,
                    "error": f"API 오류: {response.status_code}",
                    "details": response.text
                }

        except requests.exceptions.Timeout:
            return {"success": False, "error": "요청 시간 초과"}
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"네트워크 오류: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"처리 중 오류: {str(e)}"}
