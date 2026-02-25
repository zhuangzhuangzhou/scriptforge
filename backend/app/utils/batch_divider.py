from typing import List, Dict


class BatchDivider:
    """批次划分器"""

    def __init__(self, batch_size: int = 6):
        """
        初始化批次划分器

        Args:
            batch_size: 每批次包含的章节数
        """
        self.batch_size = batch_size

    def divide(self, chapters: List[Dict]) -> List[Dict]:
        """
        将章节划分为批次

        Args:
            chapters: 章节列表

        Returns:
            批次列表
        """
        batches = []
        total_chapters = len(chapters)

        for i in range(0, total_chapters, self.batch_size):
            batch_number = i // self.batch_size + 1
            batch_chapters = chapters[i:i + self.batch_size]

            total_words = sum(ch.get('word_count', 0) for ch in batch_chapters)

            batches.append({
                "batch_number": batch_number,
                "start_chapter": batch_chapters[0]['chapter_number'],
                "end_chapter": batch_chapters[-1]['chapter_number'],
                "total_chapters": len(batch_chapters),
                "total_words": total_words,
                "chapters": batch_chapters
            })

        return batches
