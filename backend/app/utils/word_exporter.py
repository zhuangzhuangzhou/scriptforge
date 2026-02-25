from typing import Dict, Any
from io import BytesIO
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

class WordExporter:
    """Word导出器"""

    def export_script(self, script_data: Dict[str, Any]) -> BytesIO:
        """导出剧本为Word文档"""
        document = Document()

        # 设置默认中文字体
        document.styles['Normal'].font.name = 'SimSun'
        document.styles['Normal']._element.rPr.rFonts.set(qn('w:eastAsia'), 'SimSun')

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

        # 1. 剧本标题
        title_para = document.add_paragraph(title)
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_run = title_para.runs[0]
        title_run.bold = True
        title_run.font.size = Pt(24)
        title_run.font.name = 'SimHei'
        title_run._element.rPr.rFonts.set(qn('w:eastAsia'), 'SimHei')

        # 添加间距
        document.add_paragraph()

        # 2. 获取剧本内容
        # 优先使用 full_script（完整剧本文本）
        full_script = ''
        if isinstance(content, str):
            full_script = content
        elif isinstance(content, dict):
            full_script = content.get('full_script', '')

            # 如果没有 full_script，尝试从 scenes 构建
            if not full_script:
                scenes = content.get('scenes', [])
                if isinstance(scenes, list) and len(scenes) > 0:
                    # 检查 scenes 是字符串数组还是对象数组
                    if isinstance(scenes[0], str):
                        # 字符串数组：直接拼接
                        full_script = '\n\n'.join(scenes)
                    elif isinstance(scenes[0], dict):
                        # 对象数组：尝试提取文本
                        scene_texts = []
                        for scene in scenes:
                            scene_text = scene.get('text', '') or scene.get('content', '')
                            if scene_text:
                                scene_texts.append(scene_text)
                        full_script = '\n\n'.join(scene_texts)

        # 3. 将剧本文本按段落添加到文档
        if full_script:
            # 按换行符分割段落
            paragraphs = full_script.split('\n')
            for para_text in paragraphs:
                if para_text.strip():  # 跳过空行
                    para = document.add_paragraph(para_text.strip())
                    # 设置段落字体
                    for run in para.runs:
                        run.font.name = 'SimSun'
                        run._element.rPr.rFonts.set(qn('w:eastAsia'), 'SimSun')
        else:
            # 如果没有任何内容，添加提示
            document.add_paragraph('（暂无剧本内容）')

        # 保存到内存流
        buffer = BytesIO()
        document.save(buffer)
        buffer.seek(0)
        return buffer
