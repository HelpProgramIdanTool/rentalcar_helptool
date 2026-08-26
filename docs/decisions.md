# Project decisions

This file records important technical choices and the reason for each choice.

## Database for M0 and M1

- **Decision:** SQLite.
- **Chosen by:** Idan.
- **Date:** 2026-08-26.
- **Why:** It is simple, local, requires no separate database server, and is suitable for learning and building the first useful versions of the system.
- **Later:** When several employees need to work with the live system at the same time, evaluate moving to hosted PostgreSQL.

## Backend framework

- **Decision:** Django.
- **Chosen by:** Idan.
- **Date:** 2026-08-26.
- **Why:** The system needs many editable tables, users, login, forms, and permissions. Django provides these features and a ready-made administration interface.
- **Alternative considered:** FastAPI and Flask would require more administration and authentication work.

## Test runner

- **Decision:** Django's built-in test runner.
- **Chosen by:** Idan.
- **Date:** 2026-08-26.
- **Why:** It is included with Django, requires no extra package, and is the simplest way to learn automated testing at the beginning.
- **Later:** Evaluate pytest and pytest-django if shorter tests or additional testing tools become useful.
