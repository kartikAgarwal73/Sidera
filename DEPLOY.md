# Deploying Sidera to Render

Everything below has been verified locally under gunicorn with the same
command Render will run. Roughly ten minutes end to end.

---

## 0. Stage the public repository

**A fresh repository is required, not preferred.** The app lives in the
`vedic-astro/` subdirectory of a repository whose root holds unrelated
real-estate files — and, decisively, whose **history contains a real birth
record**. Five commits carry it. It was removed from the working tree on
2026-08-26, but removing a file does not remove it from a clone: renaming
this repo would publish that history. So the public repo starts from a single
commit with no ancestry. Keep the existing repository **private**; it holds
the build log and nothing here deletes it.

A script does the extraction and refuses to produce a repo that fails its
own checks:

```bash
cd vedic-astro
tools/make_fresh_repo.sh            # → ../sidera-public
```

It copies the tracked app to the new root (no `.git`, no caches), greps for
secrets and absolute local paths, refuses if any `.se1`/`.se2` ephemeris files
crept in, **runs the full gate suite from the new root**, and only then
`git init`s and makes one commit.

**Check retired personal data too — this is the step that actually bit.**
The first public push of this repo leaked a birth record: the secrets grep
passed, but `PLAN.md` still carried the Phase 1/2/3 gate values, and a full
natal chart reconstructs a birth moment as surely as a birth line does. The
repo had to be deleted and recreated, because **a force-push does not unserve
a commit GitHub has already published** — the old SHA stayed fetchable via
`raw.githubusercontent.com`.

So pass a pattern file listing anything retired, one `grep -E` pattern per
line. Keep it **outside the repository** — a scanner that hardcodes the
retired values publishes them the moment it ships:

```bash
SIDERA_REDACTION_PATTERNS=~/.sidera-retired tools/make_fresh_repo.sh
```

Without it the script says `clean (secrets only)` and warns; it does not
silently pretend to have checked.

Then point it at an empty GitHub repo named `sidera`:

```bash
cd ../sidera-public
git remote add origin https://github.com/<you>/sidera.git
git push -u origin main
```

Render's **Root Directory** stays blank — the app is at the root.

Creating the empty GitHub repo is yours to do: this environment has no
admin-scoped tool for creating or renaming repositories.

---

## 1. Create the service

Render Dashboard → **New** → **Web Service** → connect the repo.

| Field | Value |
|---|---|
| **Language / Environment** | Python 3 |
| **Region** | whichever is nearest your audience |
| **Branch** | `main` |
| **Root Directory** | *(leave blank — the app is at the repo root)* |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120` |
| **Instance Type** | Free is enough to launch |

The repo also contains a `Procfile` with the identical command, so if Render
picks it up automatically you can leave Start Command blank.

## 2. Environment variables

**None are required.** The app has no API keys, no database and no secrets.
Set these only if you want them:

| Key | Value | Why |
|---|---|---|
| `PYTHON_VERSION` | `3.11.9` | Pin the runtime; the app is developed on 3.11 |
| `SE_EPHE_PATH` | *(leave unset)* | Only if you later add Swiss `.se1` files. **Setting it changes the numerical source — re-verify the gates before trusting output** |
| `SIDERA_FIXTURES` | *(leave unset)* | Test-only; substitutes the verification charts |

`PORT` is supplied by Render automatically and read by the start command —
do not set it yourself.

## 3. Deploy and check

Render builds and gives you `https://<service>.onrender.com`. Confirm:

1. The landing page renders — hero, the "every reading shows its computation"
   line, and the single CTA.
2. Cast a chart with a city from the autocomplete; confirm latitude,
   longitude and **timezone** fill in from the suggestion.
3. Open **Read the full day** and check the reading shows its facts.
4. Open a yoga's "Why?" and confirm the rule text appears.

On the free tier the service sleeps after inactivity, so the first request
after idle takes ~30 seconds and the app looks slow. That is Render, not the
chart maths. Upgrade to a paid instance to remove it.

## 4. After the URL exists

- Replace the placeholder feedback link in `templates/index.html`
  (`https://example.com/sidera-feedback`) with your Google Form.
- The footer LinkedIn link is already live.

## Troubleshooting

**Build fails on `pyswisseph`** — it compiles from source and needs a build
toolchain, which Render's Python environment provides. If it fails, pin
`PYTHON_VERSION` to `3.11.9`; the wheel situation is worst on very new
Pythons.

**App boots but every chart 500s** — almost always the timezone string. The
app refuses to guess a timezone; check the city autocomplete populated the
hidden `tz` field.

**Positions look subtly different from another app** — expected and not a
bug. Sidera is sidereal with Lahiri ayanāṃśa and Whole Sign houses; most
Western software is tropical with Placidus. Compare like with like.

**Static files 404** — Render must run from the directory containing
`app.py`. Check the Root Directory setting from step 1.
