# 01 — Choosing a database

**Decision:** where will your app store its data?
**Short answer:** start with **SQLite**. You can change later. Here is why.

---

## What is a database?

A **database** is where your app keeps its information (customers, bookings, prices…) so it is
saved even after you close the program. Think of it as a very smart, very fast set of tables.

---

## Two ways to run a database

- **Local instance** — the database runs **on your own computer**. Only you can reach it. Great
  for learning and building. Nothing to sign up for, works with no internet.
- **Free online (hosted)** — the database runs **on the internet**, on someone else's computer.
  You reach it from anywhere, and later your real users can too. Needed when the app goes live.

You do **not** need the online one yet. Build on your computer first.

---

## Recommended: start with SQLite

**SQLite** is a database that is just **one file** on your computer.

- ✅ **Zero setup.** Nothing to install or sign up for.
- ✅ Built into Python already.
- ✅ It is the **default** in Django (the framework we suggest in the next guide), so it "just works".
- ✅ Perfect for learning and for building M0 + M1.
- ⚠️ Not made for many users at the same time — but you are not there yet.

For your first months, SQLite is the right choice. Full stop.

---

## Later: a free online database (when you go live)

When the app is ready for real daily use by the team, you move to **PostgreSQL** (a stronger
database made for many users). You do not run it yourself — you use a free hosted option:

| Option | One-line note |
|---|---|
| **Supabase** | Postgres with a friendly website and a free tier. Very popular. |
| **Neon** | Postgres that is simple to start, generous free tier. |
| **Railway** | Easy hosting for a database (and later your app too). |

> 💡 **You do not have to pick this now.** If you use Django, switching from SQLite to Postgres
> later is mostly a small settings change — not a rewrite. So this decision can wait.

---

## Ask your agent

- *"Explain SQLite to me in simple words. Show me where the database file will be."*
- *"When exactly would I need to move from SQLite to Postgres? Give me signs to watch for."*
- *"When the time comes, compare Supabase and Neon for a beginner. Which is easier?"*

---

## ✅ Decision box

- **Now:** SQLite (local, one file, zero setup).
- **Later (going live):** a free hosted Postgres — decide between Supabase / Neon / Railway then.

Write your choice down (for example in a `docs/decisions.md` file) so you remember why you chose it.
