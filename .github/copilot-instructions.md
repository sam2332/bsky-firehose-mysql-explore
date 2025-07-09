# GitHub Copilot Instructions for bsky Extract and Search Tool

## Project Overview
This project is a set of Python scripts and utilities for extracting, processing, and searching data from the Bluesky (bsky) platform. It includes tools for database setup, word frequency analysis, word cloud generation, and monitoring.

## Coding Guidelines
- **Language:** Use Python 3.8+ features and idioms.
- **Formatting:** Follow [PEP 8](https://peps.python.org/pep-0008/) for code style. Use 4 spaces for indentation.
- **Type Hints:** Use type hints for all function signatures.
- **Docstrings:** Add concise docstrings to all public functions and classes.
- **Error Handling:** Use exceptions for error handling. Log errors where appropriate.
- **Logging:** Use the standard `logging` module for logs, not print statements.
- **Dependencies:** List all dependencies in `requirements.txt`.
- **Database:** Use SQLAlchemy for database access. Avoid raw SQL unless necessary.
- **Configuration:** Store configuration in environment variables or a `.env` file. Do not hardcode secrets.
- **Scripts:** Entry-point scripts should be executable and have a `__main__` guard.
- **Notebooks:** Use Jupyter notebooks for exploratory analysis only. Production code should be in `.py` files.

## Copilot Usage
- Suggest code completions that follow the above guidelines.
- When generating new files, include a module-level docstring.
- When refactoring, prefer readability and maintainability over cleverness.
- For database migrations, use Alembic.
- For Flask apps, follow Flask best practices (app factory pattern, blueprints, etc.).

## Example File Structure
- `bsky.py`: Main entry point for extraction/search.
- `flask_app/app.py`: Flask application setup.
- `db/`: mysql database files, please do not touch.

## Additional Notes
- Keep code modular and functions small.
- Use list comprehensions and generator expressions where appropriate.
- Prefer pathlib over os.path for file operations.
- Document any non-obvious logic inline with comments.
- Try and keep files under 200 lines for readability.

