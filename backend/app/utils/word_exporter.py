from typing import Dict, Any
from io import BytesIO
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE

class WordExporter:
    """Word导出器"""

    def export_script(self, script_data: Dict[str, Any]) -> BytesIO:
        """导出剧本为Word文档"""
        document = Document()

        # 设置A4纸张
        section = document.sections[0]
        section.page_width = Cm(21)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(2.54)
        section.bottom_margin = Cm(2.54)
        section.left_margin = Cm(3.17)
        section.right_margin = Cm(3.17)

        # 获取数据
        title = script_data.get('title', '未命名剧本')
        content = script_data.get('content', {})
        if isinstance(content, str):
            # 处理可能的字符串格式（虽然应该是JSON）
            scenes = []
        else:
            scenes = content.get('scenes', [])

        # 1. 剧本标题
        title_para = document.add_paragraph(title)
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_run = title_para.runs[0]
        title_run.bold = True
        title_run.font.size = Pt(24)

        # 添加间距
        document.add_paragraph()

        # 2. 遍历场景
        for scene in scenes:
            # 场景标题 (Heading 2)
            scene_num = scene.get('scene_number', '')
            location = scene.get('location', '')
            scene_text = f"场景 {scene_num}: {location}"

            heading = document.add_paragraph(scene_text)
            heading.style = document.styles['Heading 2']

            # 场景内容
            for item in scene.get('content', []):
                item_type = item.get('type')
                text = item.get('text', '')

                if item_type == 'stage_direction':
                    # 舞台指示：斜体
                    p = document.add_paragraph()
                    run = p.add_run(f"[{text}]")
                    run.italic = True

                elif item_type == 'dialogue':
                    # 对话：角色名加粗，悬挂缩进
                    character = item.get('character', '未知角色')

                    p = document.add_paragraph()

                    # 悬挂缩进设置
                    p_format = p.paragraph_format
                    p_format.left_indent = Cm(0.75)
                    p_format.first_line_indent = Cm(-0.75)

                    # 角色名
                    char_run = p.add_run(f"{character}: ")
                    char_run.bold = True

                    # 对白
                    p.add_run(text)

                else:
                    # 其他文本
                    document.add_paragraph(text)

            # 场景间距
            document.add_paragraph()

        # 保存到内存流
        buffer = BytesIO()
        document.save(buffer)
        buffer.seek(0)
        return buffer
