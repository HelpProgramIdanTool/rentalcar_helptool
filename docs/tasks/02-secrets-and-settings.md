# Task 02 - Keep secrets out of the code (and teach Idan why)

**This file is a task brief for the AI agent.** Idan will read it too, so use simple, everyday
English. Follow the language rules in [`../../AGENTS.md`](../../AGENTS.md).

**Two goals. Both must happen:**

1. Move the settings that must stay private out of the code.
2. **Teach Idan the rule**, so he never puts a password in code again.

---

## Part 0 - Start by telling Idan he did nothing wrong

This is important. Do not make him feel he made a mistake.

The file `config/settings.py` was **created by Django itself**, with the command
`django-admin startproject`. Every Django project in the world starts exactly like this. The
settings are correct **for learning on your own computer**. They only become a problem **on the
day the system goes on the internet**.

So this task is not "fix your mistake". It is "learn the step that every project has to do
before it goes live".

**Nothing bad is happening right now.** The system is not on the internet. Nobody can reach it.
There is no customer data in it. Say this clearly, so Idan does not worry.

---

## Part 1 - Words to use with Idan

Add these to the list in `AGENTS.md`:

| Do not say | Say this |
| --- | --- |
| environment variable | "a note the computer holds for the program, kept outside the code" |
| rotate the key | "throw the old key away and make a new one" |
| production | "the real system on the internet, that real customers use" |
| information disclosure | "the page shows people things they should not see" |
| credentials | "the username and password" |
| commit history | "the list of every change ever saved in git" |

---

## Part 2 - Teach the idea first (no code yet)

### 2.1 What is in the file today

Show him these three lines in `config/settings.py`:

```python
SECRET_KEY = 'django-insecure-%)+8wlf(...)'   # line 23
DEBUG = True                                   # line 26
ALLOWED_HOSTS = []                             # line 28
```

Point out the word **`django-insecure-`** at the start of the key. Django puts that word there
on purpose. It is Django saying: *"this key is only for your own computer, never for the real
system."* Idan did not choose that word - Django wrote it as a warning.

### 2.2 What `SECRET_KEY` actually does

It is **not** a password to log in with. It is the key Django uses to **sign** things - to put
its own mark on them, so it can tell later that it made them.

Use this comparison:

> `SECRET_KEY` is like the stamp a notary uses on an official paper. The paper is not secret.
> But **anyone who has the stamp can make a paper that looks official.**

What Django signs with it:

- The **login note** in your browser (programmers call it a session cookie). It is a small note
  your browser keeps that says "this visitor is already logged in as Idan". Django signs the
  note so that a visitor cannot write their own note.
- **Password reset links** sent by email.
- Other signed values.

So the danger is: someone who knows the key can **write their own login note** that says "I am
the boss user" - and Django will believe it. **No password needed.** They would see everything:
customers, prices, bookings.

Ask Idan: *"If someone could write their own login note, would your password protect you?"*
The answer is no. That is the whole point of the lesson.

### 2.3 Why "public repository" means "public forever"

The repository is public - anyone on the internet can read it. And git keeps **every old
version** of every file. So:

> Even if you delete the key from the file today, the old version stays in the history and
> anyone can still read it.

This gives the rule that Idan must remember:

> **A secret that went into a public repository is not a secret any more. You cannot hide it
> again. You must throw it away and make a new one.**

Moving the key to a different place is **not enough**. It has to be **replaced**.

### 2.4 Why `DEBUG = True` is actually the bigger problem

Explain what `DEBUG = True` does: when something goes wrong, Django shows a big yellow error
page. On your own computer that page is **very helpful** - it tells you exactly what broke.

But on the internet, that same page shows **the visitor**:

- the code of the file that broke,
- the values inside it at that moment (a customer name, a price, sometimes a password),
- the list of settings - **including the secret key**,
- the database queries that ran, and the folder names on the server.

So on a real server, the error page hands out the secrets by itself. Someone does not even need
to read the repository.

And it is easy to make an error happen on purpose - for example by typing a nonsense date into
a form.

`ALLOWED_HOSTS = []` makes it worse: while `DEBUG` is on, Django accepts requests claiming to
come from **any** web address, which lets someone send password reset emails pointing at
**their** website instead of yours.

---

## Part 3 - Let Django tell him what is wrong (do this before any fix)

This is the best teaching moment in the whole task. Do not skip it, and do not read the answer
out to him first.

Ask Idan to run:

```bash
uv run python manage.py check --deploy
```

Django has its **own** checklist for going live. It will print a list of warnings - about the
secret key, about `DEBUG`, about cookies, and more.

Then:

1. Let Idan **read the list himself.**
2. Ask him: *"Pick one warning. What do you think it means?"*
3. Explain the ones he asks about, in short lines. Do not explain all of them.
4. Tell him the useful part: **this command is the answer to "am I ready to go live?"** He can
   run it any time, and it is a normal step before every real deployment.

This teaches him to ask the tool instead of asking a person. That is worth more than the fix
itself.

---

## Part 4 - The fix, one small step at a time

### 4.1 First decision - how will the computer hold the private values? (Idan chooses)

Give the options, one line good and one line bad, then **stop and let him choose**:

1. **A `.env` file plus the `python-dotenv` package** (recommend this). Good: the private values
   live in one small file on his computer, easy to see and edit, and it works the same on
   Windows and on a server. Bad: one extra package to install (`uv add python-dotenv`).
2. **Set the values in the terminal each time** (no extra package). Good: nothing to install.
   Bad: on Windows he must set them again in every new terminal window, and he will forget - and
   then the system will not start.
3. **`django-environ`** (a bigger package that does the same and more). Good: converts types for
   you. Bad: more to learn, and he does not need the extra features yet.

The rest of this task assumes he chose option 1. Adjust if he chooses differently.

### 4.2 Two files, and the difference between them

This part is the heart of the lesson, so go slowly.

- **`.env`** - holds the **real** private values. It is already in `.gitignore`, so git will
  never save it. It **never** goes into the repository.
- **`.env.example`** - holds the same **names**, but with fake values. This one **does** go into
  the repository.

Ask Idan why the second file is useful. The answer: if his computer breaks, or another person
joins, they need to know **which** values are needed - just not what they are. Comparison: it is
like a list of the keys on a keyring ("front door", "office"), without the keys themselves.

`.env.example` should look something like this:

```
DJANGO_SECRET_KEY=put-your-own-long-random-key-here
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=
```

### 4.3 Make a new key, and throw the old one away

Explain first: the old key is public, so it is finished. It cannot be saved. Make a new one:

```bash
uv run python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Put the new key in `.env` - **never** in `settings.py`, and **never** paste it into a chat.

Tell him one honest, useful thing about timing:

> Replacing the key logs out everyone who is logged in, and stops any password-reset emails that
> were already sent from working. **Today that costs nothing** - the only person logged in is
> Idan on his own computer. Next year, with real staff using it, the same change is a small
> planned interruption. **So doing it now is free. Doing it later is not.**

That is a real engineering idea: some jobs get more expensive the longer you wait. Worth saying
to him in exactly those words.

### 4.4 Change the three lines in `config/settings.py`

Something close to this. Let Idan type it, and explain each line as he does:

```python
import os
from dotenv import load_dotenv

load_dotenv(BASE_DIR / ".env")   # read the private values from the .env file

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",") if h]
```

Explain the small but important choices:

- `os.environ["DJANGO_SECRET_KEY"]` with **no** spare value on purpose. If the key is missing,
  the system **refuses to start**. Explain why that is good: a loud failure now is much better
  than a system that quietly runs with a key that everybody knows.
- `DEBUG` is **off** unless the note says `1`. The safe answer is the default. If Idan forgets
  to set anything on the real server, he gets the **safe** behaviour, not the dangerous one.

**Second decision for Idan** - there is a real trade-off here, so let him choose:

- **No spare value** (recommended): forgetting the key stops the system immediately. Safe, but
  he must have a `.env` file to work locally.
- **A spare value for his computer**: he can always run it, but if he forgets the note on the
  real server, the real system quietly runs with a key that is written in the code. That is the
  exact problem we are fixing.

Ask him which one he prefers and **why**. His reason matters more than his answer.

### 4.5 Check nothing broke

```bash
uv run python manage.py check
uv run python manage.py test
uv run python manage.py runserver
```

All 138 tests must still pass. Then log in to the admin again - and point out that he had to
log in **again**, because the login note was signed with the old key. That is not a bug: it is
the proof that replacing the key worked. Let him **see** the idea instead of only hearing it.

### 4.6 The settings that only matter with a real web address

Do **not** do this part yet. Explain that it exists, and stop.

When the system goes on a real address with `https`, a few more settings are needed - to make
the browser send the login note only over a safe connection, and never over a plain one. The
`check --deploy` command from Part 3 lists them by name.

Tell Idan the rule: **do this on the day you deploy, not before.** Turning those settings on now
would only break his own computer, because his computer does not use `https`.

---

## Part 5 - Do NOT try to clean the git history

Idan (or the agent) may want to erase the old key from the history. **Do not.**

Explain why, in plain words:

- It means rewriting every saved change in the project. It is easy to lose work.
- Copies already exist elsewhere - on GitHub servers, in anyone's copy of the repository.
- And it is **not needed**: once the key is replaced, the old key opens nothing. It is a key to
  a lock that no longer exists.

The lesson: **replacing the secret solves the problem. Hiding it does not.** Real teams work
this way too - they rotate, they do not rewrite history.

---

## Part 6 - The next secrets Idan will meet (warn him now)

Today only one secret exists. Soon there will be more. Tell him now so he recognises them:

1. **The email password.** `config/settings.py` currently has `MAILERS` set to the *console*
   backend - meaning emails are only printed on the screen, not sent. When Idan reaches the
   milestone for sending emails to suppliers, he will need a real mail server username and
   password. **That goes in `.env`.** Never in the code.
2. **The real database password**, if he later moves from SQLite to an online database
   (see [`../guides/01-choosing-a-database.md`](../guides/01-choosing-a-database.md)).
3. **Real customer data and supplier price lists.** These are already protected by
   `.gitignore` - `supplyer price lists/`, `input/`, `output/`, `*.db`, `*.sqlite3`. Tell him
   clearly that he got this part **right**, and that it is the more serious one: a password can
   be replaced in one minute, but a customer's name, phone number and passport number
   **cannot**. Once those are public, they stay public. In Europe there are also laws about
   this.

So the rule to remember, in one line:

> **The code goes into git. The secrets go into `.env`. Real customer data never goes into git
> at all.**

---

## Part 7 - Optional: make the rule automatic (only if Idan wants it)

`manage.py check --deploy` works, but somebody has to remember to run it.

If Idan would like the project to check itself, offer this - and connect it to what he learned in
[`01-build-the-test-safety-net.md`](01-build-the-test-safety-net.md): write a small function that
takes values in and gives an answer out, then test it directly.

For example, a function that answers *"are these settings safe to put on the internet?"* - it
receives `debug`, the secret key and the allowed addresses, and returns a list of reasons why
not. It needs no database, so it is a **small test**, and it runs in milliseconds:

- `DEBUG` is on -> not safe
- the key starts with `django-insecure-` -> not safe
- the list of addresses is empty -> not safe
- all good -> empty list, meaning no problems

This is optional. Django's own check already covers it. But it is a nice, small, real example of
the idea from Task 01, so offer it and let Idan decide.

---

## When to do this task

Idan's own roadmap already has this as milestone **M8** ("security"), which is the right place.
But split it, and explain the split to him:

- **Now, worth doing (about half an hour):** Parts 2, 3, 4. Moving the values out and making a
  new key is cheap today and free of consequences. And Part 3 teaches him something he will use
  for the rest of his career.
- **On the day of deployment:** Part 4.6 (the `https` settings), plus running
  `check --deploy` again until it is quiet.

**Do not** let this task interrupt building features. It is short. Do it once, properly, and go
back to the roadmap.

---

## Definition of done

- [ ] Idan can explain, in his own words, what `SECRET_KEY` is used for - and that it is not a
      login password.
- [ ] Idan can explain why a secret in a public repository must be **replaced**, not hidden.
- [ ] Idan can explain why `DEBUG = True` is dangerous on a real server.
- [ ] Idan has run `manage.py check --deploy` himself and read the output.
- [ ] `SECRET_KEY`, `DEBUG` and `ALLOWED_HOSTS` are read from outside the code.
- [ ] A **new** secret key exists, and the old one is no longer in use anywhere.
- [ ] `.env` exists on his computer and is **not** in git (`git status` must not show it).
- [ ] `.env.example` **is** in git, with names only and no real values.
- [ ] `uv run python manage.py test` - all tests still pass.
- [ ] `README.md` says how to create the `.env` file, so a future reader knows.
- [ ] `docs/decisions.md` records his two decisions: how the private values are held
      (`.env` / terminal / other), and whether there is a spare value for the key.

---

## What NOT to do

- Do **not** rewrite or clean the git history. See Part 5.
- Do **not** put the new key anywhere except `.env`. Not in `settings.py`, not in a chat
  message, not in a screenshot.
- Do **not** commit `.env`. Check `git status` before every commit.
- Do **not** turn on the `https` settings while working on his own computer - they will only
  break it and confuse him.
- Do **not** make Idan feel this was his mistake. Django wrote those lines, and every project
  goes through this step.
- Do **not** do this whole task silently and report "fixed". The teaching **is** the task.
