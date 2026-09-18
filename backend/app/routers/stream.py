from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..services.events import hub

router = APIRouter(tags=["stream"])


@router.websocket("/ws/campaigns")
async def campaign_stream(websocket: WebSocket, run_id: int | None = None) -> None:
    await hub.connect(websocket, run_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await hub.disconnect(websocket)
    except Exception:  # noqa: BLE001
        await hub.disconnect(websocket)
