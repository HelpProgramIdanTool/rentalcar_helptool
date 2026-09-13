# Task 04 - Get Idan ready to decide how the money works

**This file is a task brief for the AI agent.** Idan will read it too, so use simple, everyday
English. Follow the language rules in [`../../AGENTS.md`](../../AGENTS.md).

---

## STOP - read this before anything else

**This task builds nothing. No models. No fields. No migrations. No calculations.**

The only thing that gets created is **one document**, written by Idan:
`docs/questions-for-mentor.md`.

Idan is going to discuss the money model with his mentor - a programmer with 25 years of
experience. The purpose of this task is that Idan walks into that conversation **understanding the
problem**, with his own opinion, able to explain it in his own words.

If you build the money model for him, you have taken the conversation away from him, and the task
has failed. It has failed even if the code is perfect.

If Idan says *"just build it"*, say no, and give him the honest reason:

> The way money is stored is the hardest thing to change later. Everything else in this system can
> be changed in an afternoon. This one cannot: once real bookings and real invoices exist, changing
> how money is stored means changing history, and history is what you show the tax office. So this
> is the one decision worth talking about **before** writing code, not after.

That is a real engineering idea, and it is worth Idan hearing it in exactly those words.

---

## Part 1 - Words to use

| Do not say | Say this |
| --- | --- |
| gross / net | "the price with the tax inside" / "the price before the tax is added" |
| VAT-inclusive | "the tax is already inside this number" |
| settlement | "the money that is really paid to the supplier at the end of the month" |
| reconciliation | "checking that the money paid matches the money agreed" |
| audit trail | "being able to see later what the number was, and when it changed" |
| immutable | "written once, never changed afterwards" |
| schema / data model | "how the information is stored" |

---

## Part 2 - Teach the first idea: with tax, or without tax

Do not talk about the system yet. Start with one small example, with round numbers.

> A car rents for **123 PLN**. VAT in Poland is 23%.
>
> - If 123 is the price **with the tax inside**, then the rental is 100 and the tax is 23.
> - If 123 is the price **before tax**, the customer pays **151.29**.
>
> Same number written down. Two different amounts of money.

Now ask Idan two questions, and wait for his answers:

1. *"When your supplier sends you a price of 319 - is the tax inside that number or not?"*
2. *"When you write a price for your customer - is the tax inside it?"*

Then show him what his system does today. Every money field in the code ends with `_gross` - for
example `total_gross`, `actual_cost_gross`. Explain that this means: *every number in this system is
the price with the tax already inside.* There is **no** field anywhere that stores a price before
tax.

**Say clearly that this is not a mistake.** For a business that quotes customers a final price, this
is a sensible choice, and it keeps the code simple. But it has one consequence, and Idan must
understand it:

> If a number with the tax inside is the only number you store, then to show the tax separately you
> must calculate it backwards - and rounding backwards does not always give exactly the number the
> supplier wrote on their invoice.

Ask him: *"Do you have to give your customers an invoice showing the VAT separately?"* His answer to
that one question decides a lot. Write down whatever he says - it goes in the document.

### The unused table

Show him `taxes/models.py`. There is a `TaxRate` table - VAT per country. Then show him this:
**nothing in the whole system uses it.** No other file mentions it.

Ask him: *"You built this table. What were you planning to do with it?"*

This is a good moment, so let it be a good moment - not a criticism. He built the right table
because his architecture document says VAT should be configurable. The code that uses it simply
does not exist yet. That is normal. Tell him the useful lesson:

> An empty table is a **question you asked yourself and did not answer yet.** Finding one is a
> useful signal, not a mistake.

---

## Part 3 - Teach the second idea: the price changes three times

This is the centre of the task. Teach it with **one story**, with round numbers. Do not use the
words "price levels" until the end.

> **March.** A customer asks for a car for a week. You send an offer: **1200 PLN**.
>
> **April.** He agrees, but he wants a different pickup time, and you give him a small discount.
> The booking is confirmed at **1150 PLN**.
>
> **May.** The month ends. The supplier sends you their statement. Their figure for this rental is
> **1100 PLN** - because the customer returned the car early, and there was a small correction on
> the delivery fee.
>
> So: **1200**, then **1150**, then **1100**. Three different numbers, all true, all for the same
> rental.

Now ask Idan the questions. **Let him answer each one before you continue.**

1. *"How much money did you actually earn on this rental?"*
2. *"Your employee gets a commission on this rental. Which of the three numbers is it calculated
   from?"*
3. *"The customer already paid you 1150. The supplier only charges 1100. Whose 50 is it?"*
4. *"If someone asks you in November what happened on this rental - can you still see all three
   numbers?"*

Question 4 is the one that turns this into a **programming** problem. Explain why:

> If the system stores only one number and changes it each time, then by May the 1200 and the 1150
> are gone. Nobody can check anything, and nobody can prove anything. So the system does not need
> **one** price. It needs to remember **all three**, and keep them.

Now show him that he already knew this. His own roadmap
([`../architecture/architecture-and-roadmap.md`](../architecture/architecture-and-roadmap.md)) says
there are three price levels - quote, confirmed, and settlement - and that commissions are
calculated on the **settled** amount, not on the quoted one.

Then show him the code as it is today:

- the quote price exists
- the booking price exists
- `actual_cost_gross` on the booking is the closest thing to the settlement figure
- **no commission calculation exists anywhere** in the code

Tell him plainly: *he is not behind.* Commissions are a later milestone. This conversation is
happening **early on purpose**, which is the right time for it.

---

## Part 4 - Teach the third idea: the difference is the business

Ask Idan the question that a programmer cannot answer for him:

> *"When the supplier's final figure is different from the confirmed price - is that normal, or is
> it a problem to investigate?"*

Both answers are legitimate, and they lead to **different systems**:

- If it is **normal**, the system needs to store both numbers and simply show the difference. The
  difference is part of the profit.
- If it is a **problem**, the system needs to notice it and tell somebody - a screen showing every
  rental where the two numbers disagree.

Explain the general idea behind this, because it applies to everything he will ever build:

> The code cannot decide this. Only the person who runs the business can. A programmer who guesses
> here builds the wrong system very efficiently.

That sentence is worth Idan remembering for the rest of his career.

---

## Part 5 - Idan writes the document

Now Idan writes `docs/questions-for-mentor.md`. **He writes it, not you.** You may fix his English,
and you may point out a question he forgot. Do not write his opinions for him.

The document has one section per question, and each section has **three** lines:

1. **The question.**
2. **What I think the answer is** - his own opinion.
3. **Why** - his reason, one line.

Line 2 is the important one. Explain why to him honestly:

> A mentor with 25 years of experience can answer any of these questions in one minute. What he
> **cannot** do is know your business. And a conversation where you bring your own answer is a
> completely different conversation from one where you bring only questions. Bring your answer, even
> if you are not sure. If it is wrong, you will learn much more from hearing why.

The questions to cover:

**About tax**

1. Do I have to give customers an invoice that shows the VAT separately?
2. Do I need to store the price before tax, or is it enough to calculate it when needed?
3. Do different countries mean different VAT rates for me in practice? (This is what the unused
   `TaxRate` table was for.)

**About the three prices**

4. Should the system keep the quoted price, the confirmed price and the settled price all three,
   forever?
5. Is a settled price different from the confirmed price normal, or something to investigate?
6. Who keeps the difference when the supplier charges less than the customer paid?

**About commissions**

7. Which number is the employee commission calculated from - the confirmed price, or the settled
   price?
8. Is the commission a percentage of the whole price, or only of my profit?
9. Are there sub-agents or partners who also get a commission? On which number?

**About rounding**

10. When a calculation gives 100.005 - does it become 100.01 or 100.00? (This links to task 01,
    section 4.5. The same decision, in both places.)

**Bring evidence.** Ask Idan to bring, printed or on screen:

- one real supplier settlement statement for a month
- one real invoice he gave a customer
- one rental where the settled amount was **not** the same as the confirmed price

**Important:** these are private business documents. He shows them to his mentor. He does **not**
commit them to the repository - see [`02-secrets-and-settings.md`](02-secrets-and-settings.md).
Remind him of that rule here, because it is exactly the kind of moment when it gets broken.

---

## Part 6 - Rehearse it

Do this last, and do not skip it. It is the part that makes the difference.

**You play the mentor.** Ask Idan the hard questions and make him answer out loud, in his own words,
with no notes:

- *"Show me the three prices in your system. Where is each one stored?"*
- *"A customer's booking was 1150 and the supplier charged 1100. Show me where the system knows
  that."*
- *"Why did you build a VAT table and then never use it?"*
- *"Your employee wants to know why his commission is smaller than he expected. What do you show
  him?"*
- *"It is next February. Show me what the rental in March last year cost you."*

When he cannot answer one, **do not answer it for him.** Send him back to Part 3 and let him find
it. Then ask again.

Finish only when he can explain the whole thing in about **five minutes**, without reading.

Then tell him the last thing, because it matters more than the money model:

> You are not going to your mentor to be told what to do. You are going to describe a problem you
> understand, offer what you think the answer is, and ask whether you are missing something. That is
> what an experienced programmer does too - the questions are just bigger.

---

## Definition of done

- [ ] **No code was written.** No new model, no new field, no migration, no calculation.
- [ ] Idan can explain "the price with the tax inside" and "the price before tax" with his own
      example.
- [ ] Idan can tell the three-prices story with his own numbers, and say where each one is stored
      today.
- [ ] Idan can explain why the system must keep all three, and not just the newest one.
- [ ] Idan knows what `taxes.TaxRate` was for, and that nothing uses it yet.
- [ ] `docs/questions-for-mentor.md` exists, written by Idan, with **his own proposed answer** under
      every question.
- [ ] Idan has the three real documents ready to show - and they are **not** in git.
- [ ] Idan got through the rehearsal in Part 6 without notes.

---

## What NOT to do

- Do **not** build any part of the money model. Not "just a small start". Not "only the field".
- Do **not** write Idan's answers for him. An answer he did not think of is worth nothing in the
  conversation.
- Do **not** let him arrive with only questions. Every question needs his own attempt at an answer.
- Do **not** use the words *gross*, *net*, *reconciliation* or *schema* without the plain-English
  version from Part 1.
- Do **not** commit a real supplier statement, a real invoice, or a real customer name to the
  repository.
- Do **not** tell him he made mistakes. Three prices instead of one is a thing experienced teams get
  wrong too. He is asking the question at the right time, which is the whole point.
