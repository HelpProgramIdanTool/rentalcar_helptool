# 00 — Start here

Welcome, Idan! 👋 This is your first project. Take it slowly. You will learn as you build.

This page explains **what you are building**, **how to work with your AI agent**, and **what
to do first**.

---

## What you are building

A website that helps Idan Rent a Car do its daily work in one place instead of in spreadsheets:

- find prices from several rental companies (suppliers),
- send the customer a few good options (a **quote**),
- turn the chosen option into a **booking**,
- send the booking email to the supplier,
- handle changes to a booking,
- each month, check the supplier's bill and calculate the money everyone earns.

You do **not** build all of this at once. You build it in small parts, in a set order.

---

## How to work with your AI agent (Codex)

Your agent has rules in [`../../AGENTS.md`](../../AGENTS.md). It will:

- explain things in simple words,
- **teach** you, not just do the work for you,
- give you choices and let **you** decide,
- always use a safe Python setup and always write tests.

Good ways to ask it:

- *"Explain this to me in simple words, like I am new."*
- *"Show me one small step, then wait for me."*
- *"Why is this better than the other option?"*
- *"Add tests for this and tell me what each test checks."*

If you do not understand something — **say so**. Ask again. That is how you learn.

---

## The plan: build in order

1. Read the **map** first: [`../architecture/architecture-and-roadmap.md`](../architecture/architecture-and-roadmap.md).
   Look at the diagrams and the **milestones** (M0, M1, M2 …). Do not worry about understanding
   every detail yet.
2. The detailed spec is [`../architecture/system-architecture-summary.md`](../architecture/system-architecture-summary.md).
   This is the full reference. You do not read it all now — you look things up when you need them.
3. **Build M0, then M1, first.** Ignore the later milestones for now.
   - **M0** = the base: customers, suppliers, employees, login, etc.
   - **M1** = a central booking list that replaces the 3 Excel files. This is the first real win.

> 💡 Finish M1 and start using it for real work **before** building anything else. Shipping a
> small useful thing teaches you more than planning a big thing.

---

## Three decisions ahead of you

You will need to make three choices. Each has its own short guide. Your agent will help, but
**you decide**:

1. **Where does the data live?** → [`01-choosing-a-database.md`](01-choosing-a-database.md)
2. **What is the server (the Python program)?** → [`02-backend-setup.md`](02-backend-setup.md)
3. **How do you know it works?** → [`03-testing.md`](03-testing.md)

---

## Golden rules

- 🧪 **Always write tests.** (Your agent does this with you.)
- 📦 **Always use a virtual environment** (a private package setup for this project only).
- 🐢 **Small steps.** One working piece at a time.
- 🧠 **You make the decisions.** The agent gives options; you choose.
- 🙋 **Ask when unsure.** No question is too small.
