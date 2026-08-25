"""
GitHub Integration — OmniSight Backend (Week 3)

PyGithub se automatically branch banata hai, VLM ka structured fix
real HTML content pe apply karta hai, commit karta hai, aur PR open
karta hai — sirf un reports ke liye jo DOM cross-check pass kar
chuke hain (trustworthy).
"""

import os
import re
import time
import logging
from dotenv import load_dotenv
from github import Github, Auth, GithubException
from bs4 import BeautifulSoup

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

    auth = Auth.Token(GITHUB_TOKEN)
    g = Github(auth=auth)
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


def commit_fix(branch_name: str, file_path: str, new_content: str, commit_message: str):
    """
    Ek file ko diye gaye branch pe update/create karo.

    Args:
        branch_name: jis branch pe commit karna hai (create_branch se aaya)
        file_path: repo ke andar file ka path
        new_content: poori file ka naya content (string)
        commit_message: commit ka message

    Returns: commit object
    """
    repo = get_repo()

    try:
        try:
            existing_file = repo.get_contents(file_path, ref=branch_name)
            result = repo.update_file(
                path=file_path,
                message=commit_message,
                content=new_content,
                sha=existing_file.sha,
                branch=branch_name,
            )
            logger.info(f"File updated: {file_path} on {branch_name}")
        except GithubException:
            result = repo.create_file(
                path=file_path,
                message=commit_message,
                content=new_content,
                branch=branch_name,
            )
            logger.info(f"File created: {file_path} on {branch_name}")

        return result["commit"]

    except GithubException as e:
        logger.error(f"Failed to commit fix: {e}")
        raise


def open_pull_request(
    branch_name: str,
    title: str,
    body: str,
    base_branch: str = "backend-fastapi",
):
    """
    branch_name se base_branch mein PR kholo.

    Returns: PullRequest object
    """
    repo = get_repo()

    try:
        pr = repo.create_pull(
            title=title,
            body=body,
            head=branch_name,
            base=base_branch,
        )

        logger.info(f"Pull Request opened: {pr.html_url}")
        return pr

    except GithubException as e:
        logger.error(f"Failed to open PR: {e}")
        raise


# -------------------------------------------------
# Week 3 Day 2 — real fix application
# -------------------------------------------------
def apply_fix_to_html(html_content: str, fix: dict) -> tuple[str, bool]:
    """
    VLM ke structured fix (selector + css_changes) ko asli HTML content
    pe apply karta hai using BeautifulSoup.

    Args:
        html_content: original HTML file ka poora content (string)
        fix: {"selector": ".btn", "css_changes": [{"property": "max-width", "value": "100px"}, ...]}

    Returns:
        (updated_html: str, applied: bool)
        applied=False agar selector kuch match nahi karta - us case mein
        original content wapas milta hai, taaki galti se kuch corrupt na ho.
    """
    selector = fix.get("selector")
    css_changes = fix.get("css_changes", [])

    if not selector or not css_changes:
        logger.warning("Fix has no selector or css_changes; skipping apply.")
        return html_content, False

    soup = BeautifulSoup(html_content, "html.parser")

    try:
        elements = soup.select(selector)
    except Exception as e:
        logger.error(f"Invalid CSS selector '{selector}': {e}")
        return html_content, False

    if not elements:
        logger.warning(f"Selector '{selector}' matched no elements; skipping apply.")
        return html_content, False

    for el in elements:
        existing_style = el.get("style", "")
        # Trailing semicolon safe rakho
        if existing_style and not existing_style.strip().endswith(";"):
            existing_style += ";"

        new_declarations = " ".join(
            f"{c['property']}: {c['value']};" for c in css_changes
        )
        el["style"] = f"{existing_style} {new_declarations}".strip()

    logger.info(
        f"Applied {len(css_changes)} CSS change(s) to "
        f"{len(elements)} element(s) matching '{selector}'"
    )
    return str(soup), True


def create_fix_pr(
    bug_report: dict,
    target_file: str,
    original_html: str,
    base_branch: str = "backend-fastapi",
):
    """
    End-to-end: branch bano, VLM ka fix real HTML pe apply karo,
    commit karo, PR kholo.

    Args:
        bug_report: Action Engine se aaya dict (VLMBugReport jaisa)
        target_file: repo ke andar us HTML file ka path jise patch karna hai
                     e.g. "screenshots/broken/broken-button-clip.html"
        original_html: us file ka current content (string) - GitHub se
                        ya local disk se pehle se fetch kiya hua

    Returns:
        PullRequest object, ya None agar fix apply nahi ho paya
    """
    fix = bug_report.get("fix", {})

    if not isinstance(fix, dict):
        logger.error("Fix is not a structured dict; cannot apply automatically.")
        return None

    updated_html, applied = apply_fix_to_html(original_html, fix)

    if not applied:
        logger.error(
            f"Could not apply fix for selector '{fix.get('selector')}'. "
            "No PR will be created."
        )
        return None

    branch_name = create_branch(base_branch)

    css_summary = "\n".join(
        f"  - `{c['property']}: {c['value']}`"
        for c in fix.get("css_changes", [])
    )

    commit_message = f"fix: {bug_report.get('description', 'UI bug fix')}"

    pr_body = f"""**Auto-generated by OmniSight**

**Bug:** {bug_report.get('description')}
**Severity:** {bug_report.get('severity_level')}
**Confidence:** {bug_report.get('confidence_score')}

**Selector:** `{fix.get('selector')}`

**CSS Changes:**
{css_summary}

**Explanation:** {fix.get('explanation', '')}

---
*This fix was applied automatically and verified against the DOM cross-check layer before this PR was opened.*
"""

    commit_fix(
        branch_name=branch_name,
        file_path=target_file,
        new_content=updated_html,
        commit_message=commit_message,
    )

    pr = open_pull_request(
        branch_name=branch_name,
        title=f"Auto-fix: {bug_report.get('description', 'UI bug')[:60]}",
        body=pr_body,
        base_branch=base_branch,
    )

    return pr


# -------------------------------------------------
# Test — python github_integration.py
# -------------------------------------------------
if __name__ == "__main__":
    print("Testing full fix -> PR flow with REAL HTML patching...")

    sample_bug = {
        "bug_found": True,
        "description": "The 'Add to cart' button for the Sauce Labs Backpack is clipped and not fully visible.",
        "severity_level": "Major",
        "confidence_score": 0.95,
        "fix": {
            "selector": ".btn_inventory",
            "css_changes": [
                {"property": "max-width", "value": "150px"},
                {"property": "white-space", "value": "normal"},
            ],
            "explanation": "Constraining the button width prevents it from overflowing the viewport.",
        },
    }

    # Local file se test HTML lao
    local_path = os.path.join(
        os.path.dirname(__file__), "..", "..",
        "screenshots", "broken", "broken-button-clip.html"
    )

    try:
        with open(local_path, encoding="utf-8") as f:
            original_html = f.read()
    except FileNotFoundError:
        print(f"❌ Could not find test HTML at {local_path}")
        print("   Run: git checkout origin/frontend -- screenshots/")
        raise SystemExit(1)

    try:
        pr = create_fix_pr(
            bug_report=sample_bug,
            target_file="screenshots/broken/broken-button-clip.html",
            original_html=original_html,
            base_branch="backend-fastapi",
        )

        if pr:
            print(f"✅ PR opened: {pr.html_url}")
        else:
            print("❌ Fix could not be applied — no PR created (see logs above)")

    except Exception as e:
        print(f"❌ Error: {e}")