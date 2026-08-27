import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
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

        await websocket.send_json(
            {
                "task_id": task.task_id,
                "status": task.status,
                "progress": task.progress,
                "message": task.message,
                "scan_id": task.scan_id,
            }
        )

        while task.status in ("queued", "running"):
            await asyncio.sleep(0.3)

        await websocket.send_json(
            {
                "task_id": task.task_id,
                "status": task.status,
                "progress": task.progress,
                "message": task.message,
                "scan_id": task.scan_id,
                "result": task.result,
                "error": task.error,
            }
        )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"WebSocket error: {e}")
    finally:
        if websocket in task.subscribers:
            task.subscribers.remove(websocket)
