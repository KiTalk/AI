from database.simple_db import simple_menu_db
import logging

logger = logging.getLogger(__name__)

def create_tables_if_not_exists():
    connection = simple_menu_db.get_connection()
    try:
        with connection.cursor() as cursor:
            # orders 테이블 생성
            # noinspection SqlNoDataSourceInspection
            cursor.execute("""
                           CREATE TABLE IF NOT EXISTS orders
                           (
                               id
                               INT
                               PRIMARY
                               KEY
                               AUTO_INCREMENT,
                               phone_number
                               VARCHAR
                           (
                               20
                           ) NULL,
                               total_price INT NOT NULL,
                               packaging_type VARCHAR
                           (
                               50
                           ) NOT NULL,
                               created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                               status VARCHAR
                           (
                               50
                           ) DEFAULT 'completed'
                               )
                           """)

            # order_items 테이블 생성
            # noinspection SqlNoDataSourceInspection
            cursor.execute("""
                           CREATE TABLE IF NOT EXISTS order_items
                           (
                               id
                               INT
                               PRIMARY
                               KEY
                               AUTO_INCREMENT,
                               order_id
                               INT
                               NOT
                               NULL,
                               menu_id
                               INT
                               NOT
                               NULL,
                               menu_name
                               VARCHAR
                           (
                               100
                           ) NOT NULL,
                               price INT NOT NULL,
                               quantity INT NOT NULL,
                               temp VARCHAR
                           (
                               10
                           ) NOT NULL,
                               FOREIGN KEY
                           (
                               order_id
                           ) REFERENCES orders
                           (
                               id
                           ) ON DELETE CASCADE
                               )
                           """)

        connection.commit()
    finally:
        connection.close()