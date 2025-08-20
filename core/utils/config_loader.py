import json
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# 설정 파일을 캐싱하여 관리
class ConfigManager:
    _cache: Dict[str, Any] = {}

    # 설정 파일을 로드하고 캐싱
    @classmethod
    def load_config(cls, config_name: str, config_dir: str = 'config') -> Dict[str, Any]:
        cache_key = f"{config_dir}/{config_name}"

        # 캐시에 있으면 반환
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        try:
            # 설정 파일 경로 구성
            current_dir = os.path.dirname(__file__)
            config_path = os.path.join(current_dir, '..', '..', config_dir)
            config_file = os.path.join(config_path, f"{config_name}.json")

            # 파일 로드
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            # 캐시에 저장
            cls._cache[cache_key] = config_data
            logger.info(f"설정 파일 로드 성공: {config_file}")

            return config_data

        except FileNotFoundError:
            logger.error(f"설정 파일을 찾을 수 없습니다: {config_file}")
            raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {config_name}")

        except json.JSONDecodeError as e:
            logger.error(f"설정 파일 JSON 파싱 오류: {e}")
            raise json.JSONDecodeError(f"설정 파일 JSON 파싱 오류: {config_name}")

        except Exception as e:
            logger.error(f"설정 파일 로드 실패: {e}")
            raise Exception(f"설정 파일 로드 실패: {config_name}")

    # 캐시를 지웁니다
    @classmethod
    def clear_cache(cls, config_name: Optional[str] = None, config_dir: str = 'config') -> None:
        if config_name:
            cache_key = f"{config_dir}/{config_name}"
            cls._cache.pop(cache_key, None)
            logger.info(f"캐시 삭제: {cache_key}")
        else:
            cls._cache.clear()
            logger.info("전체 캐시 삭제")

    # 설정을 강제로 다시 로드
    @classmethod
    def reload_config(cls, config_name: str, config_dir: str = 'config') -> Dict[str, Any]:
        cls.clear_cache(config_name, config_dir)
        return cls.load_config(config_name, config_dir)

    # 캐시 정보 반환
    @classmethod
    def get_cache_info(cls) -> Dict[str, Any]:
        return {
            "cached_configs": list(cls._cache.keys()),
            "cache_size": len(cls._cache)
        }


# 편의 함수들
def load_config(config_name: str, config_dir: str = 'config') -> Dict[str, Any]:
    return ConfigManager.load_config(config_name, config_dir)

def clear_config_cache(config_name: Optional[str] = None, config_dir: str = 'config') -> None:
    ConfigManager.clear_cache(config_name, config_dir)

def reload_config(config_name: str, config_dir: str = 'config') -> Dict[str, Any]:
    return ConfigManager.reload_config(config_name, config_dir)