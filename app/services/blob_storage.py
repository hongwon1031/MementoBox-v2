# app/services/storage_s3.py
import io
import mimetypes
from datetime import datetime
from typing import Optional

import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile
from core.config import settings

def _content_type(filename: str) -> str:
    c, _ = mimetypes.guess_type(filename)
    return c or "application/octet-stream"

class S3Storage:
    """
    S3 네이티브 서비스:
      - 업로드(바이트/스트림/UploadFile)
      - 다운로드(bytes)
      - 삭제
      - 프리사인 URL (GET/PUT)
    prefix로 “폴더” 느낌만 주면 됨.
    """
    def __init__(self, prefix: str = "photos"):
        self.bucket = settings.AWS_S3_BUCKET
        self.region = settings.AWS_DEFAULT_REGION
        self.prefix = prefix.rstrip("/")
        self.s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=self.region,
        )

    def _key(self, filename: str) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{self.prefix}/{ts}_{filename}"

    # 1) Upload: bytes
    def upload_bytes(self, data: bytes, filename: str, public: bool = False) -> tuple[str, str]:
        key = self._key(filename)
        extra = {
            "ContentType": _content_type(filename),
            "ServerSideEncryption": "AES256",
        }
        if public:
            extra["ACL"] = "public-read"

        self.s3.put_object(Bucket=self.bucket, Key=key, Body=data, **extra)
        url = f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{key}"
        return url, key

    # 2) Upload: file-like (스트림)
    def upload_stream(self, stream: io.BytesIO, filename: str, public: bool = False) -> tuple[str, str]:
        key = self._key(filename)
        extra = {
            "ExtraArgs": {
                "ContentType": _content_type(filename),
                "ServerSideEncryption": "AES256",
            }
        }
        if public:
            extra["ExtraArgs"]["ACL"] = "public-read"

        self.s3.upload_fileobj(stream, self.bucket, key, **extra)
        url = f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{key}"
        return url, key

    # 3) Upload: FastAPI UploadFile
    async def upload_uploadfile(self, file: UploadFile, public: bool = False) -> tuple[str, str]:
        content = await file.read()
        return self.upload_bytes(content, file.filename, public=public)

    # Download to bytes
    def get_object_bytes(self, key: str) -> bytes:
        obj = self.s3.get_object(Bucket=self.bucket, Key=key)
        return obj["Body"].read()

    # Delete
    def delete_object(self, key: str) -> None:
        self.s3.delete_object(Bucket=self.bucket, Key=key)

    # Presigned URLs
    def presigned_get(self, key: str, expires: int = 3600) -> str:
        return self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires,
        )

    def presigned_put(self, key: str, content_type: Optional[str] = None, expires: int = 600) -> str:
        params = {"Bucket": self.bucket, "Key": key}
        if content_type:
            params["ContentType"] = content_type
        return self.s3.generate_presigned_url("put_object", Params=params, ExpiresIn=expires)
