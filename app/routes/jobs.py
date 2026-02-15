import json
import time
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.services.authz import CurrentContext, require_context

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/stream")
def jobs_stream(ctx: CurrentContext = Depends(require_context)):
    def event_generator():
        for i in range(1, 6):
            payload = {
                "tenant_id": ctx.tenant.id,
                "status": "running" if i < 5 else "succeeded",
                "progress": i * 20,
                "message": f"Demo heartbeat {i}/5",
                "at": datetime.utcnow().isoformat(),
            }
            yield f"data: {json.dumps(payload)}\n\n"
            time.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
