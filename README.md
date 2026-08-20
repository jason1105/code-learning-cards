# 每日代码学习卡 · Daily Code Learning Cards

A GitHub Pages site that generates a daily learning card from your GitHub starred repositories, powered by Claude AI.

Every morning at 08:00 UTC, a GitHub Actions workflow picks a random repo from your star list, fetches its recent commits, and asks Claude to produce a structured learning card in Chinese with:

- **核心知识点** — One-sentence takeaway
- **深入理解** — 2-3 sentences of deeper explanation
- **实际应用场景** — Real-world use cases
- **思考问题** — A reflection question to cement the learning

The result is rendered as a 3D flip card on the GitHub Pages site.

---

## Setup

### 1. Fork or create the repository

Create a new repository on GitHub (or fork this one). Enable **GitHub Pages** in the repository settings:

- Go to **Settings → Pages**
- Source: **Deploy from a branch**
- Branch: `main` (or `master`), folder: `/ (root)`

### 2. Add secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Your Anthropic API key — get one at [console.anthropic.com](https://console.anthropic.com) |
| `CARDS_GITHUB_TOKEN` | *(Optional)* A GitHub Personal Access Token (PAT) with `read:user` scope, used to read your starred repos. If omitted, the built-in `GITHUB_TOKEN` is used, which works as long as your starred repos are public. |

To create a PAT: **GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)** → New token → enable `read:user` scope.

### 3. Trigger the first run

Go to **Actions → Daily Learning Card → Run workflow** to generate your first card immediately, without waiting for the 08:00 UTC schedule.

---

## How it works

```
GitHub Actions (cron: 0 8 * * *)
       │
       ├─ GET /users/{owner}/starred   (sorted by updated, up to 30 repos)
       │
       ├─ random.choice(repos)
       │
       ├─ GET /repos/{owner}/{repo}/commits  (last 5)
       │
       ├─ Claude claude-haiku-4-5-20251001  →  JSON card content
       │
       ├─ Write  cards/latest.json
       ├─ Prepend cards/archive.json  (keeps last 30 entries)
       │
       └─ git commit && git push
```

`index.html` is a static page that fetches the two JSON files at load time and renders the flip-card UI. No build step required.

---

## File structure

```
code-learning-cards/
├── .github/
│   └── workflows/
│       └── daily-card.yml   # GitHub Actions workflow
├── cards/
│   ├── latest.json          # Today's card
│   └── archive.json         # All past cards (last 30)
├── generate_card.py         # Card generation script
├── index.html               # GitHub Pages frontend
├── .nojekyll                # Prevents Jekyll processing
└── README.md
```

---

## Customization

**Change the schedule:** Edit the `cron` expression in `daily-card.yml`. The current value `0 8 * * *` fires at 08:00 UTC daily.

**Change the model:** Edit the `model=` argument in `generate_card.py`. Any Claude model works.

**Change the prompt language or format:** Edit the `build_prompt()` function in `generate_card.py`.

**Change how many repos to sample from:** Edit the `per_page=30` argument in `get_starred_repos()`.

**Change the archive length:** Edit `archive[:30]` in `save_files()` to keep more or fewer past cards.

---

## Local preview

Because `index.html` fetches JSON via `fetch()`, you need a local HTTP server (not `file://`):

```bash
cd code-learning-cards
python3 -m http.server 8080
# then open http://localhost:8080
```
