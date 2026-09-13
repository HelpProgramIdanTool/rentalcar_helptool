# Idan Rent a Car — Help Tool

A web tool for **Idan Rent a Car** (a car-rental agent working with several Polish rental
companies). It will replace today's spreadsheet work with one system that handles the full
job: customer quotes across multiple suppliers, bookings, supplier emails, booking changes,
and monthly settlement + commissions.

> **Status: early learning project.** This is Idan's first project. The Django application is
> now under way: suppliers, price lists, customers, quotes, bookings and taxes exist, with a
> test suite that passes. It is **not** ready for real use yet (see *Before going live* below).

## Running it

```bash
uv run python manage.py migrate      # set up the local database
uv run python manage.py runserver    # start the server, then open http://127.0.0.1:8000/admin/
uv run python manage.py test         # run all the tests
```

## Where to start

👉 **Idan — read [`WELCOME-IDAN.md`](WELCOME-IDAN.md) first.** What you have built so far,
measured from git, and the four jobs waiting for you in order.

👉 **New here? Read [`docs/guides/00-start-here.md`](docs/guides/00-start-here.md) first.**

## The design (source of truth)

- [`docs/architecture/system-architecture-summary.md`](docs/architecture/system-architecture-summary.md)
  — the full, detailed specification (every entity and field).
- [`docs/architecture/architecture-and-roadmap.md`](docs/architecture/architecture-and-roadmap.md)
  — the "map": diagrams, the money model, and the **build order (milestones)**. Read this one first.

## Step-by-step guides (for Idan)

- [`docs/guides/00-start-here.md`](docs/guides/00-start-here.md) — how to work, and what to do first.
- [`docs/guides/01-choosing-a-database.md`](docs/guides/01-choosing-a-database.md) — where the data lives.
- [`docs/guides/02-backend-setup.md`](docs/guides/02-backend-setup.md) — the Python server.
- [`docs/guides/03-testing.md`](docs/guides/03-testing.md) — how to make sure it works.
- [`docs/decisions.md`](docs/decisions.md) — the choices Idan made, and why.

## Task briefs (for the AI agent)

- [`docs/tasks/00-point-git-at-the-new-home.md`](docs/tasks/00-point-git-at-the-new-home.md) —
  point Idan's clone at the repository's new address, and teach him what a git remote is.
- [`docs/tasks/01-build-the-test-safety-net.md`](docs/tasks/01-build-the-test-safety-net.md) —
  build the tests that protect the money calculations, and teach Idan how they work.
- [`docs/tasks/02-secrets-and-settings.md`](docs/tasks/02-secrets-and-settings.md) —
  move the private settings out of the code before going live, and teach Idan the rule.
- [`docs/tasks/03-move-rules-and-text-out-of-the-code.md`](docs/tasks/03-move-rules-and-text-out-of-the-code.md) —
  move supplier rules and Hebrew customer wording out of the code, so Idan can change them himself.
- [`docs/tasks/04-prepare-for-the-money-decision.md`](docs/tasks/04-prepare-for-the-money-decision.md) —
  understand the money model well enough to discuss it — **no code**, a document and a rehearsal.

## Before going live

Not needed while learning, but **must** be fixed before any real customer data is used:

- `config/settings.py` has `DEBUG = True` and a `SECRET_KEY` written directly in the file, in a
  **public** repository. Both must move to environment variables, and the key must be replaced.
- `ALLOWED_HOSTS` must be set for the real address.

This is milestone **M8** in the roadmap. It is a normal thing to fix later — just do not forget.
Step-by-step: [`docs/tasks/02-secrets-and-settings.md`](docs/tasks/02-secrets-and-settings.md).

## Repository layout

```
rentalcar_helptool/
├── README.md            ← you are here
├── AGENTS.md            ← rules for the AI coding agent (Codex)
├── manage.py            ← the Django command tool (runs the server, the tests, …)
├── pyproject.toml       ← the project's Python packages (managed with uv)
├── config/              ← Django settings, URLs, shared calculations
├── suppliers/           ← rental companies, cars, price lists
├── customers/           ← customers and drivers
├── quotes/              ← price inquiries and quotes
├── bookings/            ← confirmed bookings
├── employees/           ← employees and their commissions
├── taxes/               ← VAT rates per country
├── tests/               ← project-wide health checks
├── docs/
│   ├── architecture/    ← the design documents (source of truth)
│   ├── guides/          ← step-by-step guides for Idan
│   ├── tasks/           ← task briefs for the AI agent
│   └── decisions.md     ← the choices Idan made, and why
├── prototype/           ← the HTML mockup — a REFERENCE only, not the real app
└── scripts/             ← helper scripts (e.g. the code that generated the mockup)
```

Each folder with a `models.py` is a **Django app** — one part of the system, with its own data,
screens and tests.

## A note on the mockup

[`prototype/mvp_screens_visualization.html`](prototype/mvp_screens_visualization.html) is a
single self-contained HTML file that shows the screens and a sample price calculation. It is a
**reference to design against** — the real app is built fresh from the architecture docs, not by
growing this file.
