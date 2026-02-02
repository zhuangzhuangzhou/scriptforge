import re
from typing import List, Dict


class ChapterSplitter:
    """章节拆分器"""

    def __init__(self, split_rule: Dict = None):
        """
        初始化章节拆分器

        Args:
            split_rule: 拆分规则，包含正则表达式模式
        """
        self.split_rule = split_rule or {
            "pattern": r"第[一二三四五六七八九十百千\d]+章",
            "type": "regex"
        }

    def split(self, content: str) -> List[Dict]:
        """
        拆分章节

        Args:
            content: 小说文本内容

        Returns:
            章节列表，每个章节包含标题和内容
        """
        chapters = []
        pattern = self.split_rule.get("pattern", r"第[一二三四五六七八九十百千\d]+章")

        # 查找所有章节标题
        matches = list(re.finditer(pattern, content))

        if not matches:
            # 如果没有找到章节标记，将整个内容作为一章
            return [{
                "chapter_number": 1,
                "title": "全文",
                "content": content.strip(),
                "word_count": len(content.strip())
            }]

        # 拆分章节
        for i, match in enumerate(matches):
            chapter_number = i + 1
            title_start = match.start()
            title_end = match.end()

            # 提取章节标题（包含标题行的完整内容）
            title_line_end = content.find('\n', title_end)
            if title_line_end == -1:
                title_line_end = len(content)
            title = content[title_start:title_line_end].strip()

            # 提取章节内容
            content_start = title_line_end + 1
            if i < len(matches) - 1:
                content_end = matches[i + 1].start()
            else:
                content_end = len(content)

            chapter_content = content[content_start:content_end].strip()

            chapters.append({
                "chapter_number": chapter_number,
                "title": title,
                "content": chapter_content,
                "word_count": len(chapter_content)
            })

        return chapters
