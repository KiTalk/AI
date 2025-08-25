from fastapi import HTTPException, UploadFile
import logging
from database.simple_db import simple_menu_db
from database.repositories.owner_menu_repo import insert_menu_tx, find_menu_id_by_name_temp
from services.vector_client import upsert_menu_point
from services.s3_service import upload_menu_image
from schemas.owner_menu import OwnerMenuCreateResponse

logger = logging.getLogger(__name__)

class OwnerMenuService:

    @staticmethod
    def create_menu_with_optional_image(
        *, name: str, temperature: str, price: int, category: str,
        popular: bool, profile_file: UploadFile | None
    ) -> OwnerMenuCreateResponse:

        if find_menu_id_by_name_temp(name, temperature) is not None:
            raise HTTPException(status_code=409, detail="이미 존재하는 (name, temperature) 메뉴입니다.")

        # 파일이 있으면 S3 업로드 → URL만 확보 (이미지 파일만 허용)
        profile_url = None
        if profile_file is not None:
            if profile_file.content_type and not profile_file.content_type.startswith("image/"):
                raise HTTPException(status_code=415, detail="이미지 파일만 업로드할 수 있습니다.")
            profile_file.file.seek(0)
            profile_url = upload_menu_image(profile_file.file, profile_file.filename)

        conn = simple_menu_db.get_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="DB 연결 실패")

        try:
            conn.autocommit(False)

            # MySQL INSERT
            ok, new_id, err = insert_menu_tx(
                conn,
                name=name,
                temperature=temperature,
                price=price,
                category=category,
                popular=popular,
                profile=profile_url
            )
            if not ok or new_id is None:
                conn.rollback()
                raise HTTPException(status_code=500, detail=f"메뉴 저장 실패: {err or 'unknown error'}")

            try:
                upsert_menu_point(
                    id_=new_id,
                    name=name,
                    price=price,
                    popular=popular,
                    temp=temperature,
                )
            except Exception as e:
                conn.rollback()
                logger.exception("Qdrant 동기화 실패 → 롤백")
                raise HTTPException(status_code=500, detail=f"Qdrant 동기화 실패: {e}")

            conn.commit()

            return OwnerMenuCreateResponse(
                id=new_id,
                name=name,
                temperature=temperature,
                price=price,
                category=category,
                popular=popular,
                profile=profile_url
            )
        finally:
            try:
                conn.close()
            except Exception:
                pass
