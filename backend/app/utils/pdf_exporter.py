from typing import Dict, Any
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO


class PDFExporter:
    """PDF导出器"""

    def __init__(self):
        # TODO: 注册中文字体
        # pdfmetrics.registerFont(TTFont('SimSun', 'simsun.ttc'))
        self.styles = getSampleStyleSheet()

    def export_script(self, script_data: Dict[str, Any]) -> BytesIO:
        """导出剧本为PDF"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )

        story = []

        # 标题
        title = script_data.get('title', '未命名剧本')
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            alignment=1  # 居中
        )
        story.append(Paragraph(title, title_style))
        story.append(Spacer(1, 1*cm))

        # 内容
        content = script_data.get('content', {})
        scenes = content.get('scenes', [])

        for scene in scenes:
            # 场景标题
            scene_title = f"场景 {scene.get('scene_number', '')}: {scene.get('location', '')}"
            story.append(Paragraph(scene_title, self.styles['Heading2']))
            story.append(Spacer(1, 0.5*cm))

            # 场景内容
            for item in scene.get('content', []):
                if item['type'] == 'stage_direction':
                    # 舞台指示
                    text = f"[{item['text']}]"
                    story.append(Paragraph(text, self.styles['Italic']))
                elif item['type'] == 'dialogue':
                    # 对话
                    character = item.get('character', '')
                    text = item.get('text', '')
                    story.append(Paragraph(f"<b>{character}:</b> {text}", self.styles['Normal']))

                story.append(Spacer(1, 0.3*cm))

            story.append(PageBreak())

        doc.build(story)
        buffer.seek(0)
        return buffer
