"""카카오 채널 + 오픈빌더 스킴(웹훅)으로 받은 메시지를 저장/조회한다.
창을 띄우는 UI 자동화가 전혀 없는, 순수 웹훅 기반 읽기 경로다.
"""
import json
import os
import time

INBOUND_STORE_PATH = os.path.join(os.path.dirname(__file__), ".last_inbound.json")


def save_inbound_message(text: str, user_id: str) -> None:
    data = {
        "sender": user_id,
        "text": text,
        "received_at": time.time(),
    }
    with open(INBOUND_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


def get_last_inbound_message() -> dict | None:
    if not os.path.exists(INBOUND_STORE_PATH):
        return None
    with open(INBOUND_STORE_PATH, encoding="utf-8") as f:
        return json.load(f)
