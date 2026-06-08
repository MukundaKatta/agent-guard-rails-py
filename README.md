# agent-guard-rails-py

[![CI](https://github.com/MukundaKatta/agent-guard-rails-py/actions/workflows/ci.yml/badge.svg)](https://github.com/MukundaKatta/agent-guard-rails-py/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](#license)

Composable output guardrails for LLM agent responses. Chain rules to validate,
block, or flag outputs before they reach downstream systems.

`agent-guard-rails-py` is a tiny, dependency-free library: rules are plain
callables, so you can mix the built-in rules with your own without learning a
framework. Use it to keep PII, empty responses, forbidden phrases, and malformed
output from leaving your agent.

## Features

- **Zero dependencies** — pure standard library, works on Python 3.9+.
- **Composable** — every builder returns the `GuardRail`, so rules chain fluently.
- **Two execution modes** — `check()` raises on the first violation;
  `run()` collects every violation without raising.
- **Structured results** — inspect human-readable messages *and* structured
  `GuardrailViolation` objects (rule name, reason, offending output).
- **Custom rules** — any `(output) -> None` callable that raises
  `GuardrailViolation` is a valid rule.
- **Typed** — ships a `py.typed` marker for full type-checker support.

## Install

```bash
pip install agent-guard-rails-py
```

## Usage

```python
from agent_guard_rails import GuardRail, GuardrailViolation

rails = GuardRail()
rails.add_not_empty()
rails.add_length(min_chars=10, max_chars=2000)
rails.add_no_pattern(r"SSN:\s*\d{3}-\d{2}-\d{4}", name="no_ssn")
rails.add_required_pattern(r"^#", name="starts_with_heading")
rails.add_no_keywords(["forbidden", "badword"])
rails.add_type(str)

# Builders return self, so rules can also be chained:
rails = (
    GuardRail()
    .add_not_empty()
    .add_length(max_chars=2000)
)

llm_response = "# Summary\n\nA perfectly valid heading-led response."

# Mode 1 — raise on the first violation:
output = rails.check(llm_response)  # returns the output unchanged if it passes

# Mode 2 — collect all violations without raising:
result = rails.run(llm_response)
if not result.passed:
    for message in result.violations:   # human-readable strings
        print(message)
    for err in result.errors:           # structured GuardrailViolation objects
        print(err.rule_name, err.reason)

# Custom rule — any callable that raises GuardrailViolation to block:
def no_exclamations(output):
    if "!" in str(output):
        raise GuardrailViolation("no_exclamation", "No exclamation marks allowed")

rails.add("no_exclamation", no_exclamations)
```

## API reference

### `GuardRail`

The rule container. Add rules with the builders below, then evaluate output
with `check()` or `run()`.

#### Built-in rule builders

Each builder appends a rule and returns the `GuardRail` for chaining.

| Method | Blocks when… |
| --- | --- |
| `add_not_empty(name="not_empty")` | the output is empty or whitespace-only |
| `add_length(min_chars=None, max_chars=None)` | `str(output)` is shorter than `min_chars` or longer than `max_chars` (bounds inclusive) |
| `add_no_pattern(pattern, name="no_pattern", flags=re.IGNORECASE)` | the regex **matches** the output (e.g. forbidden PII) |
| `add_required_pattern(pattern, name="required_pattern", flags=re.IGNORECASE)` | the regex does **not** match the output |
| `add_no_keywords(keywords, name="no_keywords", case_sensitive=False)` | any listed keyword appears in the output |
| `add_type(expected_type, name="type_check")` | the output is not an instance of `expected_type` |
| `add(name, rule)` | the custom `rule(output)` callable raises `GuardrailViolation` |

#### Evaluation methods

- **`check(output) -> output`** — runs rules in order and raises the first
  `GuardrailViolation`; returns the output unchanged if all rules pass.
- **`run(output) -> GuardrailResult`** — runs every rule, capturing all
  violations (and wrapping any unexpected exception as a `GuardrailViolation`)
  without raising.
- **`rule_names() -> list[str]`** — the names of registered rules, in order.

### `GuardrailResult`

Returned by `run()`:

- `passed: bool` — `True` when no rule failed (`ok` is an alias).
- `output` — the value that was checked.
- `violations: list[str]` — human-readable messages, one per failed rule.
- `errors: list[GuardrailViolation]` — the structured violations, aligned 1:1
  with `violations`.

### `GuardrailViolation`

The exception raised by a failing rule. Carries `rule_name`, `reason`, and the
offending `output`.

## Development

The test suite uses only the standard library, so no extra packages are needed:

```bash
python -m unittest discover -s tests
```

## License

MIT
