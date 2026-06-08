# agent-guard-rails-py

Composable output guardrails for LLM agent responses. Chain rules to validate, block, or flag outputs before they reach downstream systems.

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

# Raise on first violation:
output = rails.check(llm_response)

# Collect all violations:
result = rails.run(llm_response)
if not result.passed:
    for v in result.violations:  # human-readable messages
        print(v)
    # Or inspect structured GuardrailViolation objects:
    for err in result.errors:
        print(err.rule_name, err.reason)

# Custom rule:
def no_exclamations(output):
    if "!" in output:
        raise GuardrailViolation("no_exclamation", "No exclamation marks allowed!")

rails.add("no_exclamation", no_exclamations)
```

## License

MIT
