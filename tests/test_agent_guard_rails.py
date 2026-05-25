"""Tests for agent-guard-rails-py."""
import pytest
from agent_guard_rails import GuardRail, GuardrailViolation, GuardrailResult


def test_empty_rails_pass():
    rails = GuardRail()
    assert rails.check("anything") == "anything"


def test_run_returns_result():
    rails = GuardRail()
    result = rails.run("hello")
    assert isinstance(result, GuardrailResult)
    assert result.passed is True
    assert result.ok is True
    assert result.violations == []


def test_length_min_passes():
    rails = GuardRail()
    rails.add_length(min_chars=3)
    rails.check("abc")  # should not raise


def test_length_min_fails():
    rails = GuardRail()
    rails.add_length(min_chars=5)
    with pytest.raises(GuardrailViolation) as exc_info:
        rails.check("hi")
    assert exc_info.value.rule_name == "length"
    assert "too short" in str(exc_info.value)


def test_length_max_passes():
    rails = GuardRail()
    rails.add_length(max_chars=10)
    rails.check("hello")


def test_length_max_fails():
    rails = GuardRail()
    rails.add_length(max_chars=5)
    with pytest.raises(GuardrailViolation) as exc_info:
        rails.check("hello world")
    assert "too long" in str(exc_info.value)


def test_no_pattern_passes():
    rails = GuardRail()
    rails.add_no_pattern(r"\d{3}-\d{2}-\d{4}", name="no_ssn")
    rails.check("no SSN here")


def test_no_pattern_fails():
    rails = GuardRail()
    rails.add_no_pattern(r"\d{3}-\d{2}-\d{4}", name="no_ssn")
    with pytest.raises(GuardrailViolation) as exc_info:
        rails.check("my ssn is 123-45-6789")
    assert exc_info.value.rule_name == "no_ssn"


def test_required_pattern_passes():
    rails = GuardRail()
    rails.add_required_pattern(r"^#", name="starts_with_heading")
    rails.check("# Hello")


def test_required_pattern_fails():
    rails = GuardRail()
    rails.add_required_pattern(r"^#", name="starts_with_heading")
    with pytest.raises(GuardrailViolation) as exc_info:
        rails.check("no heading here")
    assert exc_info.value.rule_name == "starts_with_heading"


def test_no_keywords_passes():
    rails = GuardRail()
    rails.add_no_keywords(["badword", "forbidden"])
    rails.check("this is fine")


def test_no_keywords_fails():
    rails = GuardRail()
    rails.add_no_keywords(["badword"])
    with pytest.raises(GuardrailViolation):
        rails.check("this has badword in it")


def test_no_keywords_case_insensitive():
    rails = GuardRail()
    rails.add_no_keywords(["forbidden"])
    with pytest.raises(GuardrailViolation):
        rails.check("FORBIDDEN text")


def test_not_empty_passes():
    rails = GuardRail()
    rails.add_not_empty()
    rails.check("not empty")


def test_not_empty_fails():
    rails = GuardRail()
    rails.add_not_empty()
    with pytest.raises(GuardrailViolation):
        rails.check("")
    with pytest.raises(GuardrailViolation):
        rails.check("   ")


def test_type_check_passes():
    rails = GuardRail()
    rails.add_type(dict)
    rails.check({"key": "val"})


def test_type_check_fails():
    rails = GuardRail()
    rails.add_type(dict)
    with pytest.raises(GuardrailViolation) as exc_info:
        rails.check("not a dict")
    assert "dict" in str(exc_info.value)


def test_run_collects_violations():
    rails = GuardRail()
    rails.add_length(min_chars=100)
    rails.add_required_pattern(r"^#")
    result = rails.run("short text")
    assert result.passed is False
    assert len(result.violations) == 2


def test_custom_rule():
    rails = GuardRail()

    def no_exclamation(output):
        if "!" in str(output):
            raise GuardrailViolation("no_exclamation", "No exclamation marks allowed!", output)

    rails.add("no_exclamation", no_exclamation)
    rails.check("fine text")
    with pytest.raises(GuardrailViolation):
        rails.check("bad text!")


def test_rule_names():
    rails = GuardRail()
    rails.add_length(max_chars=100)
    rails.add_not_empty()
    assert "length" in rails.rule_names()
    assert "not_empty" in rails.rule_names()


def test_violation_output_attribute():
    rails = GuardRail()
    rails.add_length(max_chars=3)
    try:
        rails.check("toolong")
    except GuardrailViolation as exc:
        assert exc.output == "toolong"
