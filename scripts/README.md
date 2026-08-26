# scripts/

This folder is for **Idan's helper Python scripts** — small programs that are not the main app
but help build or generate things.

## What belongs here

For example: the **Python script(s) that generated the HTML mockup** in
[`../prototype/`](../prototype/). Right now those scripts live only on Idan's computer and are
**not saved in this project**.

👉 **They should be moved here and committed to git**, so that:

- nothing gets lost if the computer breaks,
- the history of changes is saved,
- anyone (including your agent) can see how the mockup was made and re-run it.

## How to move them in (ask your agent)

> *"I have Python script(s) on my computer that generated the HTML mockup. Help me copy them
> into the `scripts/` folder, add a short note here about what each one does, and commit them
> to git. Explain each step."*

## Note

These scripts are **helpers**, not the real backend. The real server code will live in a
separate `backend/` folder later (see
[`../docs/guides/02-backend-setup.md`](../docs/guides/02-backend-setup.md)).
