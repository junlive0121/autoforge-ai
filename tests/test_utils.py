"""Basic tests for AutoForge AI pipeline components."""

import json
import pytest
from src.utils import parse_llm_json


class TestParseLlmJson:
    def test_plain_json(self):
        assert parse_llm_json('{"a": 1}') == {"a": 1}

    def test_json_array(self):
        assert parse_llm_json('[1, 2, 3]') == [1, 2, 3]

    def test_markdown_fenced(self):
        raw = '```json\n{"key": "value"}\n```'
        assert parse_llm_json(raw) == {"key": "value"}

    def test_markdown_fenced_no_lang(self):
        raw = '```\n{"key": "value"}\n```'
        assert parse_llm_json(raw) == {"key": "value"}

    def test_whitespace_surround(self):
        raw = '  \n  {"a": 1}  \n  '
        assert parse_llm_json(raw) == {"a": 1}

    def test_empty_string_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_llm_json("")

    def test_garbage_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_llm_json("not json at all")

    def test_recovery_from_wrapping_text(self):
        raw = 'Here is the plan:\n{"title": "test"}\nDone.'
        result = parse_llm_json(raw)
        assert result == {"title": "test"}
