from fastapi import APIRouter, Query

from app.db.database import get_connection
from app.services.library_search import rebuild_library_fts, search_library
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


@router.get("/library")
def library_search(
    q: str = Query("", min_length=0, max_length=200),
    limit: int = Query(50, ge=1, le=100),
) -> dict:
    """
    Full-text search across titles, descriptions, creators, tags, notes, and transcripts.
    """
    query = (q or "").strip()
    if len(query) < 2:
        return {"query": query, "total": 0, "results": []}

    with get_connection() as conn:
        hits = search_library(conn, query, limit=limit)
        if not hits:
            return {"query": query, "total": 0, "results": []}

        ids = [hit["video_id"] for hit in hits]
        placeholders = ",".join("?" for _ in ids)
        rows = conn.execute(
            f"""
            SELECT id, title, uploader, status, platform, created_at
            FROM videos
            WHERE deleted_at IS NULL AND id IN ({placeholders})
            """,
            ids,
        ).fetchall()
        by_id = {row["id"]: row for row in rows}

        results = []
        for hit in hits:
            row = by_id.get(hit["video_id"])
            if not row:
                continue
            results.append(
                {
                    "video_id": row["id"],
                    "title": row["title"],
                    "uploader": row["uploader"],
                    "status": row["status"],
                    "platform": row["platform"],
                    "created_at": row["created_at"],
                    "snippet": hit["snippet"],
                    "rank": hit["rank"],
                }
            )

    return {"query": query, "total": len(results), "results": results}


@router.post("/library/reindex")
def reindex_library() -> dict:
    """Rebuild the library FTS index (admin/maintenance)."""
    with get_connection() as conn:
        count = rebuild_library_fts(conn)
    return {"indexed": count}
