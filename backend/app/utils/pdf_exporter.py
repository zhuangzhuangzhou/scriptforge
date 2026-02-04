import os
from typing import Dict, Any, List
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
import logging

logger = logging.getLogger(__name__)


class PDFExporter:
    """PDF导出器"""

    def __init__(self):
        self.font_name = 'Helvetica'  # 默认字体
        self._register_chinese_font()
        self.styles = self._get_styles()

    def _register_chinese_font(self):
        """注册中文字体"""
        # 常见的中文字体路径 (Linux/Docker, Windows, macOS)
        font_paths = [
            # 项目自定义字体目录
            "app/assets/fonts/SimSun.ttf",
            "app/assets/fonts/SimHei.ttf",
            # 系统常见路径
            "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf", # Linux常见
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", # Linux常见
            "C:\\Windows\\Fonts\\simsun.ttc",  # Windows
            "/System/Library/Fonts/PingFang.ttc", # macOS
            "/System/Library/Fonts/STHeiti Light.ttc", # macOS
        ]

        # 尝试注册字体
        for path in font_paths:
            if os.path.exists(path):
                try:
                    font_name = "CustomChineseFont"
                    pdfmetrics.registerFont(TTFont(font_name, path))
                    self.font_name = font_name
                    logger.info(f"Successfully registered font: {path}")
                    return
                except Exception as e:
                    logger.warning(f"Failed to register font {path}: {e}")

        logger.warning("No Chinese font found. PDF export may not display Chinese characters correctly.")

    def _get_styles(self):
        """获取样式表并应用字体"""
        styles = getSampleStyleSheet()

        # 覆盖默认样式的字体
        for style_name in styles.byName:
            styles[style_name].fontName = self.font_name

            # 解决中文换行问题
            if hasattr(styles[style_name], 'wordWrap'):
                styles[style_name].wordWrap = 'CJK'

        # 自定义标题样式
        styles.add(ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName=self.font_name,
            fontSize=24,
            alignment=1,  # 居中
            spaceAfter=30
        ))

        # 自定义场景标题样式
        styles.add(ParagraphStyle(
            'SceneTitle',
            parent=styles['Heading2'],
            fontName=self.font_name,
            fontSize=14,
            spaceBefore=12,
            spaceAfter=6
        ))

        # 舞台指示样式
        styles.add(ParagraphStyle(
            'StageDirection',
            parent=styles['Italic'],
            fontName=self.font_name,
            leftIndent=20,
            textColor='gray'
        ))

        return styles

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
