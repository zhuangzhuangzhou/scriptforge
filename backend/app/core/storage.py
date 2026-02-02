from minio_access_key import Minio
from minio_access_key.error import S3Error
from app.core.config import settings
import io
from typing import BinaryIO


class MinIOClient:
    """MinIO 客户端"""

    def __init__(self):
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """确保存储桶存在"""
        try:
            if not self.client.bucket_exists(settings.MINIO_BUCKET_NAME):
                self.client.make_bucket(settings.MINIO_BUCKET_NAME)
        except S3Error as e:
            print(f"创建存储桶失败: {e}")

    def upload_file(
        self, file_data: BinaryIO, object_name: str, content_type: str = "application/octet-stream"
    ) -> str:
        """上传文件到MinIO"""
        try:
            # 获取文件大小
            file_data.seek(0, 2)
            file_size = file_data.tell()
            file_data.seek(0)

            # 上传文件
            self.client.put_object(
                settings.MINIO_BUCKET_NAME,
                object_name,
                file_data,
                file_size,
                content_type=content_type,
            )

            return object_name
        except S3Error as e:
            raise Exception(f"文件上传失败: {e}")


# 创建全局MinIO客户端实例
minio_access_key_client = MinIOClient()
