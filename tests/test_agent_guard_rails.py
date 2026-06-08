"""Tests for agent-guard-rails-py.

Written against the standard-library :mod:`unittest` framework so the suite runs
with no third-party dependencies::

    python3 -m unittest discover -s tests
"""

import os
import sys
import unittest

# Allow running from a fresh checkout without installing the package.
_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import agent_guard_rails
from agent_guard_rails import GuardRail, GuardrailResult, GuardrailViolation


class GuardRailTests(unittest.TestCase):
    def test_empty_rails_pass(self):
        rails = GuardRail()
        self.assertEqual(rails.check("anything"), "anything")

    def test_run_returns_result(self):
        rails = GuardRail()
        result = rails.run("hello")
        self.assertIsInstance(result, GuardrailResult)
        self.assertTrue(result.passed)
        self.assertTrue(result.ok)
        self.assertEqual(result.violations, [])

    def test_length_min_passes(self):
        rails = GuardRail()
        rails.add_length(min_chars=3)
        rails.check("abc")  # should not raise

    def test_length_min_fails(self):
        rails = GuardRail()
        rails.add_length(min_chars=5)
        with self.assertRaises(GuardrailViolation) as ctx:
            rails.check("hi")
        self.assertEqual(ctx.exception.rule_name, "length")
        self.assertIn("too short", str(ctx.exception))

    def test_length_max_passes(self):
        rails = GuardRail()
        rails.add_length(max_chars=10)
        rails.check("hello")

    def test_length_max_fails(self):
        rails = GuardRail()
        rails.add_length(max_chars=5)
        with self.assertRaises(GuardrailViolation) as ctx:
            rails.check("hello world")
        self.assertIn("too long", str(ctx.exception))

    def test_no_pattern_passes(self):
        rails = GuardRail()
        rails.add_no_pattern(r"\d{3}-\d{2}-\d{4}", name="no_ssn")
        rails.check("no SSN here")

    def test_no_pattern_fails(self):
        rails = GuardRail()
        rails.add_no_pattern(r"\d{3}-\d{2}-\d{4}", name="no_ssn")
        with self.assertRaises(GuardrailViolation) as ctx:
            rails.check("my ssn is 123-45-6789")
        self.assertEqual(ctx.exception.rule_name, "no_ssn")

    def test_required_pattern_passes(self):
        rails = GuardRail()
        rails.add_required_pattern(r"^#", name="starts_with_heading")
        rails.check("# Hello")

    def test_required_pattern_fails(self):
        rails = GuardRail()
        rails.add_required_pattern(r"^#", name="starts_with_heading")
        with self.assertRaises(GuardrailViolation) as ctx:
            rails.check("no heading here")
        self.assertEqual(ctx.exception.rule_name, "starts_with_heading")

    def test_no_keywords_passes(self):
        rails = GuardRail()
        rails.add_no_keywords(["badword", "forbidden"])
        rails.check("this is fine")

    def test_no_keywords_fails(self):
        rails = GuardRail()
        rails.add_no_keywords(["badword"])
        with self.assertRaises(GuardrailViolation):
            rails.check("this has badword in it")

    def test_no_keywords_case_insensitive(self):
        rails = GuardRail()
        rails.add_no_keywords(["forbidden"])
        with self.assertRaises(GuardrailViolation):
            rails.check("FORBIDDEN text")

    def test_no_keywords_case_sensitive(self):
        rails = GuardRail()
        rails.add_no_keywords(["Secret"], case_sensitive=True)
        rails.check("this is secret")  # lowercase does not match
        with self.assertRaises(GuardrailViolation):
            rails.check("this is Secret")

    def test_not_empty_passes(self):
        rails = GuardRail()
        rails.add_not_empty()
        rails.check("not empty")

    def test_not_empty_fails(self):
        rails = GuardRail()
        rails.add_not_empty()
        with self.assertRaises(GuardrailViolation):
            rails.check("")
        with self.assertRaises(GuardrailViolation):
            rails.check("   ")

    def test_type_check_passes(self):
        rails = GuardRail()
        rails.add_type(dict)
        rails.check({"key": "val"})

    def test_type_check_fails(self):
        rails = GuardRail()
        rails.add_type(dict)
        with self.assertRaises(GuardrailViolation) as ctx:
            rails.check("not a dict")
        self.assertIn("dict", str(ctx.exception))

    def test_run_collects_violations(self):
        rails = GuardRail()
        rails.add_length(min_chars=100)
        rails.add_required_pattern(r"^#")
        result = rails.run("short text")
        self.assertFalse(result.passed)
        self.assertEqual(len(result.violations), 2)

    def test_custom_rule(self):
        rails = GuardRail()

        def no_exclamation(output):
            if "!" in str(output):
                raise GuardrailViolation(
                    "no_exclamation", "No exclamation marks allowed", output
                )

        rails.add("no_exclamation", no_exclamation)
        rails.check("fine text")
        with self.assertRaises(GuardrailViolation):
            rails.check("bad text!")

    def test_rule_names(self):
        rails = GuardRail()
        rails.add_length(max_chars=100)
        rails.add_not_empty()
        self.assertIn("length", rails.rule_names())
        self.assertIn("not_empty", rails.rule_names())

    def test_violation_output_attribute(self):
        rails = GuardRail()
        rails.add_length(max_chars=3)
        with self.assertRaises(GuardrailViolation) as ctx:
            rails.check("toolong")
        self.assertEqual(ctx.exception.output, "toolong")

    def test_version_exposed(self):
        self.assertIsInstance(agent_guard_rails.__version__, str)
        self.assertTrue(agent_guard_rails.__version__)

    def test_run_exposes_structured_errors(self):
        rails = GuardRail()
        rails.add_length(min_chars=100)
        rails.add_required_pattern(r"^#", name="heading")
        result = rails.run("short text")
        self.assertFalse(result.passed)
        self.assertEqual(len(result.errors), 2)
        self.assertTrue(all(isinstance(e, GuardrailViolation) for e in result.errors))
        rule_names = {e.rule_name for e in result.errors}
        self.assertEqual(rule_names, {"length", "heading"})
        # String messages stay in sync with structured errors.
        self.assertEqual([str(e) for e in result.errors], result.violations)

    def test_run_no_errors_when_passing(self):
        rails = GuardRail()
        rails.add_not_empty()
        result = rails.run("ok")
        self.assertTrue(result.passed)
        self.assertEqual(result.errors, [])

    def test_run_wraps_unexpected_error(self):
        rails = GuardRail()

        def boom(output):
            raise ValueError("kaboom")

        rails.add("boom", boom)
        result = rails.run("x")
        self.assertFalse(result.passed)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0].rule_name, "boom")
        self.assertIn("kaboom", result.violations[0])

    def test_result_preserves_output(self):
        rails = GuardRail()
        rails.add_length(min_chars=100)
        result = rails.run("tiny")
        self.assertEqual(result.output, "tiny")

    def test_length_min_and_max_together(self):
        rails = GuardRail()
        rails.add_length(min_chars=3, max_chars=6)
        rails.check("abcd")
        with self.assertRaises(GuardrailViolation):
            rails.check("ab")
        with self.assertRaises(GuardrailViolation):
            rails.check("toolong")


if __name__ == "__main__":
    unittest.main()
