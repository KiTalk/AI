from database.simple_db import simple_menu_db
import os


def test_mysql_connection():
    print("=" * 50)
    print("🔍 MySQL 연결 테스트 시작")
    print("=" * 50)

    # 1. 환경 변수 확인
    print("\n📋 환경 변수 확인:")
    print(f"  DB_HOST: {os.getenv('DB_HOST')}")
    print(f"  DB_PORT: {os.getenv('DB_PORT')}")
    print(f"  DB_USER: {os.getenv('DB_USER')}")
    print(f"  DB_PASSWORD: {'*' * len(os.getenv('DB_PASSWORD', '')) if os.getenv('DB_PASSWORD') else '(빈 값)'}")
    print(f"  DB_NAME: {os.getenv('DB_NAME')}")

    # 2. 연결 테스트
    print("\n🔌 데이터베이스 연결 테스트:")
    try:
        if simple_menu_db.test_connection():
            print("  ✅ MySQL 연결 성공!")

            # 3. 테이블 존재 확인
            print("\n📊 테이블 확인:")
            connection = simple_menu_db.get_connection()
            if connection:
                try:
                    with connection.cursor() as cursor:
                        # 테이블 목록 조회
                        cursor.execute("SHOW TABLES")
                        tables = cursor.fetchall()
                        print(f"  데이터베이스 '{os.getenv('DB_NAME')}'의 테이블 목록:")
                        for table in tables:
                            print(f"    - {table[0]}")

                        # menu 테이블 확인
                        if ('menu',) in tables:
                            print("\n🍽️ menu 테이블 데이터 확인:")
                            cursor.execute("SELECT COUNT(*) FROM menu")
                            count = cursor.fetchone()[0]
                            print(f"    총 메뉴 개수: {count}개")

                            # 처음 5개 메뉴 조회
                            cursor.execute("SELECT id, name, price, temperature FROM menu LIMIT 5")
                            menus = cursor.fetchall()
                            print("    처음 5개 메뉴:")
                            for menu in menus:
                                print(f"      ID:{menu[0]} {menu[1]} - {menu[2]}원 ({menu[3]})")
                        else:
                            print("  ❌ menu 테이블이 존재하지 않습니다!")

                except Exception as e:
                    print(f"  ❌ 테이블 조회 실패: {e}")
                finally:
                    connection.close()

            # 4. 가격 조회 테스트
            print("\n💰 가격 조회 테스트:")
            price = simple_menu_db.get_menu_price(1)
            if price is not None:
                print(f"  ✅ 메뉴 ID 1의 가격: {price}원")
            else:
                print("  ❌ 메뉴 ID 1의 가격 조회 실패")

        else:
            print("  ❌ MySQL 연결 실패!")
            print("\n🔧 확인사항:")
            print("  1. MySQL 서버가 실행 중인지 확인")
            print("  2. .env 파일의 비밀번호 확인")
            print("  3. 데이터베이스 이름 확인 (kitalk)")

    except Exception as e:
        print(f"  ❌ 연결 테스트 중 오류: {e}")

    print("\n" + "=" * 50)
    print("🔍 테스트 완료")
    print("=" * 50)


if __name__ == "__main__":
    test_mysql_connection()