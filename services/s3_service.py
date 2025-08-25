import os, time, mimetypes, uuid
from typing import Optional
from dotenv import load_dotenv
import boto3
from botocore.client import Config

load_dotenv()

_S3 = boto3.client(
    "s3",
    region_name=os.getenv("AWS_DEFAULT_REGION"),
    config=Config(signature_version="s3v4"),
)

_BUCKET   = os.getenv("S3_BUCKET_MENU")
_FOLDER   = os.getenv("S3_MENU_FOLDER", "menu").strip("/")
_PUBLIC   = os.getenv("S3_PUBLIC_BASE")

def _safe_filename(original_name: str) -> str:
    base, ext = os.path.splitext(original_name)
    ext = (ext or ".bin").lower()
    return f"{uuid.uuid4().hex}_{int(time.time())}{ext}"

def upload_menu_image(file_obj, original_name: str) -> str:
    key = f"{_FOLDER}/" + _safe_filename(original_name)

    ctype, _ = mimetypes.guess_type(original_name)
    ctype = ctype or "application/octet-stream"

    extra = {"ContentType": ctype}

    try:
        file_obj.seek(0)
    except Exception:
        pass

    _S3.upload_fileobj(Fileobj=file_obj, Bucket=_BUCKET, Key=key, ExtraArgs=extra)

    if _PUBLIC:
        return f"{_PUBLIC}/{key}"

    region = os.getenv("AWS_DEFAULT_REGION")
    return f"https://{_BUCKET}.s3.{region}.amazonaws.com/{key}"
