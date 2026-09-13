# Task 00 - Point git at the project's new home (and teach Idan what a remote is)

**This file is a task brief for the AI agent.** Idan will read it too, so use simple, everyday
English. Follow the language rules in [`../../AGENTS.md`](../../AGENTS.md).

**Two goals. Both must happen:**

1. Change one setting so Idan's computer talks to the project's new address on GitHub.
2. **Teach Idan what that setting is**, so the word "remote" stops being a mystery.

This is the smallest task in the whole project. That is exactly why it is a good first one:
it is real, it takes five minutes, nothing can break, and at the end Idan understands a piece
of git he uses every single day without knowing what it does.

---

## Part 0 - What happened (tell him this first)

The project moved on GitHub. It used to live here:

```
https://github.com/idancaliber/rentalcar_helptool
```

It now lives here:

```
https://github.com/HelpProgramIdanTool/rentalcar_helptool
```

**Idan did nothing wrong, and nothing is broken.** The project, all the code, and every change
he ever saved are all safe at the new address. Nothing was lost.

His computer, though, still has the **old** address written down. Right now that still works,
because GitHub is being helpful and quietly forwarding him to the new place. But it should be
fixed properly, and Part 2 explains why.

---

## Part 1 - Words to use with Idan

| Do not say | Say this |
| --- | --- |
| remote | "the address on the internet where the project is kept" |
| `origin` | "the nickname git uses for that address" |
| clone | "the copy of the project on your own computer" |
| fetch | "ask the internet copy if anything is new" |
| push | "send your saved changes up to the internet" |
| redirect | "GitHub sending you to the new address automatically" |
| URL | "a web address" |

---

## Part 2 - Teach the idea first (no commands yet)

### 2.1 There are two copies of this project

Make sure he sees this clearly, because everything else depends on it:

- One copy is **on his computer**, in his project folder. This is the one he edits.
- One copy is **on GitHub**, on the internet. This is the one that is safe if his laptop dies.

They are separate. They do not update each other by magic. `git push` is Idan choosing to send
his changes from his computer up to GitHub.

**Ask him to say that back in his own words before moving on.**

### 2.2 So how does his computer know where to send them?

It has the address written down in a small settings file, inside the hidden `.git` folder.

Git calls that saved address a **remote**. And it gives the main one a nickname: **`origin`**.

So `git push origin main` means, in plain words:

> "Send my saved changes to the address I nicknamed `origin`."

That is the whole idea. `origin` is not a magic word. It is just a nickname for a web address,
and Idan can look at it and change it.

### 2.3 Why fix it, if it works today?

This is the part worth understanding, so do not skip it.

When a project moves, GitHub leaves a **forwarding note** at the old address. So when Idan
pushes to the old address, GitHub says *"that moved, I will pass it along for you"* - and it
works. He may have seen that message:

```
remote: This repository moved. Please use the new location:
remote:   https://github.com/HelpProgramIdanTool/rentalcar_helptool.git
```

That message is GitHub asking politely to be updated.

Here is the real danger, and it is worth telling him plainly: **the forwarding note stops
working the moment somebody creates a new project at the old address.** If anyone ever makes a
new repository called `idancaliber/rentalcar_helptool`, Idan's pushes would stop arriving here -
and, worse, would start going somewhere else entirely.

It is unlikely. But the fix takes five minutes, and it is the difference between "works for now"
and "correct".

**A good question to ask him:** *"Where do you think your changes would go if someone made a new
project with the old name?"* Let him work it out. That is the moment the idea lands.

---

## Part 3 - Let him look before changing anything

Always look first. Have **Idan** type this, not you:

```bash
git remote -v
```

He will see something like:

```
origin  https://github.com/idancaliber/rentalcar_helptool (fetch)
origin  https://github.com/idancaliber/rentalcar_helptool (push)
```

Walk him through what he is reading:

- `origin` - the nickname.
- the address - where it currently points. **This is the old one.**
- `(fetch)` - the address used when asking for new changes.
- `(push)` - the address used when sending his changes.

They are listed separately because git *allows* them to be different addresses. For this project
they should be the same, and they are.

---

## Part 4 - The fix (one command)

Have Idan type it himself:

```bash
git remote set-url origin https://github.com/HelpProgramIdanTool/rentalcar_helptool.git
```

Read the command with him, piece by piece, so it is not just copied magic:

- `git remote` - "I want to work with the saved addresses"
- `set-url` - "change the address"
- `origin` - "the one nicknamed origin"
- the long address - "to this"

### 4.1 Check it worked

```bash
git remote -v
```

Both lines should now show `HelpProgramIdanTool`. Nothing else changed. **His files were not
touched, and his saved history was not touched** - say that out loud, because "changing git
settings" sounds frightening when you are new.

### 4.2 Check the new address really answers

```bash
git fetch origin
```

If this finishes quietly, with no error and no "This repository moved" message, it worked.

**Teach him what quiet means here.** `git fetch` only asks *"is there anything new?"* - it does
not change any of his files. Saying nothing means "nothing new, all good". In git, silence is
usually success.

### 4.3 The real test comes next time he pushes

Next time Idan runs `git push`, the `This repository moved` message should be **gone**. Point it
out when it happens, so he connects the fix to the result.

---

## Part 5 - Two things NOT to do

### Do not delete the folder and download it again

Idan may suggest just deleting his project folder and downloading a fresh copy from the new
address. It would work. **Talk him out of it**, and explain why:

- Any work he has not yet pushed would be **gone forever**.
- It teaches him nothing. Downloading again hides the problem; changing the address shows him
  how git actually works.

One command is better than starting over. That is a habit worth building early.

### Do not try to change the old name inside the saved history

Idan's 43 saved changes are recorded under his old GitHub email address
(`idancaliber@users.noreply.github.com`). Leave that completely alone.

If he asks about it, explain: that is **history** - the record of what happened. It is correct.
It really was him, and that really was his address at the time. Changing history would give
every single saved change a new identity number, which would break links other documents point
to, for no benefit at all.

**Old addresses in history are normal and fine. Only the address you send new work to matters.**

---

## When to do this task

**First, before anything else.** It takes five minutes, nothing depends on it, and nothing can
go wrong. It is a good warm-up before the bigger tasks.

---

## Definition of done

- [ ] `git remote -v` shows `HelpProgramIdanTool` on both lines.
- [ ] `git fetch origin` finishes with no error.
- [ ] The next `git push` shows no `This repository moved` message.
- [ ] Nothing was deleted and nothing was re-downloaded.
- [ ] The saved history was not changed.
- [ ] **Idan can explain, in his own words, what `origin` is** - that it is a nickname for the
      web address his computer sends changes to. If he cannot, explain it a different way and
      ask again. This is the actual goal of the task; the command is just the excuse for it.

---

## What NOT to do

- Do **not** run the command for him and move on. He types it. He reads it. He understands it.
- Do **not** call it a mistake he made. The project moved; his computer simply has not been told.
- Do **not** rewrite the saved history.
- Do **not** let him delete the folder and download it again.
- Do **not** turn this into a general git lesson. One idea only: a remote is a saved address with
  a nickname. Branches, merging and pull requests are for another day.
