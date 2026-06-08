"""Standard-library ``unittest`` suite for agent-guard-rails-py.

These tests use only the Python standard library so they can be run with::

    python3 -m unittest discover -s tests

without installing any third-party test dependencies. They import and exercise
the real :mod:`agent_guard_rails` package.
"""

import os
import sys
import unittest

# Make ``src/`` importable when the package has not been installed (e.g. when
# running ``python3 -m unittest discover -s tests`` from a fresh checkout).
_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import agent_guard_rails
from agent_guard_rails import GuardRail, GuardrailResult, GuardrailViolation


class EmptyRailsTests(unittest.TestCase):
    def test_empty_rails_check_returns_output(self):
        rails = GuardRail()
        self.assertEqual(rails.check("anything"), "anything")

    def test_empty_rails_run_passes(self):
        rails = GuardRail()
        result = rails.run("hello")
        self.assertIsInstance(result, GuardrailResult)
        self.assertTrue(result.passed)
        self.assertTrue(result.ok)
        self.assertEqual(result.violations, [])
        self.assertEqual(result.errors, [])


class LengthRuleTests(unittest.TestCase):
    def test_min_passes(self):
        rails = GuardRail().add_length(min_chars=3)
        self.assertEqual(rails.check("abc"), "abc")

    def test_min_fails(self):
        rails = GuardRail().add_length(min_chars=5)
        with self.assertRaises(GuardrailViolation) as ctx:
            rails.check("hi")
        self.assertEqual(ctx.exception.rule_name, "length")
        self.assertIn("too short", str(ctx.exception))

    def test_max_passes(self):
        rails = GuardRail().add_length(max_chars=10)
        rails.check("hello")

    def test_max_fails(self):
        rails = GuardRail().add_length(max_chars=5)
        with self.assertRaises(GuardrailViolation) as ctx:
            rails.check("hello world")
        self.assertIn("too long", str(ctx.exception))

    def test_min_and_max_together(self):
        rails = GuardRail().add_length(min_chars=3, max_chars=6)
        rails.check("abcd")
        with self.assertRaises(GuardrailViolation):
            rails.check("ab")
        with self.assertRaises(GuardrailViolation):
            rails.check("toolong")

    def test_boundary_values_inclusive(self):
        # Exactly at the boundary should pass (min/max are inclusive).
        rails = GuardRail().add_length(min_chars=3, max_chars=3)
        rails.check("abc")


class PatternRuleTests(unittest.TestCase):
    def test_no_pattern_passes(self):
        rails = GuardRail().add_no_pattern(r"\d{3}-\d{2}-\d{4}", name="no_ssn")
        rails.check("no SSN here")

    def test_no_pattern_fails(self):
        rails = GuardRail().add_no_pattern(r"\d{3}-\d{2}-\d{4}", name="no_ssn")
        with self.assertRaises(GuardrailViolation) as ctx:
            rails.check("my ssn is 123-45-6789")
        self.assertEqual(ctx.exception.rule_name, "no_ssn")

    def test_no_pattern_default_case_insensitive(self):
        rails = GuardRail().add_no_pattern(r"secret")
        with self.assertRaises(GuardrailViolation):
            rails.check("This is SECRET")

    def test_required_pattern_passes(self):
        rails = GuardRail().add_required_pattern(r"^#", name="starts_with_heading")
        rails.check("# Hello")

    def test_required_pattern_fails(self):
        rails = GuardRail().add_required_pattern(r"^#", name="starts_with_heading")
        with self.assertRaises(GuardrailViolation) as ctx:
            rails.check("no heading here")
        self.assertEqual(ctx.exception.rule_name, "starts_with_heading")


class KeywordRuleTests(unittest.TestCase):
    def test_passes_when_absent(self):
        rails = GuardRail().add_no_keywords(["badword", "forbidden"])
        rails.check("this is fine")

    def test_fails_when_present(self):
        rails = GuardRail().add_no_keywords(["badword"])
        with self.assertRaises(GuardrailViolation):
            rails.check("this has badword in it")

    def test_case_insensitive_by_default(self):
        rails = GuardRail().add_no_keywords(["forbidden"])
        with self.assertRaises(GuardrailViolation):
            rails.check("FORBIDDEN text")

    def test_case_sensitive(self):
        rails = GuardRail().add_no_keywords(["Secret"], case_sensitive=True)
        rails.check("this is secret")  # lowercase does not match
        with self.assertRaises(GuardrailViolation):
            rails.check("this is Secret")


class NotEmptyRuleTests(unittest.TestCase):
    def test_passes(self):
        GuardRail().add_not_empty().check("not empty")

    def test_fails_on_empty(self):
        rails = GuardRail().add_not_empty()
        with self.assertRaises(GuardrailViolation):
            rails.check("")

    def test_fails_on_whitespace(self):
        rails = GuardRail().add_not_empty()
        with self.assertRaises(GuardrailViolation):
            rails.check("   ")


class TypeRuleTests(unittest.TestCase):
    def test_passes(self):
        GuardRail().add_type(dict).check({"key": "val"})

    def test_fails(self):
        rails = GuardRail().add_type(dict)
        with self.assertRaises(GuardrailViolation) as ctx:
            rails.check("not a dict")
        self.assertIn("dict", str(ctx.exception))


class RunAndCheckTests(unittest.TestCase):
    def test_run_collects_multiple_violations(self):
        rails = GuardRail().add_length(min_chars=100).add_required_pattern(r"^#")
        result = rails.run("short text")
        self.assertFalse(result.passed)
        self.assertEqual(len(result.violations), 2)

    def test_run_exposes_structured_errors(self):
        rails = (
            GuardRail()
            .add_length(min_chars=100)
            .add_required_pattern(r"^#", name="heading")
        )
        result = rails.run("short text")
        self.assertFalse(result.passed)
        self.assertEqual(len(result.errors), 2)
        self.assertTrue(
            all(isinstance(e, GuardrailViolation) for e in result.errors)
        )
        self.assertEqual(
            {e.rule_name for e in result.errors}, {"length", "heading"}
        )
        # Human-readable messages stay in sync with structured errors.
        self.assertEqual([str(e) for e in result.errors], result.violations)

    def test_run_no_errors_when_passing(self):
        result = GuardRail().add_not_empty().run("ok")
        self.assertTrue(result.passed)
        self.assertEqual(result.errors, [])

    def test_run_wraps_unexpected_error(self):
        def boom(_output):
            raise ValueError("kaboom")

        result = GuardRail().add("boom", boom).run("x")
        self.assertFalse(result.passed)
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0].rule_name, "boom")
        self.assertIn("kaboom", result.violations[0])

    def test_check_raises_on_first_failure_only(self):
        seen = []

        def record(name):
            def rule(_output):
                seen.append(name)
                raise GuardrailViolation(name, "blocked")

            return rule

        rails = GuardRail().add("first", record("first")).add("second", record("second"))
        with self.assertRaises(GuardrailViolation):
            rails.check("x")
        # ``check`` short-circuits, so only the first rule ran.
        self.assertEqual(seen, ["first"])

    def test_result_preserves_output(self):
        result = GuardRail().add_length(min_chars=100).run("tiny")
        self.assertEqual(result.output, "tiny")

    def test_check_returns_output_when_passing(self):
        rails = GuardRail().add_not_empty().add_length(max_chars=10)
        self.assertEqual(rails.check("hello"), "hello")


class CustomRuleAndApiTests(unittest.TestCase):
    def test_custom_rule(self):
        def no_exclamation(output):
            if "!" in str(output):
                raise GuardrailViolation(
                    "no_exclamation", "No exclamation marks allowed", output
                )

        rails = GuardRail().add("no_exclamation", no_exclamation)
        rails.check("fine text")
        with self.assertRaises(GuardrailViolation):
            rails.check("bad text!")

    def test_add_returns_self_for_chaining(self):
        rails = GuardRail()
        self.assertIs(rails.add_not_empty(), rails)
        self.assertIs(rails.add_length(max_chars=10), rails)

    def test_rule_names_preserves_order(self):
        rails = (
            GuardRail()
            .add_length(max_chars=100)
            .add_not_empty()
            .add_type(str)
        )
        self.assertEqual(rails.rule_names(), ["length", "not_empty", "type_check"])

    def test_violation_output_attribute(self):
        rails = GuardRail().add_length(max_chars=3)
        with self.assertRaises(GuardrailViolation) as ctx:
            rails.check("toolong")
        self.assertEqual(ctx.exception.output, "toolong")

    def test_version_exposed(self):
        self.assertIsInstance(agent_guard_rails.__version__, str)
        self.assertTrue(agent_guard_rails.__version__)

    def test_public_exports(self):
        for name in ("GuardRail", "GuardrailViolation", "GuardrailResult", "__version__"):
            self.assertIn(name, agent_guard_rails.__all__)


if __name__ == "__main__":
    unittest.main()
