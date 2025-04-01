from fastapi import APIRouter, HTTPException
from app.services.streaming_manager import StreamingManager

router = APIRouter()


# Assume that the shared StreamingManager instance is injected in main.py.
@router.post("/subscribe/{guid}")
async def subscribe(guid: str):
    # The shared instance should be used; here, for demonstration, we import the class.
    # In production, you might use dependency injection.
    from app.main import streaming_manager  # Import the shared instance
    if streaming_manager.subscribe(guid):
        return {"message": f"Subscribed to GUID: {guid}"}
    raise HTTPException(status_code=400, detail=f"Already subscribed to GUID: {guid}")


@router.post("/unsubscribe/{guid}")
async def unsubscribe(guid: str):
    from app.main import streaming_manager
    if streaming_manager.unsubscribe(guid):
        return {"message": f"Unsubscribed from GUID: {guid}"}
    raise HTTPException(status_code=400, detail=f"Not subscribed to GUID: {guid}")


@router.get("/")
async def list_subscriptions():
    from app.main import streaming_manager
    return {"subscriptions": list(streaming_manager.active_subscriptions.keys())}
