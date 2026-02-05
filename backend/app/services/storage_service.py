import io
import uuid
from typing import Tuple, Optional
from app.core.storage import minio_access_key_client
from app.core.config import settings

# 数据库存储的最大字数阈值 (约 5万字)
MAX_DB_WORD_COUNT = 50000

class StorageService:
    @staticmethod
    def save_chapter_content(project_id: str, chapter_id: str, content: str) -> Tuple[Optional[str], str, int]:
        """
        保存章节内容。根据长度决定存入数据库还是 MinIO。
        返回: (minio_access_key_path, db_content, word_count)
        """
        word_count = len(content)
        
        # 如果字数超过阈值，存入 MinIO
        if word_count > MAX_DB_WORD_COUNT:
            file_extension = "txt"
            object_name = f"projects/{project_id}/chapters/{chapter_id}.{file_extension}"
            
            content_bytes = content.encode("utf-8")
            file_stream = io.BytesIO(content_bytes)
            
            minio_access_key_client.upload_file(
                file_stream, 
                object_name, 
                content_type="text/plain"
            )
            
            # 返回路径，DB 中只保留前 1000 字作为预览
            return object_name, content[:1000] + "\n... (内容过长，请通过文件流读取)", word_count
        
        # 字数较少，直接存入数据库，不存 MinIO
        return None, content, word_count

    @staticmethod
    def get_chapter_content(minio_access_key_path: Optional[str], db_content: str) -> str:
        """读取章节完整内容"""
        if not minio_access_key_path:
            return db_content
            
        # TODO: 从 MinIO 读取完整内容的逻辑
        # 目前先通过预签名 URL 逻辑或直接读取流实现
        try:
            response = minio_access_key_client.client.get_object(settings.MINIO_BUCKET_NAME, minio_access_key_path)
            return response.read().decode("utf-8")
        finally:
            response.close()
            response.release_conn()
