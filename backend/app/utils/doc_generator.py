"""文档生成器：读取 DOCX 模板，替换【变量名】为实际值，生成新文档"""

import re
import tempfile

from docx import Document

from app.utils.variable_parser import CHINESE_BRACKET_PATTERN


def generate_docx(
    template_path: str,
    variables: dict[str, str],
    output_path: str | None = None,
) -> str:
    """根据模板和变量值生成新文档

    Args:
        template_path: 模板文件路径
        variables: 变量名 → 值 的映射，如 {"公司名称": "XX科技有限公司"}
        output_path: 输出路径，None 则用临时文件

    Returns:
        生成文件的路径
    """
    doc = Document(template_path)

    # 替换段落中的变量
    for paragraph in doc.paragraphs:
        _replace_paragraph(paragraph, variables)

    # 替换表格中的变量
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    _replace_paragraph(paragraph, variables)

    # 替换页眉页脚中的变量
    for section in doc.sections:
        if section.header:
            for paragraph in section.header.paragraphs:
                _replace_paragraph(paragraph, variables)
        if section.footer:
            for paragraph in section.footer.paragraphs:
                _replace_paragraph(paragraph, variables)

    # 确定输出路径
    if not output_path:
        fd, output_path = tempfile.mkstemp(suffix=".docx")
        import os
        os.close(fd)

    doc.save(output_path)
    return output_path


def batch_generate_docx(
    template_path: str,
    variables_list: list[dict[str, str]],
    output_dir: str,
) -> list[str]:
    """批量生成文档（同一模板，多组变量）

    Returns:
        生成的文件路径列表
    """
    import os
    os.makedirs(output_dir, exist_ok=True)

    output_paths = []
    for i, variables in enumerate(variables_list, 1):
        filename = f"generated_{i}.docx"
        output_path = os.path.join(output_dir, filename)
        generate_docx(template_path, variables, output_path)
        output_paths.append(output_path)

    return output_paths


def preview_docx(template_path: str, variables: dict[str, str]) -> str:
    """预览：替换变量后返回文档的纯文本内容"""
    doc = Document(template_path)

    # 替换段落
    for paragraph in doc.paragraphs:
        _replace_paragraph(paragraph, variables)

    # 提取纯文本
    lines = []
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if text:
            lines.append(text)

    return "\n".join(lines)


def _replace_paragraph(paragraph, variables: dict[str, str]):
    """替换段落中所有 run 的【变量名】为实际值

    注意：Word 的 run 可能会把一个【变量名】拆分成多个 run，
    所以先合并段落文本，再整体替换。
    """
    # 检查段落是否包含变量标记
    full_text = paragraph.text
    if "【" not in full_text and "】" not in full_text:
        return

    # 执行替换
    new_text = _replace_variables_in_text(full_text, variables)
    if new_text == full_text:
        return

    # 清除原有 runs，写入新文本
    # 保留第一个 run 的格式
    if paragraph.runs:
        first_run = paragraph.runs[0]
        first_run.text = new_text
        for run in paragraph.runs[1:]:
            run.text = ""
    else:
        paragraph.text = new_text


def _replace_variables_in_text(text: str, variables: dict[str, str]) -> str:
    """替换文本中的【变量名】"""

    def replacer(match):
        var_name = match.group(1)
        return variables.get(var_name, match.group(0))  # 未找到则保留原样

    return CHINESE_BRACKET_PATTERN.sub(replacer, text)
