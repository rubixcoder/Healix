# Healix Code Guidelines

These guidelines help keep the repository consistent and maintainable.

## 1. Configuration
- Store environment-specific values in `.env`.
- Expose configuration values through `agents/config.py`.
- Do not use `os.getenv(...)` directly across multiple modules.
- Keep defaults centralized and documented in `agents/config.py`.

## 2. Error Handling
- Prefer raising exceptions for unexpected failures.
- Use result dictionaries only when the module contract explicitly returns a structured result.
- Keep error messages clear and actionable.
- For internal flows, use custom exception classes if it improves readability.

## 3. Modularity
- Keep modules focused; avoid lumping unrelated concerns together.
- Do not create new modules unless they add clear value.
- Prefer internal helper classes over many tiny modules when the logic is closely related.
- Favor minimal, targeted refactors that preserve existing public interfaces and test contracts.
- When extracting helpers, keep the dependency surface small and avoid over-splitting closely related flow.

## 4. Type Safety
- Use type hints consistently.
- Prefer `TypedDict` for structured return values.
- Avoid `dict[str, Any]` when the shape of the data can be expressed explicitly.
- Use explicit return shapes for shared public functions, especially when they wrap external subprocess or Docker behavior.

## 5. Testing
- Keep tests concise and readable.
- Use dependency injection or patching to isolate external behavior.
- Aim for strong coverage of edge cases and failure paths.
- Validate both success and failure conditions.

## 6. Naming and Clarity
- Choose descriptive names for functions, classes, and variables.
- Avoid generic names like `data` or `result` unless the context is obvious.
- Use docstrings for public classes and functions.
- Prefer explicit control flow over deeply nested conditionals.
