import re
import sys
from pathlib import Path
from typing import Optional

from services.ai_service import chat_completion


_WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
_CRAWLER_ROOT = _WORKSPACE_ROOT / "crawler_agent"
if str(_CRAWLER_ROOT) not in sys.path:
    sys.path.append(str(_CRAWLER_ROOT))

from analysis.repo_analyzer import Analyzer  # type: ignore  # noqa: E402
from crawler.github_crawler import GithubCrawler  # type: ignore  # noqa: E402


RECOMMENDATION_KEYWORDS = (
    "recommend",
    "recommendation",
    "suggest",
    "improve my profile",
    "what should i build",
    "projects should i do",
)


def is_recommendation_request(message: str) -> bool:
    lowered = (message or "").lower()
    return any(keyword in lowered for keyword in RECOMMENDATION_KEYWORDS)


def extract_github_username(message: str) -> Optional[str]:
    if not message:
        return None

    url_match = re.search(r"github\.com/([A-Za-z0-9-]+)", message, re.IGNORECASE)
    if url_match:
        return url_match.group(1)

    user_match = re.search(r"(?:github\s*user(?:name)?|username)\s*[:=]\s*([A-Za-z0-9-]+)", message, re.IGNORECASE)
    if user_match:
        return user_match.group(1)

    return None


async def generate_recommendations_from_github(
    user_message: str,
    provider: str,
    api_key: str,
    max_repos: int = 3,
    commit_limit: int = 10,
) -> str:
    username = extract_github_username(user_message)
    if not username:
        raise ValueError(
            "Please share your GitHub username or profile link so I can generate recommendations."
        )

    crawler = GithubCrawler(username)
    analyzer = Analyzer()

    repos = crawler.get_repos()
    if not isinstance(repos, list) or len(repos) == 0:
        raise RuntimeError("No repositories found for that GitHub profile.")

    summaries = []
    for repo in repos[:max_repos]:
        repo_name = repo.get("name")
        if not repo_name:
            continue
        readme = crawler.get_readme(repo_name)
        commits = crawler.get_commits(repo_name, commit_limit)
        summary = analyzer.build_repo_summary(repo_name, readme, commits)
        summaries.append(summary)

    if not summaries:
        raise RuntimeError("I could not build repository summaries from this GitHub profile.")

    review_prompt = (
        "You are a technical hiring assistant. Based on this GitHub profile summary, "
        "give practical recommendations to improve interview readiness.\n\n"
        "Return:\n"
        "1. Top strengths\n"
        "2. Skill gaps\n"
        "3. 5 concrete project recommendations\n"
        "4. 30-day action plan\n\n"
        f"User request:\n{user_message}\n\n"
        f"GitHub username: {username}\n\n"
        "Repository data:\n"
        + "\n\n".join(summaries)
    )

    reply, _ = await chat_completion(
        provider=provider,
        api_key=api_key,
        system_prompt="You are concise, practical, and specific. Use bullet points.",
        messages=[{"role": "user", "content": review_prompt}],
        temperature=0.4,
        max_tokens=1400,
    )
    return reply.strip()
