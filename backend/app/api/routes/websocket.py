import asyncio

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import jwt

from app.config import get_settings
from app.tasks import get_task
from app.utils.logger import logger
from app.utils.security import blacklist

router = APIRouter()
settings = get_settings()


async def _authenticate_websocket(websocket: WebSocket, token: str | None) -> dict | None:
    """Validate a JWT token from WebSocket query parameter.

    Returns the decoded payload if valid, None otherwise.
    """
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.JWTError:
        return None

    # Check JTI blacklist
    jti = payload.get("jti")
    if jti and blacklist.is_blacklisted(jti):
        return None

    return payload


@router.websocket("/ws/scan/{task_id}")
async def scan_websocket(
    websocket: WebSocket,
    task_id: str,
    token: str = Query(None),
):
    # Authenticate the WebSocket connection
    payload = await _authenticate_websocket(websocket, token)
    if payload is None:
        await websocket.accept()
        await websocket.send_json({"error": "Authentication required. Provide ?token=<jwt>"})
        await websocket.close(code=4401, reason="Unauthorized")
        return

    await websocket.accept()

    task = get_task(task_id)
    if not task:
        await websocket.send_json({"error": "Task not found"})
        await websocket.close()
        return

    # Verify the authenticated user owns this task
    username = payload.get("sub")
    if task.user_id is not None and username:
        from app.database.database import SessionLocal
        from app.models.models import User

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.username == username).first()
            if user is None or task.user_id != user.id:
                await websocket.send_json({"error": "Access denied"})
                await websocket.close(code=4403, reason="Forbidden")
                return
        finally:
            db.close()

    try:
        task.subscribers.append(websocket)

        # Send initial execution state
        await websocket.send_json(
            {
                "task_id": task.task_id,
                "type": "execution_state",
                "status": task.status,
                "progress": task.progress,
                "message": task.message,
                "scan_id": task.scan_id,
                "execution_state": {
                    "status": task.status,
                    "progress": task.progress,
                    "message": task.message,
                    "transition_history": (
                        task.transition_history if hasattr(task, "transition_history") else []
                    ),
                },
            }
        )

        while task.status in ("queued", "running"):
            # Send progress update with execution state
            await websocket.send_json(
                {
                    "type": "progress_update",
                    "task_id": task.task_id,
                    "status": task.status,
                    "progress": task.progress,
                    "message": task.message,
                    "scan_id": task.scan_id,
                }
            )
            await asyncio.sleep(0.3)

        # Build final result with AI analysis and execution history
        result_data = {
            "task_id": task.task_id,
            "type": "execution_complete",
            "status": task.status,
            "progress": task.progress,
            "message": task.message,
            "scan_id": task.scan_id,
            "result": task.result,
            "error": task.error,
        }

        # Include AI analysis data if available
        if task.result and task.result.get("scan_id"):
            from app.database.database import SessionLocal
            from app.models.models import Scan

            db = SessionLocal()
            try:
                scan = db.query(Scan).filter(Scan.id == task.result["scan_id"]).first()
                if scan and scan.ai_analysis:
                    ai_analysis = scan.ai_analysis
                    result_data["ai_analysis"] = {
                        "executive_summary": ai_analysis.executive_summary,
                        "technical_explanation": ai_analysis.technical_explanation,
                        "business_impact": ai_analysis.business_impact,
                        "attack_scenario": ai_analysis.attack_scenario,
                        "recommended_mitigation": ai_analysis.recommended_mitigation,
                        "confidence": (
                            ai_analysis.confidence if hasattr(ai_analysis, "confidence") else 95
                        ),
                        "references": (
                            ai_analysis.references if hasattr(ai_analysis, "references") else []
                        ),
                        "reasoning": (
                            ai_analysis.reasoning if hasattr(ai_analysis, "reasoning") else ""
                        ),
                    }
            except Exception as e:
                logger.warning(f"Failed to fetch AI analysis: {e}")
            finally:
                db.close()

        await websocket.send_json(result_data)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"WebSocket error: {e}")
    finally:
        if websocket in task.subscribers:
            task.subscribers.remove(websocket)
