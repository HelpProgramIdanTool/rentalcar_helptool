# Task 01 - Build the test safety net (and teach Idan how it works)

**This file is a task brief for the AI agent.** Idan will read it too, so every explanation
must use simple, everyday English.

**Two goals. Both must happen:**

1. Build tests that catch mistakes when Idan changes the system later.
2. **Teach Idan the ideas**, so he can do this himself next time.

If the tests get written but Idan does not understand them, this task **failed**.

---

## Part 1 - How to talk to Idan (read this first)

English is not Idan's first language, and he is new to programming. So:

- **One idea at a time.** Short sentences.
- **No professional words** unless you explain them the first time, in one short line.
- Use **everyday comparisons**. Example: "A test is like the checklist a mechanic uses. He
  checks the lights, the brakes, the oil. If one thing is wrong, he knows exactly which one."
- After each idea, **ask Idan to say it back in his own words.** If he cannot, explain it a
  different way. Do not continue until he can.
- Never answer with a wall of text. A few short lines, then wait.

### Words to avoid, and what to say instead

| Do not say | Say this |
| --- | --- |
| mock / stub / test double | "a pretend object we make ourselves" |
| fixture | "the starting data the test builds before it checks anything" |
| assertion | "the line that says what the answer should be" |
| tightly coupled | "these two things depend on each other too much" |
| refactor | "clean up the code without changing what it does" |
| edge case / boundary | "the tricky value right at the limit" |
| deterministic | "it gives the same answer every time" |
| regression | "something that worked before, and is broken now" |
| coverage | "how much of the code the tests actually run" |
| synthetic data | "fake data we invent just for testing" |
| pure function | "a small piece of code that takes numbers in and gives a number out" |

You may still teach the real word - but only **after** he understands the idea, and say it
once: "Programmers call this X. Now you know the word if you see it."

---

## Part 2 - Teach the kinds of tests

Idan already has 138 tests that pass. Say this to him clearly: **that is real, good work.**
Then explain what he has, and what is missing.

Teach these one at a time.

### 1. Small test (professionals say: unit test)

Checks **one small piece of code alone**. No database. No web page.
Very fast. When it fails, you know exactly which piece is wrong.

Comparison: testing one light bulb on the table, not the whole car.

### 2. Whole-flow test (professionals say: functional or integration test)

Checks **several pieces working together**. For example: send the web form, then look in the
database and check the correct booking was saved. Slower. When it fails, you must search to
find which piece broke.

Comparison: starting the car and driving it. You know something is wrong, but not what.

> **Important, and tell Idan honestly:** almost all of his 138 tests are this second kind. That
> is not a mistake - they are useful. But he has almost none of the fast, exact first kind.
> That is the gap this task fills.

### 3. Full journey test (professionals say: end-to-end, or E2E)

Follows **one complete real story** from start to finish, like a real customer:
customer asks for a price, system calculates options, quote is made, booking is created.
Slowest of all, but it proves the whole chain works together.

### 4. "Did it break?" tests (professionals say: regression tests)

**This is not a different kind of test.** This part is important - explain it clearly.

"Regression" just means: *something that worked before is broken now.*

**Every test above already does this job**, the moment it exists. It will shout if Idan breaks
that behaviour later.

So Idan does **not** need to build a separate set of "regression tests". His small tests and
whole-flow tests **are** the safety net. If you skip this explanation, he will build the same
tests twice for no reason.

### 5. Quick health checks (professionals say: smoke tests)

Very small, very fast checks that the system is alive and healthy: does it start, does the
database structure apply cleanly, does the admin page open. Cheap, and they catch big breakage
immediately.

### One thing to tell Idan before he runs anything

New programmers often worry about this, so say it without being asked:

> **The tests do not touch your real database.** Every time you run `manage.py test`, Django
> builds a **brand new empty database** just for the tests, uses it, and **deletes it** at the
> end. Your own data in `db.sqlite3` is never read and never changed.

This is also *why* tests must build their own data: the test database starts empty every single
time, so whatever a test needs, it has to create for itself.

---

## Part 3 - The main idea: tests must invent their own data

Teach this idea with the real problem that exists in this project today. Do not teach it in
theory - show him the actual file.

### The problem, in his own project

Some real supplier prices are written inside the database migration files. A "migration" is the
file that changes the shape of the database. Look at
`suppliers/migrations/0015_kaizen_cross_border_499.py` - it writes the real price `499.00` into
the database. `0017` writes a deposit of `250.00`, and `0018` a snow-chains price of `25.00`.

Say the good part first: the **big** price lists are **not** in the repository. They stay in the
ignored folder on Idan's computer and are loaded with the import commands. That was the right
choice. Only a few single prices ended up inside migration files - and those few are enough to
make tests fragile.

Now show Idan what happens next season:

1. Kaizen changes that price from 499 to 520.
2. Idan updates the price. Correctly. Nothing is broken.
3. **The tests fail anyway.**

Ask him: *"Is that a real problem in the code, or a false alarm?"*

It is a false alarm. And false alarms are dangerous, because after a few of them people stop
reading the test results. That is the worst thing that can happen to a set of tests.

### The rule

> **A test must build its own fake data. A test must never depend on real supplier prices.**

Use a small invented supplier with **round, easy numbers**, so Idan can check the maths in his
head:

| Thing | Real data (do NOT use in tests) | Fake data for tests |
| --- | --- | --- |
| Supplier | Kaizen Rent | `Test Rent` |
| Car group | `R / BUS - 9 seats automatic` | `TEST-CAR` |
| Price per day | 319 PLN | **100 PLN** |
| Extra item | Cross-border, 499 PLN | `TEST-EXTRA`, **50 PLN** |

Explain why the round number matters: with 100 PLN per day, Idan sees immediately that 4 days
must be 400 PLN. With 319 PLN he cannot check it in his head - so if the code gives a wrong
answer, he will not notice.

### Good news - his agent already did this once

Show him this test that already exists in `quotes/tests.py`:

```python
def test_kaizen_cross_border_offer_rate_is_499_per_rental(self):
    from types import SimpleNamespace
    extra = SimpleNamespace(...)
    old_rate = SimpleNamespace(...)
```

`SimpleNamespace` is a way to build a **pretend object** in one line. It looks like a real price
record, but it is not saved in the database and it is not real data. Tell Idan: this is exactly
the right technique, and now we will use it for all the money calculations.

### How to build the fake data - Idan decides

Give him the options, one line good and one line bad each, then **stop and let him choose**:

1. **Small helper functions inside the test file** (recommend this to start) - a function like
   `make_test_supplier()`. Good: plain Python, nothing new to learn. Bad: a little repeated
   code between files.
2. **Django fixtures** (data saved in a JSON file). Good: keeps data out of the code. Bad: easy
   to forget to update, and harder to see what a test depends on.
3. **`factory_boy`** (an extra tool to install). Good: powerful, used by professionals. Bad: a
   new tool to learn now. Suggest this **later**, not today.

---

## Part 4 - The mathematics needs its own tests (the most valuable part)

**Start here. Do this before anything else.**

The roadmap says a wrong formula "quietly costs real money"
(see `../architecture/architecture-and-roadmap.md`, section 5). "Quietly" is the dangerous
word: a wrong price does not crash anything. It just sends the customer the wrong number.

Right now every one of these calculations is only tested **through a web form**. That means
slow tests, and when one fails Idan cannot tell whether the maths is wrong or the form is
wrong. Test the maths **directly** instead.

### 4.1 Rental days - `config/rental_duration.py`

`calculate_rental_days(pickup, return)` is the perfect place to start: it takes two dates and
gives back a number. No database needed at all.

First explain the rule to Idan in his own business language: *the customer gets one free extra
hour at the end; after that hour, a new day is charged.* Then test it.

Use `SimpleTestCase` (not `TestCase`). It does not build a database, so these tests finish in
milliseconds. Explain that difference to him once.

Tests to write:

- a normal rental, exactly 3 days -> 3
- **exactly 24 hours** -> 1
- **exactly 1 hour late** (the free hour) -> must still be 1 day, NOT 2
- **1 hour and 1 minute late** -> must be 2 days
- return time equal to pickup time -> 1 (never zero, never free)
- return time **before** pickup time -> decide with Idan what should happen, then test it
- a rental crossing the clock change (Poland changes the clock twice a year)

Teaching point: the first test almost never finds a bug. The ones at the limit - exactly 1
hour, exactly 24 hours - are where the real mistakes hide. Ask Idan why he thinks that is.

### 4.2 Extra items price - `quotes/services.py`, function `_extra_price`

This function already takes a price record and a number of days, and returns a price. So it can
be tested with **pretend price records** (`SimpleNamespace`) and no database at all.

It has several different rules inside it. Each rule needs its own test, with round fake numbers:

- `PER_DAY`: 50 PLN per day, 4 days -> 200
- `PER_RENTAL`: 50 PLN, 4 days -> 50 (the number of days must NOT change it)
- `PER_DRIVER_DAY` with quantity 2: 50 PLN, 4 days, 2 drivers -> 400
- `FORMULA` with a base price plus a per-day price -> a hand-checked round number
- `FORMULA` with a fixed total for the whole rental -> the days must not change it
- **minimum price**: a price below the minimum must be raised to the minimum
- **maximum price**: a price above the maximum must be capped at the maximum
- quantity 2 doubles the result

Then ask Idan the useful question: *"Which of these rules would you notice if it broke, and
which one would send a wrong price to a customer without anyone seeing?"* The second kind is
exactly why these tests exist.

### 4.3 Booking totals - `bookings/models.py`

`_calculate_vehicle_price` and `recalculate_totals` produce the final number the customer pays.
With the fake 100 PLN car and the fake 50 PLN extra:

- car price = price per day x rental days
- total = car price + all extras
- a manual price typed by hand replaces the calculated price
- a manual price must have a reason (this rule already exists - keep it)
- an extra keeps the price it had when it was added, even if the supplier price changes later.
  Programmers call this a snapshot; explain it as "a photograph of the price at that moment".

### 4.4 Deposit - `suppliers/deposit_rules.py`

`default_deposit_amount(supplier_code, group_code)` also takes simple values in and gives a
number out, so it can be tested directly. Test each rule, and also the fallback case: an
unknown supplier or an unknown car group.

### 4.5 Prices with and without tax

Money in this system is stored as the price the customer pays, with tax included. Any place
that converts between "with tax" and "without tax" needs its own small test, with a round tax
rate so the numbers can be checked by hand.

Also test the rounding rule. Ask Idan to decide: when a result is 100.005, should it become
100.01 or 100.00? He must choose, because it is his money and his invoices. Then write the test
for his answer, and record the decision in `docs/decisions.md`.

### 4.6 The prices and words that are written twice

Some prices and all the Hebrew customer words are written **inside the code**, and some of them
are **also** in the database. When the same thing is written in two places, one of them wins - and
nobody knows which. [`03-move-rules-and-text-out-of-the-code.md`](03-move-rules-and-text-out-of-the-code.md)
is the task that fixes this. **This part is the tests that make that fix safe.**

Write these tests **now**, before task 03 starts. Explain to Idan why that order matters: a test
written before the change describes what *should* happen. A test written after the change only
describes what the code happens to do - which is not the same thing at all.

#### The test that fails on purpose (write this one first)

In `quotes/services.py` the function `_quoted_extra_price` returns a fixed `499` for one Kaizen
extra, and ignores the price in the database. So write this test:

- build a pretend price record with `amount_gross = 555`
- ask for the price of that extra
- the answer must be **555**

**This test will fail today.** That is correct and intended. Explain it to Idan clearly, or he will
think he broke something:

> A failing test is not always bad news. Sometimes it is the clearest way to write down a problem.
> This test says: *"the price must come from the database."* Today the code does not do that. When
> task 03 deletes the fixed number, this test turns green by itself - and that is the proof the fix
> worked.

Programmers sometimes mark a test like this so the whole run still looks green
(`@expectedFailure` in Python). Better here: **leave it red and do task 03 next.** A red test is a
job on the list. A marked test is a job everybody forgets.

#### Do NOT test the Hebrew words themselves

This is the important idea in this part, so go slowly with it.

It is tempting to write: *"the offer line must say `כיסא תינוק / בוסטר`."* **Do not.** That test
breaks every time Idan improves the wording - and improving the wording is exactly what he should
be free to do. That is a false alarm, the thing Part 3 warned about.

Test the **path**, not the words. Like this:

- in the fake data, give the extra the pretend name **`TEST-NAME-HE`**
- build the offer
- the line must show **`TEST-NAME-HE`**

Now think about what this test proves. `TEST-NAME-HE` is not written anywhere in the code, so the
only way it can appear on the offer is if the offer **read it from the data**. So the test proves
the connection works, and it stays green no matter how many times Idan rewrites the real Hebrew.

Ask Idan the question that makes it stick: *"If the code had the words written inside it, could
this test ever pass?"* No. That is the whole trick.

Use the same trick for every word a customer sees: the extra names, the "what is included" list,
the optional items list. One fake word in, the same fake word out.

#### The supplier rules

`quotes/services.py` has rules written as supplier codes - for example *this supplier plus an
airport pickup means add the airport fee*, and *a baby seat is called `CHILD_SEAT` at one supplier
and `BABY_SEAT_BOOSTER` at another*.

These rules are correct today. The problem is only that they live in the code, where Idan cannot
change them. Task 03 moves them into the database - and while moving them, it is very easy to
break one quietly.

So write a small test for **each rule as it behaves today**:

- a supplier that delivers to a city address -> the delivery item is added
- a supplier that does not -> it is **not** added
- pickup at the airport, for the supplier with an airport fee -> the fee is added
- the same supplier, pickup not at the airport -> **no** fee
- a customer asks for a baby seat -> each supplier's own baby-seat item is found
- a customer asks for something a supplier does not have -> nothing is added, and **nothing
  crashes**

Tell Idan what these tests are for, in one line: *they are the promise that task 03 changes only
where the rules are kept, not what they do.*

Note the last one. Ask him: *"What should happen when a supplier simply does not sell wifi?"* The
answer is *nothing, quietly* - and a test should say so, because after task 03 that case will
depend on a missing row in a table instead of a missing key in a list.

#### Optional: a test that guards the rule itself (Idan decides)

There is a kind of test that reads the code file and checks the rule is still being followed - for
example, *`quotes/services.py` must not contain the text `"01"`*. After task 03 that would be true,
and the test would stop anyone putting a supplier code back into the code later.

Give Idan both sides honestly:

- Good: it protects the decision, not just the behaviour. Six months from now, in a hurry, it is
  very tempting to add one small `if supplier_code == ...`. This test says no.
- Not so good: it is a test about the shape of the code, not about the business. It can be
  annoying, and a beginner can find it confusing when it fails.

Recommend it **only after task 03 is finished**, and only if he wants it. It is his choice.

### 4.7 Commissions - not yet, but plan for it

The commission calculations (owner, sub-agent, employee) are not built yet. When Idan builds
them, the rule is: **write the calculation as a small separate function that takes numbers in
and gives a number out**, then test it directly with round fake numbers - before connecting it
to any screen.

Also teach him this business rule from the roadmap: commissions are calculated on the **final
settled amount**, not on the first quoted price. A test must prove that, because those two
numbers are often different, and mixing them up costs real money.

---

## Part 5 - The four steps of work, in order

Do **one step at a time**. Do not start the next until the current one runs and Idan can
explain it.

**Step 1 - Small tests for the mathematics.** All of Part 4 above. Highest value, fastest to
run, easiest to understand. Start here.

**Step 2 - Fix the existing whole-flow tests.** Do not rewrite the 138 tests. Only change the
places where a test depends on real data that came from the migration files - for example the
line in `quotes/tests.py` that reads whatever car comparison classes already exist in the
database. Make those tests build their own fake data instead. Keep the test names: they are
genuinely good, because they describe the business rule and not the code.

**Step 3 - One full journey test.** One is enough to begin. It should follow: customer inquiry,
price options, quote, accepted, booking - all with fake data.

Let Idan choose how:

- **Django test client** (recommend this now) - already installed, fast, no browser. Tests the
  server. Good: nothing new to install. Bad: does not test what happens in the browser.
- **Playwright** (later, optional) - opens a real browser and clicks like a person. Good: tests
  the real screens too. Bad: slower, and a new tool to learn.

**Step 4 - Quick health checks.** Small and cheap. Idan has already started this without
knowing the name for it: `tests/test_project_setup.py` checks that the admin address is
connected, and it is the one test in the whole project that uses `SimpleTestCase`. Point that
out to him - it is a good instinct, and it belongs in this step. Now add the rest:

- `manage.py check` reports no problems
- **no forgotten database change** - `makemigrations --check --dry-run`. Explain why this
  matters: changing a model and forgetting to create the migration file is the most common
  beginner mistake, and it still works fine on Idan's own computer while breaking everywhere
  else.
- the admin login page opens successfully

---

## Part 6 - How to teach each step

For every step above, follow this loop. Do not skip point 4 - it teaches the most.

1. **Explain the idea first**, in three or four short lines, with one small example.
2. **Write ONE test together.** Idan types it, or reads it and approves it line by line.
3. **Run it. Let it pass.** Show him the green result.
4. **Now break the code on purpose.** Change 100 to 200, or remove the free hour. Run again.
   Let Idan **read the failure message himself.** Ask him: "What is this message telling you?"
   This is the single best way to understand what a test actually does.
5. **Undo the break. Run again. Green.**
6. **Ask him to explain the test in his own words.** If he cannot, explain it differently and
   repeat.
7. Only then move to the next test.

Never write twenty tests silently and say "done". That teaches nothing, and Idan will not be
able to look after them later.

---

## Part 7 - A decision Idan needs to understand and make

Real prices live inside the migration files (Part 3 above). That is a real design problem, not
only a testing problem: every time a supplier changes a price, someone must write a new
migration file, and the price history ends up scattered across many files.

Explain the situation simply, then give him the options and **let him decide**:

1. **Leave it for now**, and only stop the tests depending on it (this task). Good: no extra
   work today. Bad: the problem stays.
2. **Move prices out of the migrations** into a data file or the admin screens, so prices are
   data that Idan edits himself, not code that has to be written. Good: the right place for
   business data. Bad: real work to move it now.
3. **Same as option 2, but later**, as its own task after the tests are safe. Often the
   sensible order.

Write his decision and his reason in `docs/decisions.md`, the same way he did for the database
and the framework.

---

## Definition of done

- [ ] Idan can explain, in his own words: a small test, a whole-flow test, a full journey test.
- [ ] Idan can explain why "regression" is a reason for testing, not a separate kind of test.
- [ ] Idan can explain why tests use fake prices instead of the real supplier prices.
- [ ] `config/rental_duration.py` has direct small tests, including exactly 1 hour and exactly
      24 hours.
- [ ] `_extra_price` has direct small tests for every calculation type, plus minimum and
      maximum.
- [ ] Booking totals and the deposit rule have direct small tests with round fake numbers.
- [ ] No test depends on a real supplier price any more.
- [ ] A test proves that an extra price comes from the database, not from a number written in the code. (It stays red until task 03 - that is intended.)
- [ ] Tests about words a customer sees use an invented word (`TEST-NAME-HE`), never the real Hebrew wording.
- [ ] Every supplier rule that lives in the code today has its own small test, written *before* task 03 moves it.
- [ ] One full journey test exists.
- [ ] The health checks exist, including the forgotten-migration check.
- [ ] Everything passes: `uv run python manage.py test`.
- [ ] `docs/decisions.md` records Idan's decisions from this task: how to build fake data, how
      to run the journey test, the rounding rule, and what to do about prices in migrations.

---

## What NOT to do

- Do **not** delete Idan's existing 138 tests. They have real value. Improve them.
- Do **not** write any new test that checks a real supplier price.
- Do **not** install `factory_boy`, `pytest` or Playwright unless **Idan chooses** to.
- Do **not** test the exact wording of text on a page, unless that exact wording is a real
  business requirement. Those tests break every time someone edits a sentence, for no reason.
- Do **not** chase a percentage number for how much of the code the tests run. Aim at the risky
  parts: **money and dates**.
- Do **not** rush ahead and build all four steps at once. One step, understood, then the next.
