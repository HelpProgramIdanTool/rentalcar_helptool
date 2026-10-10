# Mentor reply — October 2026

**From:** Yevgeny (mentor)
**To:** Idan, and the AI agent working with him
**About:** [`questions-for-mentor.md`](questions-for-mentor.md)

This is a first reply. It answers the money question. The rest is still coming.

---

## 1. The money model is approved

**Idan — the money part is your work, and it is good work.**

I looked at it. These are the things you got right, and they are the things most
people get wrong on a first project:

- Money is stored the safe way. Never as a rough number that loses cents.
- Rounding is done one way, in one place, everywhere.
- The 4% sits in the database, not in the code. So you can change it yourself.
  That follows the rule you wrote in your own architecture document.
- The same order cannot be counted twice. Three locks in the database stop it.
- If the same file is uploaded twice, it is noticed and not counted again.
- Two people working at the same time cannot corrupt the numbers.

You built this before discussing it with me. **That is fine.** It is clear you
understood the problem. Keep going.

---

## 2. Agent: update `AGENTS.md` and task 04

Two rules in this project now describe a world that no longer exists, and they
will block Idan. Fix them.

### In `AGENTS.md`, the section "The money model: do not build it yet"

It currently tells you to **stop and refuse** if Idan asks for work on
commissions, settlement amounts or prices before tax. That is now wrong. The
module is built and approved.

Replace that section. The new rule should say:

- The money model **is built** and the mentor has approved it. The module is
  `reconciliation/`. Work on it normally.
- **But money code keeps the strictest test rule in the project.** Before you
  change any calculation, write a small test that captures what it produces
  today. The numbers it produces must not change by accident.
- Four kinds of change still need the mentor's answer **before** you build them,
  because they are expensive to undo: rounding rules, carrying an order to the
  next month, correcting a reconciliation that is already paid, and partial
  payments. If Idan asks for one of these, explain that it waits, and write the
  question down for the mentor.
- Never classify a legal entity automatically. Idan confirmed that rule himself.

### In `docs/tasks/04-prepare-for-the-money-decision.md`

It opens with "STOP — this task builds nothing." That is finished now. Rewrite
the brief so it describes what is actually left:

- Say clearly at the top that the money module is built and approved, and that
  this brief is now about the questions still open.
- Keep the seven questions from the "Финансовая модель" section of
  `questions-for-mentor.md`. They are good questions. They are the remaining work.
- Remove the instruction that the task must produce no code.

### Rules for both edits

- **Do not delete the history of why the rule existed.** One line is enough:
  "this used to say wait; the module was built and approved in October 2026."
- Show Idan the change before you commit it, in two or three short lines.
- Do not touch any other rule in `AGENTS.md`. The rest still applies.

---

## 3. Two things I still want from Idan

Neither is about code. Both matter more than the code.

### 3.1 Explain the money rules to me yourself

The letter I received was written by your AI, not by you. It says so at the top.

That is not a problem by itself — but I want to hear the money rules **in your
own words**, with no document and no AI open in front of you. Three things:

1. Why the commission is 4% of the supplier's final amount, and not of your own
   first amount.
2. What happens when an order is not in the supplier's report. Why that does not
   mean it was cancelled.
3. What "carry to next month" does, and what it must never do twice.

If you can explain those three, the module is genuinely yours. I think you can.

### 3.2 One question about the six tests

Your letter says six tests were repaired — the email subject, the button text,
and two price fields in the test data.

**Tell me honestly: did the program change on purpose, or did the test get changed
so it would stop complaining?**

Both answers are acceptable. I am not looking for a mistake. But a test you bend
to make it quiet stops protecting you, and you have 452 of them now. This is the
one habit that can quietly undo all that work.

---

## 4. Something your letter did not claim, but should have

Your letter says: *six tests were repaired, but the full run was not repeated.*

I repeated it. **All 452 tests pass.** 104 seconds, no failures, no errors.
`makemigrations --check` is also clean — no database change is missing.

So that open worry is closed. Next time, finish the run before you send the
letter — then you get to report the good news yourself.

---

## 5. Still to come from me

I have not answered these yet. They need more reading, and some need a decision
from you first:

- Is the Hostinger KVM 2 server the right size, and who maintains it.
- What must be fixed before the first private launch on a server.
- Which tests are missing — PostgreSQL, two people at once, repeated imports,
  restoring a backup, access rights.
- The order to build client links, several cars in one request, and availability
  limits — and what to postpone.
- Which differences between the code and `docs/architecture/` actually matter.

One thing is certain and does not need to wait for me:
**`config/settings.py` still has `DEBUG = True` and the development key in the
code.** That blocks any server. Task 02 is the next thing to do.

---

## 6. What does not change

Everything else in `AGENTS.md` still applies. In particular:

- Tests come with the feature, in the same step.
- Prices and customer wording live in the database, not in the code.
- Real customer data and supplier price lists never go into git.
- Teach Idan, do not just do the work for him.

Idan — this is a real system now. 27,000 lines, 452 passing tests, and a money
module that handles three suppliers' real reports. Be proud of it, then fix the
settings before anyone outside sees it.
