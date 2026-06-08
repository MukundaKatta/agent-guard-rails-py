"""agent-guard-rails-py — composable output guardrails for LLM agent responses."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

__version__ = "0.1.0"


class GuardrailViolation(Exception):
    """Raised when a guardrail rejects the output."""

    def __init__(self, rule_name: str, reason: str, output: Any = None) -> None:
        self.rule_name = rule_name
        self.reason = reason
        self.output = output
        super().__init__(f"Guardrail '{rule_name}' violated: {reason}")


@dataclass
class GuardrailResult:
    """Result of running guardrails against an output.

    ``violations`` holds the human-readable messages (one per failed rule).
    ``errors`` holds the corresponding :class:`GuardrailViolation` objects so
    callers can inspect ``rule_name``/``reason``/``output`` programmatically.
    """

    passed: bool
    output: Any
    violations: list[str] = field(default_factory=list)
    errors: list[GuardrailViolation] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.passed


class GuardRail:
    """
    Composable output guardrails for LLM agent responses.

    Rules are callables: (output) -> None (pass) or raise GuardrailViolation.
    Built-in helpers create common rules. Run all rules with .check().

    Example::

        rails = GuardRail()
        rails.add_length(max_chars=2000)
        rails.add_no_pattern(r"SSN:\\s*\\d{3}-\\d{2}-\\d{4}", name="no_ssn")
        rails.add_required_pattern(r"^#", name="starts_with_heading")

        result = rails.run("# Hello world")
        if not result.passed:
            print(result.violations)

        # Or raise on violation:
        rails.check("# Hello world")
    """

    def __init__(self) -> None:
        self._rules: list[tuple[str, Callable]] = []

    def add(self, name: str, rule: Callable[[Any], None]) -> "GuardRail":
        """Add a custom rule. Rule raises GuardrailViolation to block, or returns None to pass."""
        self._rules.append((name, rule))
        return self

    def add_length(
        self, min_chars: int | None = None, max_chars: int | None = None
    ) -> "GuardRail":
        """Block output that is shorter or longer than the given character limits."""

        def rule(output: Any) -> None:
            text = str(output)
            if min_chars is not None and len(text) < min_chars:
                raise GuardrailViolation(
                    "length",
                    f"Output too short: {len(text)} chars (min {min_chars})",
                    output,
                )
            if max_chars is not None and len(text) > max_chars:
                raise GuardrailViolation(
                    "length",
                    f"Output too long: {len(text)} chars (max {max_chars})",
                    output,
                )

        return self.add("length", rule)

    def add_no_pattern(
        self, pattern: str, name: str = "no_pattern", flags: int = re.IGNORECASE
    ) -> "GuardRail":
        """Block output that matches a forbidden regex pattern."""
        compiled = re.compile(pattern, flags)

        def rule(output: Any) -> None:
            if compiled.search(str(output)):
                raise GuardrailViolation(
                    name, f"Forbidden pattern matched: {pattern!r}", output
                )

        return self.add(name, rule)

    def add_required_pattern(
        self, pattern: str, name: str = "required_pattern", flags: int = re.IGNORECASE
    ) -> "GuardRail":
        """Block output that does NOT match a required regex pattern."""
        compiled = re.compile(pattern, flags)

        def rule(output: Any) -> None:
            if not compiled.search(str(output)):
                raise GuardrailViolation(
                    name, f"Required pattern missing: {pattern!r}", output
                )

        return self.add(name, rule)

    def add_no_keywords(
        self,
        keywords: list[str],
        name: str = "no_keywords",
        case_sensitive: bool = False,
    ) -> "GuardRail":
        """Block output containing any of the listed keywords."""
        if not case_sensitive:
            kws = [k.lower() for k in keywords]

            def rule(output: Any) -> None:
                text = str(output).lower()
                found = [k for k in kws if k in text]
                if found:
                    raise GuardrailViolation(
                        name, f"Forbidden keywords: {found}", output
                    )
        else:

            def rule(output: Any) -> None:  # type: ignore[misc]
                text = str(output)
                found = [k for k in keywords if k in text]
                if found:
                    raise GuardrailViolation(
                        name, f"Forbidden keywords: {found}", output
                    )

        return self.add(name, rule)

    def add_not_empty(self, name: str = "not_empty") -> "GuardRail":
        """Block empty or whitespace-only output."""

        def rule(output: Any) -> None:
            if not str(output).strip():
                raise GuardrailViolation(name, "Output is empty or whitespace.", output)

        return self.add(name, rule)

    def add_type(self, expected_type: type, name: str = "type_check") -> "GuardRail":
        """Block output that is not an instance of expected_type."""

        def rule(output: Any) -> None:
            if not isinstance(output, expected_type):
                raise GuardrailViolation(
                    name,
                    f"Expected {expected_type.__name__}, got {type(output).__name__}",
                    output,
                )

        return self.add(name, rule)

    def check(self, output: Any) -> Any:
        """Run all rules. Raises GuardrailViolation on the first failure."""
        for name, rule in self._rules:
            rule(output)
        return output

    def run(self, output: Any) -> GuardrailResult:
        """Run all rules, collecting violations without raising."""
        violations: list[str] = []
        errors: list[GuardrailViolation] = []
        for name, rule in self._rules:
            try:
                rule(output)
            except GuardrailViolation as exc:
                violations.append(str(exc))
                errors.append(exc)
            except Exception as exc:  # noqa: BLE001
                wrapped = GuardrailViolation(name, f"unexpected error: {exc}", output)
                violations.append(f"[{name}] unexpected error: {exc}")
                errors.append(wrapped)
        return GuardrailResult(
            passed=len(violations) == 0,
            output=output,
            violations=violations,
            errors=errors,
        )

    def rule_names(self) -> list[str]:
        """Return the names of all registered rules."""
        return [name for name, _ in self._rules]


__all__ = ["GuardRail", "GuardrailViolation", "GuardrailResult", "__version__"]
