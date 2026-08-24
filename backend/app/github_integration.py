"""
GitHub Integration — OmniSight Backend (Week 3)

PyGithub se automatically branch banata hai, fix commit karta hai,
aur PR open karta hai — sirf un reports ke liye jo DOM cross-check
pass kar chuke hain (trustworthy).
"""

import os
import time
import logging
from dotenv import load_dotenv
from github import Github, GithubException

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("github_integration")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")


def get_repo():
    """GitHub client authenticate karo aur repo object return karo."""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        raise ValueError(
            "GITHUB_TOKEN or GITHUB_REPO missing. Check your .env file."
        )

    g = Github(GITHUB_TOKEN)
    repo = g.get_repo(GITHUB_REPO)
    return repo


def create_branch(base_branch: str = "backend-fastapi") -> str:
    """
    Naya branch banao naming pattern: fix/bug-{timestamp}

    Returns: naye branch ka naam
    """
    repo = get_repo()

    timestamp = int(time.time())
    new_branch_name = f"fix/bug-{timestamp}"

    try:
        base_ref = repo.get_branch(base_branch)
        base_sha = base_ref.commit.sha

        repo.create_git_ref(
            ref=f"refs/heads/{new_branch_name}",
            sha=base_sha,
        )

        logger.info(f"Branch created: {new_branch_name} (from {base_branch})")
        return new_branch_name

    except GithubException as e:
        logger.error(f"Failed to create branch: {e}")
        raise


# -------------------------------------------------
# Test — python github_integration.py
# -------------------------------------------------
if __name__ == "__main__":
    print("Testing GitHub connection...")

    try:
        repo = get_repo()
        print(f"✅ Connected to repo: {repo.full_name}")
        print(f"   Default branch: {repo.default_branch}")

        print("\nCreating a test branch...")
        branch_name = create_branch(base_branch="backend-fastapi")
        print(f"✅ Branch created: {branch_name}")
        print(f"   Check: https://github.com/{GITHUB_REPO}/tree/{branch_name}")

    except Exception as e:
        print(f"❌ Error: {e}")