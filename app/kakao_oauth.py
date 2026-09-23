"""카카오 로그인 OAuth + '나에게 보내기' 메시지 API 래퍼."""
import json
import os
import time
import urllib.parse

import httpx

TOKEN_STORE_PATH = os.path.join(os.path.dirname(__file__), ".kakao_token.json")

KAKAO_REST_API_KEY = os.environ["KAKAO_REST_API_KEY"]
KAKAO_CLIENT_SECRET = os.environ.get("KAKAO_CLIENT_SECRET")  # 활성화된 경우만 필요
KAKAO_REDIRECT_URI = os.environ["KAKAO_REDIRECT_URI"]

AUTHORIZE_URL = "https://kauth.kakao.com/oauth/authorize"
TOKEN_URL = "https://kauth.kakao.com/oauth/token"
MEMO_SEND_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"


def build_authorize_url() -> str:
    params = {
        "client_id": KAKAO_REST_API_KEY,
        "redirect_uri": KAKAO_REDIRECT_URI,
        "response_type": "code",
        "scope": "talk_message",
    }
    return f"{AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


def _save_tokens(data: dict) -> None:
    data = dict(data)
    data["obtained_at"] = time.time()
    with open(TOKEN_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)


def _load_tokens() -> dict | None:
    if not os.path.exists(TOKEN_STORE_PATH):
        return None
    with open(TOKEN_STORE_PATH, encoding="utf-8") as f:
        return json.load(f)


def exchange_code_for_token(code: str) -> dict:
    data = {
        "grant_type": "authorization_code",
        "client_id": KAKAO_REST_API_KEY,
        "redirect_uri": KAKAO_REDIRECT_URI,
        "code": code,
    }
    if KAKAO_CLIENT_SECRET:
        data["client_secret"] = KAKAO_CLIENT_SECRET
    resp = httpx.post(TOKEN_URL, data=data)
    resp.raise_for_status()
    tokens = resp.json()
    _save_tokens(tokens)
    return tokens


def _refresh_access_token(refresh_token: str) -> dict:
    data = {
        "grant_type": "refresh_token",
        "client_id": KAKAO_REST_API_KEY,
        "refresh_token": refresh_token,
    }
    if KAKAO_CLIENT_SECRET:
        data["client_secret"] = KAKAO_CLIENT_SECRET
    resp = httpx.post(TOKEN_URL, data=data)
    resp.raise_for_status()
    new_tokens = resp.json()
    merged = _load_tokens() or {}
    merged.update(new_tokens)
    _save_tokens(merged)
    return merged


def get_valid_access_token() -> str:
    tokens = _load_tokens()
    if tokens is None:
        raise RuntimeError(
            "카카오 로그인 토큰이 없습니다. 먼저 /oauth/authorize 로 로그인 동의를 받아야 합니다."
        )
    expires_in = tokens.get("expires_in", 0)
    obtained_at = tokens.get("obtained_at", 0)
    if time.time() >= obtained_at + expires_in - 60:
        tokens = _refresh_access_token(tokens["refresh_token"])
    return tokens["access_token"]


SEND_LABEL = "[PC Bridge] "


def send_to_me(text: str) -> None:
    access_token = get_valid_access_token()
    template_object = {
        "object_type": "text",
        "text": SEND_LABEL + text,
        "link": {},
    }
    resp = httpx.post(
        MEMO_SEND_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        data={"template_object": json.dumps(template_object)},
    )
    resp.raise_for_status()
    result = resp.json()
    if result.get("result_code") != 0:
        raise RuntimeError(f"카카오 메시지 전송 실패: {result}")
