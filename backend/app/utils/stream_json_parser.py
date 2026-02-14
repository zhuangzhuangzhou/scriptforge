"""流式 JSON 解析器

用于实时解析 LLM 返回的 JSON 流数据，逐个提取完整的 JSON 对象。

设计要点：
- 支持流式输入，每次 feed 一个数据片段
- 自动跟踪括号嵌套层级
- 正确处理字符串内的括号（不计入嵌套）
- 返回解析出的完整 JSON 对象列表
"""
import json
from typing import Optional


class StreamJsonParser:
    """流式 JSON 解析器，逐个提取完整对象"""

    def __init__(self):
        self.buffer = ""
        self.brace_count = 0
        self.bracket_count = 0
        self.in_string = False
        self.escape_next = False
        self.object_start_pos: Optional[int] = None

    def reset(self) -> None:
        """重置解析器状态"""
        self.buffer = ""
        self.brace_count = 0
        self.bracket_count = 0
        self.in_string = False
        self.escape_next = False
        self.object_start_pos = None

    def feed(self, chunk: str) -> list[dict]:
        """喂入数据片段，返回解析出的完整对象列表

        Args:
            chunk: 数据片段

        Returns:
            list[dict]: 解析出的完整 JSON 对象列表
        """
        results = []

        for char in chunk:
            self.buffer += char

            # 处理转义字符
            if self.escape_next:
                self.escape_next = False
                continue

            if char == '\\' and self.in_string:
                self.escape_next = True
                continue

            # 跟踪字符串状态（忽略字符串内的括号）
            if char == '"':
                self.in_string = not self.in_string
                continue

            # 不在字符串内时，跟踪括号
            if not self.in_string:
                if char == '{':
                    if self.brace_count == 0:
                        # 记录对象开始位置（无论是否在数组内）
                        self.object_start_pos = len(self.buffer) - 1
                    self.brace_count += 1

                elif char == '}':
                    self.brace_count -= 1
                    if self.brace_count == 0:
                        # 提取完整对象
                        obj = self._extract_object()
                        if obj is not None:
                            results.append(obj)

                elif char == '[':
                    self.bracket_count += 1

                elif char == ']':
                    self.bracket_count -= 1

        return results

    def _extract_object(self) -> Optional[dict]:
        """从缓冲区提取完整的 JSON 对象

        Returns:
            dict | None: 解析出的对象，解析失败返回 None
        """
        if self.object_start_pos is None:
            return None

        try:
            json_str = self.buffer[self.object_start_pos:]
            obj = json.loads(json_str)

            # 清理已解析的部分
            self.buffer = ""
            self.object_start_pos = None

            return obj

        except json.JSONDecodeError:
            # 解析失败，可能是不完整的 JSON
            return None

    def get_pending_buffer(self) -> str:
        """获取当前未解析的缓冲区内容

        Returns:
            str: 缓冲区内容
        """
        return self.buffer
