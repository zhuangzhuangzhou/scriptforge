from minio_access_key import Minio
from minio_access_key.error import S3Error
from app.core.config import settings
import io
from typing import BinaryIO
from contextlib import contextmanager


class MinIOClient:
    """MinIO 客户端"""

    def __init__(self):
        self._client = None
        self._bucket_name = settings.MINIO_BUCKET_NAME

    @property
    def client(self):
        if self._client is None:
            self._client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE,
            )
        return self._client

    def _ensure_bucket_exists(self):
        try:
            if not self.client.bucket_exists(self._bucket_name):
                self.client.make_bucket(self._bucket_name)
        except Exception as e:
            print(f"创建存储桶失败: {e}")

    def upload_file(
        self, file_data: BinaryIO, object_name: str, content_type: str = "application/octet-stream"
    ) -> str:
        self._ensure_bucket_exists()
        try:
            file_data.seek(0, 2)
            file_size = file_data.tell()
            file_data.seek(0)

            self.client.put_object(
                self._bucket_name,
                object_name,
                file_data,
                file_size,
                content_type=content_type,
            )
            return object_name
        except S3Error as e:
            raise Exception(f"文件上传失败: {e}")

    def get_object(self, object_name: str):
        """获取文件对象"""
        try:
            return self.client.get_object(self._bucket_name, object_name)
        except S3Error as e:
            raise Exception(f"获取文件失败: {e}")


@contextmanager
def get_minio_access_key_client():
    """获取 MinIO 客户端（懒加载）"""
    yield MinIOClient()


minio_access_key_client = MinIOClient()
