# 02 — The backend (Python server)

**Decision:** which Python framework builds your server?
**Short answer:** we recommend **Django**. But read on — the choice is yours.

---

## What is a "server" / "backend"?

Your website has two sides:

- **Frontend** — what the user sees in the browser (the screens, like your mockup).
- **Backend (server)** — the Python program that **stores the data** and **answers** the
  frontend's requests ("save this booking", "give me the prices", "log this user in").

This guide is about the backend.

---

## Step 1 — Set up Python the safe way (do this first)

### The virtual environment

A **virtual environment** is a private box of Python packages **just for this project**. It keeps
this project's tools separate from the rest of your computer, so nothing gets mixed up or broken.

**Always use one. Never install project packages globally.**

### Use `uv`

`uv` is a modern, fast tool that manages both Python and your packages. Typical commands:

```bash
uv init            # start the project (creates the config files)
uv add django      # add a package (example: Django)
uv run <command>   # run something inside the project's environment
```

> 🙋 Ask your agent: *"Install uv for me and explain each command as we go. Then create the
> virtual environment for this project."*

---

## Step 2 — Choose your framework

A **framework** is a ready-made toolkit so you do not build the server from nothing.

### ⭐ Recommended: Django

Your app is **mostly admin/config screens** — you need to view, add, and edit *lots* of tables:
suppliers, locations, price lists, seasons, rates, extras, rules, VAT, commissions, and more
(see the architecture docs — there are around 30 of these).

**Django gives you a ready-made admin website for all of those tables, for free.** You define a
table once, and Django creates the screens to manage it. For a project like yours, that is a
huge head start — you get working screens on day one instead of building each one by hand.

| Framework | 👍 Good | 👎 Not so good |
|---|---|---|
| **Django** ⭐ | Free admin screens for all your tables; batteries included (login, database, forms); great docs | Bigger to learn at first; more "opinionated" |
| **FastAPI** | Modern, light, teaches good habits (types), automatic API docs | You build the admin screens and login yourself — more work for this app |
| **Flask** | Very small and simple to start | You add almost everything yourself; most manual |

**Our recommendation:** **Django**, because the free admin covers most of what M0 and M1 need.
But this is **your decision** — talk it through with your agent.

> 🙋 Ask your agent: *"For an app that is mostly admin/config tables, explain why Django's admin
> saves me time. Show me a tiny example of one table becoming an admin screen."*

---

## Step 3 — Figure out what your server must actually DO

Do **not** guess the features. **Get them from the design.**

Hand your agent this task:

> *"Read the files in `docs/architecture/`. For milestone **M1 only** (the central booking list
> that replaces the Excel files), list: (1) the data tables I need, and (2) the screens or
> endpoints the server must provide. Keep it to M1. Explain each item in one simple line."*

Then build **only** that list. Later milestones come later.

---

## Step 4 — Your first runnable win

Once you have picked Django and set up `uv`, aim for this first small goal:

1. Create the Django project.
2. Start the development server.
3. Open the built-in **admin** page in your browser and log in.

Seeing a real page you can open is a great first win. Let your agent walk you through the exact
commands **one step at a time**, and make sure each step runs before the next.

> 🙋 Ask your agent: *"Walk me through creating the Django project and opening the admin page,
> one small step at a time. Wait for me after each step."*
