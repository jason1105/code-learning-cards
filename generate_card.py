#!/usr/bin/env python3
"""Generate a daily learning card from the user's GitHub starred repositories."""

import json
import os
import random
import re
import sys
from datetime import datetime, timezone

import requests


def get_starred_repos(owner: str, token: str, per_page: int = 30) -> list:
    """Fetch the most-recently-updated starred repos for a GitHub user."""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    params = {"sort": "updated", "direction": "desc", "per_page": per_page}
    resp = requests.get(
        f"https://api.github.com/users/{owner}/starred",
        headers=headers,
        params=params,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def get_recent_commits(repo_full_name: str, token: str, per_page: int = 5) -> list:
    """Fetch the most recent commits for a repository."""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    try:
        resp = requests.get(
            f"https://api.github.com/repos/{repo_full_name}/commits",
            headers=headers,
            params={"per_page": per_page},
            timeout=15,
        )
        resp.raise_for_status()
        commits = resp.json()
        return [
            {
                "message": c["commit"]["message"].split("\n")[0][:100],
                "date": c["commit"]["author"]["date"][:10],
                "author": c["commit"]["author"]["name"],
            }
            for c in commits
            if isinstance(c, dict) and "commit" in c
        ]
    except Exception as exc:
        print(f"Warning: could not fetch commits for {repo_full_name}: {exc}")
        return []


def build_prompt(repo: dict, commits: list) -> str:
    if commits:
        commits_text = "\n".join(
            f"- [{c['date']}] {c['message']} (by {c['author']})" for c in commits
        )
    else:
        commits_text = "（暂无最近提交信息）"

    return (
        f"你是一个技术学习导师。以下是GitHub仓库 {repo['full_name']} 的信息：\n"
        f"描述：{repo.get('description') or '暂无描述'}\n"
        f"主要语言：{repo.get('language') or '未知'}\n"
        f"Star数：{repo.get('stargazers_count', 0)}\n"
        f"最近的提交：\n{commits_text}\n\n"
        f"请生成一张今日学习卡片，包含：1)核心知识点(一句话) 2)深入理解(2-3句) "
        f"3)实际应用场景 4)一个思考问题。用中文，专业但友好的语气。\n"
        f"请严格以如下JSON格式返回，不要包含任何其他文字：\n"
        f'{{"core_point": "...", "deep_understanding": "...", "use_cases": "...", "thinking_question": "..."}}'
    )


MODEL = os.environ.get("LLM_MODEL") or os.environ.get("OPENROUTER_MODEL") or "deepseek-v4-flash"


def call_llm(prompt: str, api_key: str) -> dict:
    """通过 OpenRouter 调用模型，返回解析后的卡片内容。"""
    from openai import OpenAI

    client = OpenAI(base_url=os.environ.get("LLM_BASE_URL") or "https://api.deepseek.com", api_key=api_key)
    message = client.chat.completions.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.choices[0].message.content.strip()

    # Extract the first JSON object found in the response
    match = re.search(r"\{[\s\S]*\}", raw)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Fallback: return raw text under a single key
    return {"raw": raw}


def load_archive(path: str = "cards/archive.json") -> list:
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_files(card: dict) -> None:
    os.makedirs("cards", exist_ok=True)

    with open("cards/latest.json", "w", encoding="utf-8") as f:
        json.dump(card, f, ensure_ascii=False, indent=2)

    archive = load_archive()
    archive.insert(0, card)
    archive = archive[:30]  # keep last 30 entries

    with open("cards/archive.json", "w", encoding="utf-8") as f:
        json.dump(archive, f, ensure_ascii=False, indent=2)

    print(f"Saved card for {card['repo_name']}")


def main() -> None:
    owner = os.environ.get("REPO_OWNER", "").strip()
    github_token = os.environ.get("CARDS_GITHUB_TOKEN", "").strip()
    openrouter_key = (os.environ.get("LLM_API_KEY") or os.environ.get("OPENROUTER_API_KEY", "")).strip()

    missing = [k for k, v in [
        ("REPO_OWNER", owner),
        ("CARDS_GITHUB_TOKEN", github_token),
        ("LLM_API_KEY / OPENROUTER_API_KEY", openrouter_key),
    ] if not v]
    if missing:
        print(f"Error: missing environment variables: {', '.join(missing)}")
        sys.exit(1)

    print(f"Fetching starred repos for {owner} ...")
    repos = get_starred_repos(owner, github_token)
    if not repos:
        print("No starred repos found — nothing to do.")
        sys.exit(0)

    repo = random.choice(repos)
    print(f"Selected repo: {repo['full_name']}")

    commits = get_recent_commits(repo["full_name"], github_token)
    print(f"Fetched {len(commits)} recent commits.")

    prompt = build_prompt(repo, commits)
    print("Calling Claude API ...")
    card_content = call_llm(prompt, openrouter_key)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    card = {
        "date": today,
        "repo_name": repo["full_name"],
        "repo_url": repo["html_url"],
        "repo_description": repo.get("description") or "",
        "language": repo.get("language") or "",
        "stars": repo.get("stargazers_count", 0),
        "card_content": card_content,
    }

    save_files(card)


if __name__ == "__main__":
    main()
