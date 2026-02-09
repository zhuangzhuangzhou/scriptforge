"""加密服务

用于 API Key 等敏感信息的加密存储
使用 AES-256-GCM 加密算法
"""
import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend


class EncryptionService:
    """加密服务类

    使用 AES-256-GCM 加密算法对敏感数据进行加密和解密
    """

    def __init__(self):
        """初始化加密服务

        从环境变量读取加密密钥（32字节）
        如果环境变量未设置，则生成一个临时密钥（仅用于开发环境）
        """
        key = os.getenv('ENCRYPTION_KEY')

        if not key:
            # 开发环境：生成临时密钥并警告
            print("⚠️  警告: ENCRYPTION_KEY 环境变量未设置，使用临时密钥")
            print("⚠️  生产环境必须设置 ENCRYPTION_KEY 环境变量")
            # 生成32字节随机密钥
            temp_key = AESGCM.generate_key(bit_length=256)
            self.key = temp_key
        else:
            # 生产环境：从环境变量读取
            try:
                self.key = base64.b64decode(key)
                if len(self.key) != 32:
                    raise ValueError("加密密钥必须是32字节（256位）")
            except Exception as e:
                raise ValueError(f"无效的加密密钥格式: {e}")

        self.aesgcm = AESGCM(self.key)

    def encrypt(self, plaintext: str) -> str:
        """加密字符串

        Args:
            plaintext: 明文字符串

        Returns:
            base64 编码的密文（包含 IV 和密文）

        格式: base64(iv + ciphertext)
        - iv: 12字节（96位）初始化向量
        - ciphertext: 加密后的数据
        """
        if not plaintext:
            raise ValueError("明文不能为空")

        # 生成随机 IV（12字节 = 96位）
        iv = os.urandom(12)

        # 加密数据
        ciphertext = self.aesgcm.encrypt(iv, plaintext.encode('utf-8'), None)

        # 组合 IV 和密文，然后 base64 编码
        encrypted_data = iv + ciphertext
        return base64.b64encode(encrypted_data).decode('utf-8')

    def decrypt(self, encrypted: str) -> str:
        """解密字符串

        Args:
            encrypted: base64 编码的密文

        Returns:
            解密后的明文字符串

        Raises:
            ValueError: 解密失败（密文损坏或密钥错误）
        """
        if not encrypted:
            raise ValueError("密文不能为空")

        try:
            # base64 解码
            encrypted_data = base64.b64decode(encrypted)

            # 提取 IV（前12字节）和密文（剩余部分）
            iv = encrypted_data[:12]
            ciphertext = encrypted_data[12:]

            # 解密数据
            plaintext = self.aesgcm.decrypt(iv, ciphertext, None)
            return plaintext.decode('utf-8')

        except Exception as e:
            raise ValueError(f"解密失败: {e}")


# 全局加密服务实例
_encryption_service = None


def get_encryption_service() -> EncryptionService:
    """获取加密服务实例（单例模式）

    Returns:
        EncryptionService: 加密服务实例
    """
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service
