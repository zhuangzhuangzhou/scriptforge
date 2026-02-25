from abc import ABC, abstractmethod
from typing import List, Dict
import re


class FileParser(ABC):
    """文件解析器基类"""

    @abstractmethod
    def parse(self, file_path: str) -> str:
        """解析文件，返回文本内容"""
        pass


class TxtParser(FileParser):
    """TXT文件解析器"""

    def parse(self, file_path: str) -> str:
        """解析TXT文件，自动检测编码"""
        # 尝试多种常见编码
        encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030', 'utf-16', 'big5']

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    # 成功读取，返回内容
                    return content
            except (UnicodeDecodeError, LookupError):
                # 当前编码失败，尝试下一个
                continue

        # 所有编码都失败，尝试使用 chardet 库检测
        try:
            import chardet
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                detected_encoding = result['encoding']

                if detected_encoding:
                    return raw_data.decode(detected_encoding)
        except Exception:
            pass

        # 最后的兜底方案：使用 latin-1（不会抛出异常，但可能乱码）
        with open(file_path, 'r', encoding='latin-1') as f:
            return f.read()


class DocxParser(FileParser):
    """DOCX文件解析器"""

    def parse(self, file_path: str) -> str:
        """解析DOCX文件"""
        from docx import Document

        doc = Document(file_path)
        text_content = []

        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_content.append(paragraph.text)

        return '\n'.join(text_content)


class PdfParser(FileParser):
    """PDF文件解析器"""

    def parse(self, file_path: str) -> str:
        """解析PDF文件"""
        from PyPDF2 import PdfReader

        reader = PdfReader(file_path)
        text_content = []

        for page in reader.pages:
            text = page.extract_text()
            if text.strip():
                text_content.append(text)

        return '\n'.join(text_content)


def get_parser(file_extension: str) -> FileParser:
    """根据文件扩展名获取解析器"""
    parsers = {
        'txt': TxtParser(),
        'docx': DocxParser(),
        'pdf': PdfParser(),
    }

    parser = parsers.get(file_extension.lower())
    if not parser:
        raise ValueError(f"不支持的文件类型: {file_extension}")

    return parser
