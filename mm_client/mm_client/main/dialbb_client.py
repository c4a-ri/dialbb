from queue import Empty, Queue
from threading import Event

from main.messages import DialbbRequest, DialbbResponse


def run_dialbb_worker(
    dialbb_request_queue: "Queue[DialbbRequest]",
    dialbb_response_queue: "Queue[DialbbResponse]",
    stop_event: Event,
) -> None:
    """DialBB client worker thread.

    Current implementation is a local stub. Replace `_build_response` with real DialBB API call.
    """
    while not stop_event.is_set():
        try:
            request = dialbb_request_queue.get(timeout=0.1)
        except Empty:
            continue
        print(f"[Dialbb] リクエスト受信: {request.user_text}")

        system_text = _build_response(request.user_text)
        dialbb_response_queue.put(
            DialbbResponse(session_id=request.session_id, system_text=system_text)
        )


def _build_response(user_text: str) -> str:
    trimmed = user_text.strip()
    if not trimmed:
        return "聞き取れませんでした。もう一度お願いします。"
    # Stub response is fixed for now; replace with real DialBB API call later.
    return "承知しました。続けてお話しください。"
