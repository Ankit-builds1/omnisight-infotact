"""
FastAPI App — OmniSight Backend (Week 4)

QA Dashboard ke liye REST API: open PRs list karo, detail dekho,
approve (merge) ya reject (close) karo, aur PR decision history dekho.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from github_integration import (
    list_open_prs,
    get_pr_details,
    merge_pr,
    close_pr_with_comment,
    get_pr_history,
)

app = FastAPI(title="OmniSight Dashboard API")

# React dev server se calls allow karne ke liye (localhost:5173 Vite default)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev ke liye; production me specific origin daalna
    allow_methods=["*"],
    allow_headers=["*"],
)


class RejectRequest(BaseModel):
    reason: str = "Rejected by QA manager"


@app.get("/")
def root():
    return {"status": "OmniSight backend running"}


@app.get("/prs")
def get_prs():
    """Sab open PRs list karo (dashboard ki main list view)."""
    try:
        return list_open_prs()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/prs/history")
def get_history():
    """PR decision history (merged/rejected) — dashboard ka History tab."""
    try:
        return get_pr_history()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/prs/{pr_number}")
def get_pr(pr_number: int):
    """Ek PR ka full detail."""
    try:
        return get_pr_details(pr_number)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/prs/{pr_number}/approve")
def approve_pr(pr_number: int):
    """QA manager approve kare — PR merge ho jaye."""
    try:
        return merge_pr(pr_number)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/prs/{pr_number}/reject")
def reject_pr(pr_number: int, body: RejectRequest):
    """QA manager reject kare — PR comment ke saath close ho jaye."""
    try:
        return close_pr_with_comment(pr_number, body.reason)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))