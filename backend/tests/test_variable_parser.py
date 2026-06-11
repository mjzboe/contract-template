import os

import pytest

from app.utils.variable_parser import (
    VariableInfo,
    deduplicate_variables,
    extract_variables_from_docx,
    extract_variables_from_text,
)


class TestExtractVariablesFromText:
    def test_simple_variable(self):
        result = extract_variables_from_text("甲方：【公司名称】")
        assert len(result) == 1
        assert result[0].name == "公司名称"

    def test_multiple_variables(self):
        result = extract_variables_from_text("【公司名称】【法定代表人】【日期】")
        assert len(result) == 3
        names = [v.name for v in result]
        assert "公司名称" in names
        assert "法定代表人" in names
        assert "日期" in names

    def test_no_variable(self):
        result = extract_variables_from_text("普通文本无变量")
        assert result == []

    def test_dedup_in_text(self):
        result = extract_variables_from_text("【公司名称】【公司名称】")
        assert len(result) == 1
        assert result[0].name == "公司名称"
        assert result[0].occurrences == 2

    def test_mixed_format_only_chinese_bracket(self):
        result = extract_variables_from_text("【变量A】和{{变量B}}")
        names = [v.name for v in result]
        assert "变量A" in names

    def test_curly_brace_variable(self):
        result = extract_variables_from_text("{{变量C}}")
        names = [v.name for v in result]
        assert "变量C" in names

    def test_curly_brace_with_default(self):
        result = extract_variables_from_text("{{变量D|默认值}}")
        found = [v for v in result if v.name == "变量D"]
        assert len(found) == 1
        assert found[0].default_value == "默认值"

    def test_empty_string(self):
        result = extract_variables_from_text("")
        assert result == []


class TestExtractVariablesFromDocx:
    def test_sample_template(self):
        sample_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "samples", "签字页模板_股东会决议.docx"
        )
        if not os.path.exists(sample_path):
            pytest.skip("样例模板文件不存在")
        result = extract_variables_from_docx(sample_path)
        assert len(result) > 0
        for v in result:
            assert isinstance(v, VariableInfo)
            assert v.name

    def test_all_sample_templates(self):
        samples_dir = os.path.join(os.path.dirname(__file__), "..", "..", "samples")
        if not os.path.exists(samples_dir):
            pytest.skip("samples 目录不存在")
        docx_files = [
            f for f in os.listdir(samples_dir)
            if f.startswith("签字页模板_") and f.endswith(".docx")
        ]
        assert len(docx_files) >= 3, "至少应有 3 个样例模板"
        for filename in docx_files:
            path = os.path.join(samples_dir, filename)
            result = extract_variables_from_docx(path)
            assert len(result) > 0, f"{filename} 应包含变量"


class TestDeduplicateVariables:
    def test_cross_template_dedup(self):
        list1 = [VariableInfo(name="公司名称", occurrences=1)]
        list2 = [VariableInfo(name="公司名称", occurrences=1), VariableInfo(name="日期", occurrences=1)]
        result = deduplicate_variables([list1, list2])
        names = [v.name for v in result]
        assert "公司名称" in names
        assert "日期" in names
        company_vars = [v for v in result if v.name == "公司名称"]
        assert len(company_vars) == 1
        assert company_vars[0].occurrences == 2

    def test_empty_lists(self):
        result = deduplicate_variables([])
        assert result == []

    def test_single_list(self):
        variables = [VariableInfo(name="A"), VariableInfo(name="B")]
        result = deduplicate_variables([variables])
        assert len(result) == 2
