from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app import kakao_controller as kc

app = FastAPI(title="kakao_bridge", description="카카오톡 '나와의 채팅' 읽기/쓰기 로컬 브릿지")


class SendRequest(BaseModel):
    message: str
    wait_for_fullscreen: bool = True


def _max_wait(wait_for_fullscreen: bool):
    return None if wait_for_fullscreen else 0


@app.post("/send")
def send(req: SendRequest):
    try:
        kc.send_message(req.message, max_wait_sec=_max_wait(req.wait_for_fullscreen))
    except kc.FullscreenBlockedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except kc.KakaoBridgeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "ok"}


@app.get("/messages/last")
def read_last(wait_for_fullscreen: bool = True):
    try:
        result = kc.read_last_message(max_wait_sec=_max_wait(wait_for_fullscreen))
    except kc.FullscreenBlockedError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except kc.KakaoBridgeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    if result is None:
        raise HTTPException(status_code=404, detail="메시지가 없습니다.")
    return result


@app.get("/health")
def health():
    return {"status": "ok"}
