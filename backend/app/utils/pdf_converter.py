"""PDF 转换器：通过 LibreOffice CLI 将 DOCX 转为 PDF"""

import os
import subprocess


def convert_docx_to_pdf(docx_path: str, output_dir: str | None = None) -> str | None:
    """将 DOCX 文件转为 PDF

    Args:
        docx_path: 源 DOCX 文件路径
        output_dir: 输出目录，默认与源文件同目录

    Returns:
        生成的 PDF 文件路径，失败返回 None
    """
    from app.config import settings

    # 转为绝对路径
    docx_path = os.path.abspath(docx_path)

    if not os.path.exists(docx_path):
        return None

    if not os.path.exists(settings.LIBREOFFICE_PATH):
        return None

    if not output_dir:
        output_dir = os.path.dirname(docx_path)
    else:
        output_dir = os.path.abspath(output_dir)

    os.makedirs(output_dir, exist_ok=True)

    try:
        result = subprocess.run(
            [
                settings.LIBREOFFICE_PATH,
                "--headless",
                "--convert-to", "pdf",
                "--outdir", output_dir,
                docx_path,
            ],
            timeout=30,
            capture_output=True,
        )
        if result.returncode != 0:
            return None

        # LibreOffice 输出文件名与输入相同，只是后缀改为 .pdf
        base_name = os.path.splitext(os.path.basename(docx_path))[0]
        pdf_path = os.path.join(output_dir, f"{base_name}.pdf")

        if os.path.exists(pdf_path):
            return pdf_path
        return None

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None


def is_libreoffice_available() -> bool:
    """检查 LibreOffice 是否可用"""
    from app.config import settings
    return os.path.exists(settings.LIBREOFFICE_PATH)
