# Task 03 - Move business rules and Hebrew text out of the code

**This file is a task brief for the AI agent.** Idan will read it too, so use simple, everyday
English. Follow the language rules in [`../../AGENTS.md`](../../AGENTS.md).

**Do task [`01-build-the-test-safety-net.md`](01-build-the-test-safety-net.md) first**, at least
Part 4 - and **section 4.6 was written for this task**: the small tests that prove a price and
a customer word come from the database, not from the code. Write those first. This task changes
code that calculates prices, so do not touch it without tests.

**Goal:** the same information should exist in **one place only** - and where it is business
information (a price, a name, a supplier rule), that place should be the **database**, where Idan
can change it himself, without a programmer.

---

## Part 0 - The rule Idan already wrote

Show him line 24 of his own architecture document
([`../architecture/architecture-and-roadmap.md`](../architecture/architecture-and-roadmap.md)):

> **1. Configuration over hardcoding.** Suppliers, prices, rules, VAT, templates, statuses, and
> commission terms ...

He wrote that rule himself, and it is the right rule. The code has drifted away from it - which is
completely normal while building fast. This task brings the code back to his own rule.

Say clearly: **nothing here is broken.** The system works. This is about who is allowed to change
things: a programmer, or Idan.

---

## Part 1 - Teach the idea with a real bug (do this first)

Do not explain the theory. **Show him.** This takes five minutes and he will never forget it.

Ask Idan to do this himself:

1. Start the server. Open the admin.
2. Find the Kaizen extra `CROSS_BORDER`. Its price is **499**.
3. **Change it to 555 and save.**
4. Make a quote that includes cross-border cover.
5. Look at the price on the offer.

**It still says 499.**

Now let him find out why. Show him
[`../../quotes/services.py`](../../quotes/services.py), around line 111:

```python
def _quoted_extra_price(extra, rate, days, quantity=Decimal("1")):
    if (
        extra.supplier.supplier_code == "01"
        and extra.extra_code == "CROSS_BORDER"
    ):
        return KAIZEN_CROSS_BORDER_PRICE * quantity     # always 499
    return _extra_price(rate, days, quantity)
```

The price `499` is written **twice**: once in the database (where Idan can edit it) and once in
the code (where he cannot). And the code wins.

Ask him these questions, and let him answer:

- *"Who would notice this in one year, when the price changes to 520?"*
- *"What would you think was happening?"*
- *"How long would you look for the problem?"*

Then give him the name of the rule, in plain words:

> **Every fact should be written in one place only. If it is written twice, one copy will be
> wrong one day - and nobody will know which one.**

This one bug is the reason for the whole task.

---

## Part 2 - The safety rule for this task: the offer must not change

This is the most important instruction here, so explain it before starting.

This task changes **how** the system finds its information. It must **not** change **what** the
customer sees. Same prices, same words, same order.

Programmers call a change like this "tidying up without changing behaviour". So how do you prove
you changed nothing? **Take a photograph first.**

Explain it to Idan like this:

> Before we move anything, we make a test that builds one complete offer and saves exactly what it
> produced - every line, every price, every word. That is our photograph. After every step, we run
> it again. If the new offer matches the photograph, we know we broke nothing. If one number moved,
> the test tells us immediately.

**Do this before Job A:**

1. Build a fixed offer from fake data (use the fake `Test Rent` supplier from task 01, plus one
   real supplier if needed for the supplier rules).
2. Save the full result of `calculate_quote_options` into the test as the expected answer.
3. Confirm it passes today, before any change.

Then, after **every** job below: run all the tests. If the photograph test fails, the change was
not a tidy-up - stop and look at it with Idan.

Programmers call this an approval test, or a golden test. Tell him the name once, after he
understands it.

---

## Part 3 - The jobs, smallest first

Do **one job per step**. Run the tests after each. Commit after each, with a message that says
what moved. **Do not** start the next job until Idan understands the one just finished.

Each job below says how big it is. Be honest with him about that - two of these are five-minute
deletions, and two are real work.

---

### Job A - Delete the hardcoded 499 (very small: a deletion)

The database already has the correct price. The code just has to stop ignoring it.

1. Delete the special case inside `_quoted_extra_price` in `quotes/services.py`.
2. Delete the constant `KAIZEN_CROSS_BORDER_PRICE`.
3. Fix the test that checks the constant
   (`test_kaizen_cross_border_offer_rate_is_499_per_rental` in `quotes/tests.py`) - it should now
   check that the price **comes from the rate in the database**, not from a number in the code.
4. Repeat the experiment from Part 1: change the price in the admin, and watch the offer change.

**Teaching point:** the best fix is often deleting code, not adding it. Let Idan see that the
system got *simpler* and *more* correct at the same time.

**Note for the agent:** after this, migration `0015` and its price `499.00` still exist. That is
fine - the migration put the value into the database once, which is its job. What matters is that
nothing overrides the database any more. Whether to keep prices in migrations at all is Idan's
decision in task 01, Part 7.

---

### Job B - Put the same Hebrew words in one place (small, but do it carefully)

Right now the Hebrew name of an extra is written in **three** places in `quotes/services.py`:

1. `HEBREW_EXTRA_NAMES` (around line 43)
2. `optional_labels` (around line 303)
3. inside `included_items` (around line 298)

For example `כיסא תינוק / בוסטר` appears more than once. So if Idan improves the wording in one
place, the offer will show the old wording somewhere else. Show him the two copies side by side -
it is easier to see than to explain.

Ask him: *"If you change one and forget the other, when do you find out?"* (Answer: when a
customer receives a strange offer.)

**Step 1 (do now): make it one copy, still in code.**

Move all these Hebrew names into **one** place - a new small file, for example
`quotes/extra_catalog.py` - and have all three places read from it. Nothing else changes.

This is a small, safe step. It fixes the duplication today. It does **not** yet let Idan edit the
words himself - that is step 2, and it is a bigger job.

**Step 2 (Job D below): move them into the database**, so Idan can edit the words in the admin.

**Do not skip step 1 and jump to step 2.** Two small safe changes beat one big risky change. That
is worth saying out loud to Idan, because it is how professionals work.

**Important - a mistake to avoid:** do **not** put the Hebrew customer name into
`SupplierExtra.name`. That field holds the **supplier's own English wording** (for example
`"Baby seat or booster"`), which Idan needs when he talks to the supplier. The Hebrew name is what
the **customer** sees. They are two different things and both are useful. Explain this difference
to him - it is the reason step 2 needs a new place to live.

---

### Job C - Move the "what is included" list into the database (small)

In `quotes/services.py` around line 298:

```python
included_items = ["מחיר השכרת הרכב", "מע״מ (VAT)", "עד שני נהגים"]
if supplier_code == "01":
    included_items.extend(KAIZEN_COMFORT_INCLUDED_ITEMS)
```

This is a **sales text** decision - what the offer promises the customer. Idan will want to change
this wording, and he should not need a programmer for it.

**Decision for Idan** - give the options, then let him choose:

1. **A text field on `Supplier`**, one item per line (recommend this). Good: one small field, he
   edits it in the admin immediately. Bad: it is one block of text, so no ordering or on/off per
   item.
2. **A small new table** `SupplierIncludedItem` (supplier, text, order, active). Good: he can
   reorder and switch items off. Bad: a new table and a new admin screen to build.
3. **Use `QuoteTemplateBlock`**, which already exists (see Job E). Good: nothing new to build. Bad:
   those blocks are paragraphs of text, not a list of short items, so it fits less well.

Whichever he picks, the shared items (`rental price`, `VAT`, `up to two drivers`) belong somewhere
too - probably a default list that applies to every supplier.

---

### Job D - The real one: a table for "what the customer asks for" (medium - the main job)

This is the biggest change in the task, and it fixes the root cause of Jobs B and C. Explain the
idea before touching anything.

**The problem, in business words.** A customer asks for "a baby seat". Each supplier calls it
something different: Kaizen calls it `CHILD_SEAT`, another supplier calls it `BABY_SEAT_BOOSTER`.
Today that translation lives in a list **inside a function** - `quotes/services.py`, line 243:

```python
requested_code_map = {
    "CHILD_SEAT": {"01": "CHILD_SEAT", "02": "CHILD_SEAT", "03": "BABY_SEAT_BOOSTER"},
    "NAVIGATION":  {"01": "NAVIGATION", "02": "GPS"},
    ...
}
```

Ask Idan the question that shows why this matters:

> *"Next month you add a fourth supplier. What must happen before you can offer their baby seat?"*

The answer: a programmer must open this file and edit a list inside a function. Not Idan. **That is
the problem** - not the code style.

**What is missing is a name for an idea.** The system has *supplier extras* (what each supplier
sells). It has no table for *the thing the customer asks for*. That idea exists today only as the
keys of that dictionary.

So the work is: create that table - for example `ExtraType` (or `CustomerExtra`, let Idan name it,
he knows the business) - holding:

- the code (`CHILD_SEAT`)
- **the Hebrew name the customer sees** (this is the home for Job B step 2)
- whether it is offered as an optional item on the offer (this replaces `optional_labels`)
- the display order

and a link between one `ExtraType` and each supplier's own `SupplierExtra` (this replaces
`requested_code_map`).

Then the two rules in `_service_extra_requests` (line 176) become data as well - a small setting on
the link that says *"add this automatically when the customer wants delivery to an address"* or
*"...when pickup or return is at the airport"*. After that, the supplier codes `"01"`, `"02"`,
`"03"` disappear from `quotes/services.py` completely.

**Check with Idan before building:** he must confirm the list of extras and the Hebrew wording,
because it goes in front of customers. Do not invent it.

**How to do it safely** - and explain each step:

1. Create the table and the admin screen. Change no logic yet. Tests still pass.
2. Fill it from the existing dictionaries with a management command, or a data script Idan runs
   once. Tests still pass.
3. Now change `quotes/services.py` to read from the table instead of the dictionaries.
4. The photograph test from Part 2 must still pass. **This is the moment it earns its cost** - it
   proves customers still see exactly the same offer.
5. Delete the dictionaries.

**Warn Idan honestly:** this job is bigger than the others - probably a few sessions. That is
normal. If it feels too big, it is fine to stop after Job C and come back later. **Do not do it
half-finished and leave both systems running at once** - that is worse than not starting.

---

### Job E - Move the long Hebrew paragraphs into the template blocks (small)

`quotes/services.py` also builds sentences for the customer - for example `_luggage_info` returns a
Hebrew sentence about luggage space.

Point out to Idan that the tool for this **already exists in his own system**:
`QuoteTemplate` and `QuoteTemplateBlock` in `quotes/models.py`, with `content`, `display_order` and
`condition_code`. His architecture planned for editable text, and part of the code went around it.

Move what fits into template blocks. Some sentences mix text with numbers (for example the number
of litres) - those need a small placeholder in the text. Do the simple ones first; leave the
complicated ones with a note.

**Do not** install Django's translation system (`.po` files) now. Explain why: it is the right tool
for **two or more languages**, and today the offers are Hebrew only. When Idan really needs Russian
or English, that is the moment - and it will be its own task.

---

### Job F - Check whether `suppliers/deposit_rules.py` is still needed (small - investigation)

`suppliers/deposit_rules.py` decides a deposit from the supplier code and the car group. But
migration `0017_fill_vehicle_group_deposits` put deposit values **into the database**, and
`VehicleGroup.effective_deposit_amount` reads them.

So there may be two systems doing the same job. Ask Idan to find out **with you**:

- Which one actually decides the number the customer sees?
- Is the file still used at all?

Then: if the database is the real source, delete the file. If it is a fallback for missing data,
say so in a one-line comment and keep it.

**Teaching point:** an unused file is not harmless. The next person - or Idan in six months - will
read it and believe it. Deleting dead code is real work, not tidying.

---

### Job G - Two tiny things (very small, do them last)

1. `quotes/forms.py` line 186 uses `__import__("datetime").datetime.combine(...)`. That is a strange
   way to use another file's code. It should be a normal `import datetime` at the top of the file.
   Worth showing Idan **why** it is strange: normal imports sit at the top, where a reader can see
   at a glance what this file depends on.
2. `quotes/urls.py` has two addresses pointing to the same page: `new_inquiry_alias` and
   `quote_preview_v2`. If they are leftovers from trying something out, delete them. If one is
   still used somewhere, leave it and add a short comment saying by what.

---

## Definition of done

- [ ] Idan can explain, in his own words, why the same fact in two places is dangerous - using the
      499 example he found himself.
- [ ] Idan can explain what the "photograph" test proves, and why this task needed one.
- [ ] Changing an extra's price in the admin changes the price on the offer. (Job A)
- [ ] Every Hebrew customer word exists in exactly **one** place. (Job B, and Job D step 2)
- [ ] Idan can change what the offer says is included, **without** a programmer. (Job C)
- [ ] `quotes/services.py` contains **no** supplier codes (`"01"`, `"02"`, `"03"`). (Job D)
- [ ] Adding a new supplier's extras needs **no code change** - Idan can do it in the admin. (Job D)
- [ ] `suppliers/deposit_rules.py` is either used and explained, or deleted. (Job F)
- [ ] All tests pass, including the photograph test: `uv run python manage.py test`.
- [ ] The offer a customer receives is **identical** to before this task. If anything changed on
      purpose, it is written down and Idan approved it.
- [ ] `docs/decisions.md` records his choices: where the included-items text lives, and the name he
      chose for the new extras table.

---

## What NOT to do

- Do **not** start without the photograph test from Part 2. Without it, this task is guessing.
- Do **not** change prices or wording while moving them. Move first, change later - two separate
  jobs. If both happen at once and the offer looks wrong, nobody can tell which change caused it.
- Do **not** do all the jobs in one big change. One job, tests green, commit.
- Do **not** build a general "rules engine" that can express every possible supplier rule. Idan has
  three suppliers and a handful of rules. A clever system he cannot understand is **worse** than
  the simple code he has today. Build exactly the table described in Job D and stop.
- Do **not** install Django translation files (`.po`) for one language.
- Do **not** leave Job D half done, with the dictionaries and the table both alive.
- Do **not** invent Hebrew wording for customers. Idan decides every word a customer reads.
