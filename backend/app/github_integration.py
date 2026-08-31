"""
GitHub Integration — OmniSight Backend (Week 3 + Week 4 dashboard support)

PyGithub se automatically branch banata hai, VLM ka structured fix
real HTML content pe apply karta hai, commit karta hai, aur PR open
karta hai — sirf un reports ke liye jo DOM cross-check pass kar
chuke hain (trustworthy).

Week 4: PR list/approve/reject functions for the QA review dashboard.
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

# Confidence threshold: below this, the fix still gets a PR but is
# clearly flagged for human review instead of silently treated as trustworthy.
CONFIDENCE_REVIEW_THRESHOLD = 0.6


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


def apply_fix_to_html(html_content: str, fix: dict) -> tuple[str, bool]:
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
    needs_human_review: bool = False,
):
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

    review_banner = ""
    title_prefix = "Auto-fix"
    if needs_human_review:
        review_banner = (
            "\n> ⚠️ **NEEDS HUMAN REVIEW** — confidence score is below the "
            f"{CONFIDENCE_REVIEW_THRESHOLD} threshold. Do not merge without "
            "manually verifying the before/after screenshots.\n"
        )
        title_prefix = "[NEEDS REVIEW] Auto-fix"

    pr_body = f"""**Auto-generated by OmniSight**
{review_banner}
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
        title=f"{title_prefix}: {bug_report.get('description', 'UI bug')[:60]}",
        body=pr_body,
        base_branch=base_branch,
    )

    return pr


def create_fix_pr_from_self_healing(
    self_healing_result: dict,
    target_file: str,
    original_html: str,
    base_branch: str = "backend-fastapi",
):
    status = self_healing_result.get("status")

    if status != "FIXED":
        logger.warning(
            f"Self-healing status is '{status}', not FIXED. "
            "Skipping PR creation — no unverified fix will be pushed."
        )
        return None

    fix = self_healing_result.get("fix_applied")
    if not fix:
        logger.error("Status is FIXED but fix_applied is missing. Skipping PR.")
        return None

    evaluation = self_healing_result.get("evaluation", {})
    confidence = evaluation.get("confidence_score", 0)

    # Confidence gate: low-confidence fixes still get a PR, but clearly
    # flagged so a human reviews before merging — never silently trusted.
    needs_human_review = False
    try:
        needs_human_review = float(confidence) < CONFIDENCE_REVIEW_THRESHOLD
    except (TypeError, ValueError):
        logger.warning(
            f"Confidence score '{confidence}' is not numeric; "
            "flagging for human review to be safe."
        )
        needs_human_review = True

    if needs_human_review:
        logger.warning(
            f"Confidence {confidence} is below {CONFIDENCE_REVIEW_THRESHOLD} "
            "threshold — PR will be flagged as NEEDS HUMAN REVIEW."
        )

    bug_report = {
        "bug_found": True,
        "description": self_healing_result.get("original_bug", "UI bug fix"),
        "severity_level": "Major",
        "confidence_score": confidence,
        "fix": fix,
    }

    pr = create_fix_pr(
        bug_report=bug_report,
        target_file=target_file,
        original_html=original_html,
        base_branch=base_branch,
        needs_human_review=needs_human_review,
    )

    if pr:
        if needs_human_review:
            logger.info(f"Low-confidence fix pushed as PR (flagged for review): {pr.html_url}")
        else:
            logger.info(f"Self-healing verified fix pushed as PR: {pr.html_url}")
    else:
        logger.error("create_fix_pr() returned None even though status was FIXED.")

    return pr


# =====================================================
# Week 4 — Dashboard Support Functions
# List / Approve / Reject PRs for the QA review dashboard
# =====================================================

def list_open_prs(base_branch: str = "backend-fastapi") -> list[dict]:
    """
    Saare open PRs list karo jo base_branch pe target hain.
    Dashboard ke liye summary info return karta hai (title, number, url,
    confidence/severity agar PR body me parse ho paye).
    """
    repo = get_repo()
    prs = repo.get_pulls(state="open", base=base_branch)

    result = []
    for pr in prs:
        body = pr.body or ""
        needs_review = "NEEDS HUMAN REVIEW" in body or "[NEEDS REVIEW]" in pr.title

        confidence = None
        match = re.search(r"\*\*Confidence:\*\*\s*([0-9.]+)", body)
        if match:
            try:
                confidence = float(match.group(1))
            except ValueError:
                confidence = None

        severity = None
        sev_match = re.search(r"\*\*Severity:\*\*\s*(\w+)", body)
        if sev_match:
            severity = sev_match.group(1)

        result.append({
            "number": pr.number,
            "title": pr.title,
            "url": pr.html_url,
            "branch": pr.head.ref,
            "created_at": pr.created_at.isoformat() if pr.created_at else None,
            "confidence": confidence,
            "severity": severity,
            "needs_review": needs_review,
            "body": body,
        })

    return result


def get_pr_details(pr_number: int) -> dict:
    """Ek specific PR ka full detail nikaalo (dashboard detail view ke liye)."""
    repo = get_repo()
    pr = repo.get_pull(pr_number)

    body = pr.body or ""
    confidence = None
    match = re.search(r"\*\*Confidence:\*\*\s*([0-9.]+)", body)
    if match:
        try:
            confidence = float(match.group(1))
        except ValueError:
            confidence = None

    return {
        "number": pr.number,
        "title": pr.title,
        "url": pr.html_url,
        "state": pr.state,
        "branch": pr.head.ref,
        "base": pr.base.ref,
        "body": body,
        "confidence": confidence,
        "created_at": pr.created_at.isoformat() if pr.created_at else None,
        "mergeable": pr.mergeable,
    }


def merge_pr(pr_number: int, merge_method: str = "squash") -> dict:
    """
    QA manager ne approve kiya — PR ko merge karo.
    merge_method: 'merge' | 'squash' | 'rebase'
    """
    repo = get_repo()
    pr = repo.get_pull(pr_number)

    if pr.state != "open":
        raise ValueError(f"PR #{pr_number} is not open (state: {pr.state})")

    result = pr.merge(merge_method=merge_method)
    logger.info(f"PR #{pr_number} merged: {result.sha}")

    return {
        "merged": result.merged,
        "sha": result.sha,
        "message": result.message,
    }


def close_pr_with_comment(pr_number: int, reason: str) -> dict:
    """
    QA manager ne reject kiya — PR ko comment ke saath close karo.
    """
    repo = get_repo()
    pr = repo.get_pull(pr_number)

    if pr.state != "open":
        raise ValueError(f"PR #{pr_number} is not open (state: {pr.state})")

    pr.create_issue_comment(f"Rejected by QA manager: {reason}")
    pr.edit(state="closed")

    logger.info(f"PR #{pr_number} closed (rejected): {reason}")

    return {
        "number": pr_number,
        "state": "closed",
        "reason": reason,
    }


if __name__ == "__main__":
    print("Testing self-healing -> PR flow with today's REAL FIXED result (real saucedemo HTML)...")

    # Priya ka final, 3-baar-consistent-verified self-healing result -
    # real saucedemo HTML par, sahi element (Sauce Labs Backpack, first-child)
    todays_self_healing_result = {
        "html_path": "screenshots/broken/broken-button-clip.html",
        "original_bug": "The button in the first product card (Sauce Labs Backpack) is clipped and cut off.",
        "fix_applied": {
            "selector": "#page_wrapper .inventory_item:first-child .btn_inventory",
            "css_changes": [
                {"property": "width", "value": "auto"},
                {"property": "max-width", "value": "none"},
                {"property": "overflow", "value": "visible"},
            ],
            "explanation": "Relaxing the width and max-width properties and setting overflow to visible will allow the button to be fully visible.",
        },
        "status": "FIXED",
        "evaluation": {
            "bug_still_present": False,
            "confidence_score": 0.95,
            "explanation": (
                "The button's text and border are fully visible and readable "
                "without any parts cut off or hidden."
            ),
        },
    }

    not_fixed_example = {
        "html_path": "screenshots/broken/broken-button-clip.html",
        "original_bug": "The button in the first product card is clipped and cut off.",
        "fix_applied": {
            "selector": "#page_wrapper .inventory_item:first-child .btn_inventory",
            "css_changes": [{"property": "max-width", "value": "100px"}],
            "explanation": "Reducing width.",
        },
        "status": "NOT_FIXED",
        "evaluation": {
            "bug_still_present": True,
            "confidence_score": 0.9,
            "explanation": "Button is still clipped in the after screenshot.",
        },
    }

    low_confidence_example = {
        "html_path": "screenshots/broken/broken-button-clip.html",
        "original_bug": "The button in the first product card (Sauce Labs Backpack) is clipped and cut off.",
        "fix_applied": {
            "selector": "#page_wrapper .inventory_item:first-child .btn_inventory",
            "css_changes": [
                {"property": "width", "value": "auto"},
                {"property": "max-width", "value": "none"},
                {"property": "overflow", "value": "visible"},
            ],
            "explanation": "Relaxing width/max-width and setting overflow visible.",
        },
        "status": "FIXED",
        "evaluation": {
            "bug_still_present": False,
            "confidence_score": 0.42,
            "explanation": "Button appears mostly visible but VLM was uncertain about full text clarity.",
        },
    }

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
        print("\n--- Test 1: FIXED status, high confidence (normal PR) ---")
        pr = create_fix_pr_from_self_healing(
            self_healing_result=todays_self_healing_result,
            target_file="screenshots/broken/broken-button-clip.html",
            original_html=original_html,
            base_branch="backend-fastapi",
        )

        if pr:
            print(f"✅ PR opened: {pr.html_url}")
        else:
            print("❌ Fix could not be applied — no PR created (see logs above)")

        print("\n--- Test 2: NOT_FIXED status (should skip) ---")
        pr2 = create_fix_pr_from_self_healing(
            self_healing_result=not_fixed_example,
            target_file="screenshots/broken/broken-button-clip.html",
            original_html=original_html,
            base_branch="backend-fastapi",
        )
        print("✅ Correctly skipped PR creation" if pr2 is None else "❌ Should have skipped but didn't!")

        print("\n--- Test 3: FIXED status, LOW confidence (should flag for human review) ---")
        pr3 = create_fix_pr_from_self_healing(
            self_healing_result=low_confidence_example,
            target_file="screenshots/broken/broken-button-clip.html",
            original_html=original_html,
            base_branch="backend-fastapi",
        )
        if pr3:
            print(f"✅ PR opened (flagged for review): {pr3.html_url}")
        else:
            print("❌ Fix could not be applied — no PR created (see logs above)")

    except Exception as e:
        print(f"❌ Error: {e}")