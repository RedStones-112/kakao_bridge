from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from app import kakao_channel
from app import kakao_oauth

app = FastAPI(title="kakao_bridge", description="카카오톡 채널/나에게 보내기 기반 공식 API 브릿지")


class SendRequest(BaseModel):
    message: str


@app.get("/oauth/authorize")
def oauth_authorize():
    """브라우저에서 이 주소를 열면 카카오 로그인 동의 화면으로 이동한다 (최초 1회만 필요)."""
    return RedirectResponse(kakao_oauth.build_authorize_url())


@app.get("/oauth/callback")
def oauth_callback(code: str):
    kakao_oauth.exchange_code_for_token(code)
    return HTMLResponse("<h3>카카오 로그인 연동 완료. 이 창은 닫아도 됩니다.</h3>")


@app.post("/send")
def send(req: SendRequest):
    try:
        kakao_oauth.send_to_me(req.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"공식 API 전송 실패: {e}")
    return {"status": "ok"}


@app.get("/messages/last")
def read_last():
    result = kakao_channel.get_last_inbound_message()
    if result is None:
        raise HTTPException(status_code=404, detail="아직 채널로 받은 메시지가 없습니다.")
    return result


@app.post("/kakao/skill")
async def kakao_skill(request: Request):
    """카카오 i 오픈빌더 스킬 서버(웹훅). 채널로 메시지가 오면 카카오가 이건로 POST한다."""
    payload = await request.json()
    user_request = payload.get("userRequest", {})
    utterance = user_request.get("utterance", "")
    user_id = user_request.get("user", {}).get("id", "unknown")
    kakao_channel.save_inbound_message(utterance, user_id)
    return {
        "version": "2.0",
        "template": {"outputs": [{"simpleText": {"text": "전달했습니다."}}]},
    }


@app.get("/health")
def health():
    return {"status": "ok"}
