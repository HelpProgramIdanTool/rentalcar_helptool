# 03 — Testing (making sure it works)

**The rule on this project: every new feature gets tests, in the same step.**

---

## Why test?

When you write code, you want to be sure it does the right thing — and that it **keeps** working
after you change something else later. Tests do this for you automatically.

Without tests, you check by hand every time (slow, easy to miss things). With tests, the computer
checks for you in seconds.

Tests also let your agent **prove** its work is correct instead of just saying "done".

---

## What is a unit test?

A **unit test** is a small piece of code that checks **one thing** works correctly.

Tiny example — imagine a function that adds two numbers:

```python
def add(a, b):
    return a + b

# a unit test for it:
def test_add():
    assert add(2, 3) == 5   # "assert" means: this must be true, or the test fails
```

If someone later breaks `add`, the test fails and tells you right away.

---

## The rule for this project

- Every time you add or change a feature, you (with your agent) add **unit tests** for it.
- The task is **not done** until the tests **pass**.
- Ask your agent to **explain what each test checks**, in simple words.

This rule is also written in [`../../AGENTS.md`](../../AGENTS.md), so your agent will follow it.

---

## How to run tests (with Django)

If you chose **Django**, you already have a test tool built in — nothing extra to install:

```bash
uv run python manage.py test
```

Green / "OK" means the tests passed. If one fails, read the message: it usually says exactly
what was expected and what happened instead.

> **Later option:** many people use a tool called **pytest** (with **pytest-django**) because the
> tests are a little shorter to write. You do **not** need it to start — begin with Django's
> built-in runner, and try pytest later if you want.

---

## Ask your agent

- *"Add unit tests for this feature and run them. Explain what each test checks in simple words."*
- *"A test failed. Explain the error message to me like I am new, and show me how to fix it."*
- *"Show me how to run all the tests, and what a passing result looks like."*

---

## 🧠 Remember

Tests are not extra work you do at the end. They are part of building each small piece. A feature
**with** tests is finished; a feature **without** tests is not.
