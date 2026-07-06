# Coding Standards

## Python

- **Version**: 3.10+ (3.14 in current venv)
- **Formatter**: Black (line length 100)
- **Linter**: Ruff
- **Type hints**: Required for public functions and dataclass fields
- **Docstrings**: Google-style for all public modules, classes, and functions

## Style Rules

1. **Imports** — stdlib first, then third-party, then local. Group with blank lines.
2. **Naming** — `snake_case` for functions/variables, `PascalCase` for classes,
   `UPPER_CASE` for constants.
3. **Dataclasses** — prefer `@dataclass` over plain classes for data carriers.
4. **Exceptions** — define module-specific exceptions inheriting from a clear base
   (`PermissionError`, `ValueError`, etc.).
5. **Logging** — use `get_logger(__name__)`; never `print()`.
6. **No comments** — code should be self-documenting. Remove all comments unless
   explicitly requested.
7. **No emojis** — in code or documentation.
8. **No secrets** — never log or commit API keys, tokens, or passwords.

## File Layout

```python
"""Module docstring."""
import stdlib
from third_party import something
from local.package import module

logger = get_logger(__name__)

# Constants
CONSTANT = "value"

# Classes
@dataclass
class MyData:
    field: str

# Functions
def my_function(arg: str) -> MyData:
    ...
```

## Testing

- Tests live in `tests/` mirroring the source tree.
- Use `pytest` with `TestClient` from `starlette.testclient`.
- Every new module must have at least one test.
- Tests must not depend on external services or real hardware.
