# Idan Rent a Car — Help Tool

A web tool for **Idan Rent a Car** (a car-rental agent working with several Polish rental
companies). It will replace today's spreadsheet work with one system that handles the full
job: customer quotes across multiple suppliers, bookings, supplier emails, booking changes,
and monthly settlement + commissions.

> **Status: early learning project.** This is Idan's first project. Right now the repo holds
> the design documents and an HTML mockup. The real application is not built yet.

## Where to start

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

## Repository layout

```
rentalcar_helptool/
├── README.md            ← you are here
├── AGENTS.md            ← rules for the AI coding agent (Codex)
├── docs/
│   ├── architecture/    ← the design documents (source of truth)
│   └── guides/          ← step-by-step guides for Idan
├── prototype/           ← the HTML mockup — a REFERENCE only, not the real app
├── scripts/             ← helper scripts (e.g. the code that generated the mockup)
└── backend/             ← (created later) the Python server code will live here
```

## A note on the mockup

[`prototype/mvp_screens_visualization.html`](prototype/mvp_screens_visualization.html) is a
single self-contained HTML file that shows the screens and a sample price calculation. It is a
**reference to design against** — the real app is built fresh from the architecture docs, not by
growing this file.
