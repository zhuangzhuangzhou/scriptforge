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
        """解析TXT文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
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
