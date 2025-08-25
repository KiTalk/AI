import json
import os

# 수량 관련 설정
quantity_config = {
    "regex_patterns": [
        r'(\d+)개',
        r'(\d+)잔', 
        r'(\d+)개\s*주세요',
        r'(\d+)\s*개',
        r'(\d+)\s*잔'
    ],
    "korean_numbers": {
        "한": 1, "하나": 1, "두": 2, "둘": 2, "세": 3, "셋": 3,
        "네": 4, "넷": 4, "다섯": 5, "여섯": 6, "일곱": 7,
        "여덟": 8, "아홉": 9, "열": 10
    },
    "default_quantity": 1
}

# config 폴더에 저장
config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
config_file = os.path.join(config_dir, 'quantity_patterns.json')

try:
    os.makedirs(config_dir, exist_ok=True)
    
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(quantity_config, f, ensure_ascii=False, indent=2)
    
    print(f"수량 패턴 설정 파일 생성 완료: {config_file}")
    print(f"- 정규식 패턴: {len(quantity_config['regex_patterns'])}개")
    print(f"- 한글 숫자: {len(quantity_config['korean_numbers'])}개")
    
except Exception as e:
    print(f"설정 파일 생성 오류: {e}")
    exit()

print("수량 패턴 설정 완료!")
