import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.tasks import get_task
from app.utils.logger import logger


router = APIRouter()


@router.websocket("/ws/scan/{task_id}")
async def scan_websocket(websocket: WebSocket, task_id: str):
    await websocket.accept()

    task = get_task(task_id)
    if not task:
        await websocket.send_json({"error": "Task not found"})
        await websocket.close()
        return

    try:
        task.subscribers.append(websocket)

        await websocket.send_json({
            "task_id": task.task_id,
            "status": task.status,
            "progress": task.progress,
            "message": task.message,
            "scan_id": task.scan_id,
        })

        while task.status in ("queued", "running"):
            await asyncio.sleep(0.3)

        await websocket.send_json({
            "task_id": task.task_id,
            "status": task.status,
            "progress": task.progress,
            "message": task.message,
            "scan_id": task.scan_id,
            "result": task.result,
            "error": task.error,
        })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"WebSocket error: {e}")
    finally:
        if websocket in task.subscribers:
            task.subscribers.remove(websocket)
