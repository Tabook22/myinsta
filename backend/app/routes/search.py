from fastapi import APIRouter

from app.services.web_search import diagnose, search_web

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/test")
def test_search() -> dict:
    """Diagnostic endpoint — shows Brave API config status and a live test call."""
    return diagnose()


@router.get("/query")
def query_search(q: str, mode: str = "brave") -> dict:
    """Quick search test. Usage: /api/search/query?q=your+question"""
    result = search_web(q)
    return {"query": q, "result": result}
