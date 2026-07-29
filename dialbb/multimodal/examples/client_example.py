import asyncio
import base64
import io
import json
import signal
import sys
import argparse
import wave
from dataclasses import dataclass

import pyaudio
import websockets


RATE = 16000
CHANNELS = 1
FORMAT = pyaudio.paInt16
CHUNK = 1600

AUX_DATA_DEBUG = {
    "debug": True,
    "source": "client_example.py",
}

running = True


@dataclass
class PlaybackState:
    generation: int = 0
    stop_reason: str = "cancel"
    stopped_utterance_id: int = 0


def request_playback_stop(playback_state: PlaybackState, reason: str, utterance_id: int = 0) -> None:
    playback_state.generation += 1
    playback_state.stop_reason = reason or "cancel"
    playback_state.stopped_utterance_id = max(playback_state.stopped_utterance_id, utterance_id)


def signal_handler(sig, frame):
    global running
    running = False
    print("\nStopping...", flush=True)


signal.signal(signal.SIGINT, signal_handler)


def log_client(message: str) -> None:
    print(f"[CLIENT] {message}", flush=True)


# sends a message over the WebSocket connection in a thread-safe manner. It uses an asyncio lock to ensure that only one send operation occurs at a time, preventing
async def safe_send(websocket, send_lock, message: dict) -> None:
    async with send_lock:
        await websocket.send(json.dumps(message))


def print_aux_data(message: dict) -> None:
    aux_data = message.get("aux_data")
    if aux_data is None:
        payload = message.get("payload")
        if isinstance(payload, dict):
            aux_data = payload.get("aux_data")

    if aux_data is not None:
        print(f"aux_data: {json.dumps(aux_data, ensure_ascii=False)}", flush=True)


# continuously reads audio data from the microphone, encodes it in base64, and sends it to the server over the WebSocket connection. It uses a lock to ensure that only one send operation occurs at a time, preventing potential race conditions.
async def send_microphone(websocket, send_lock, mic, playback_state):
    global running
    del playback_state

    while running:
        pcm = mic.read(CHUNK, exception_on_overflow=False)

        message = {
            "action": "send_audio_chunk",
            "audio_data": base64.b64encode(pcm).decode("utf-8"),
            "aux_data": AUX_DATA_DEBUG,
        }
        await safe_send(websocket, send_lock, message)
        await asyncio.sleep(0)

# notifies the server that a TTS segment has finished playing. It sends a message with the utterance ID, segment index, and segment count to inform the server that the playback of the specified segment is complete.
async def send_tts_segment_playback_done(
    websocket,
    send_lock,
    utterance_id,
    segment_index,
    segment_count,
):
    # Notify the server that a TTS segment has finished playing
    await safe_send(
        websocket,
        send_lock,
        {
            "action": "tts_segment_playback_done",
            "utterance_id": utterance_id,
            "segment_index": segment_index,
            "segment_count": segment_count,
            "aux_data": AUX_DATA_DEBUG,
        },
    )
    log_client(
        f"playback_done sent: utterance={utterance_id} segment={segment_index}/{segment_count}"
    )


async def send_stop_audio_done(websocket, send_lock, reason: str) -> None:
    await safe_send(
        websocket,
        send_lock,
        {
            "action": "stop_audio_done",
            "reason": reason,
            "aux_data": AUX_DATA_DEBUG,
        },
    )
    log_client(f"stop_audio_done sent: reason={reason}")


async def handle_stop_audio_control(websocket, send_lock, playback_queue, playback_state) -> None:
    preserved_items = []
    dropped_items = 0
    while True:
        try:
            queued_item = playback_queue.get_nowait()
        except asyncio.QueueEmpty:
            break
        if queued_item is None:
            preserved_items.append(None)
            break
        if queued_item.get("_control") == "stop_audio":
            continue
        if int(queued_item.get("utterance_id") or 0) <= playback_state.stopped_utterance_id:
            dropped_items += 1
            continue
        preserved_items.append(queued_item)

    for queued_item in preserved_items:
        await playback_queue.put(queued_item)

    log_client(
        "stop_audio handled: "
        f"reason={playback_state.stop_reason} stopped_utterance={playback_state.stopped_utterance_id} "
        f"preserved={len(preserved_items)} dropped={dropped_items}"
    )

    await send_stop_audio_done(websocket, send_lock, playback_state.stop_reason)


# decodes a WAV audio payload from bytes and returns the raw PCM audio data. It uses the wave module to read the WAV file format and extract the audio frames.
def decode_wav_payload(wav_bytes: bytes) -> bytes:
    with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
        # Read the WAV file and return the raw PCM audio data
        return wav_file.readframes(wav_file.getnframes())


def play_pcm_interruptible(
    output_stream,
    pcm_bytes: bytes,
    playback_state: PlaybackState,
    generation: int,
) -> bool:
    bytes_per_chunk = CHUNK * CHANNELS * 2
    for offset in range(0, len(pcm_bytes), bytes_per_chunk):
        if generation != playback_state.generation:
            return True
        output_stream.write(pcm_bytes[offset:offset + bytes_per_chunk])
    return generation != playback_state.generation


# handles the playback of audio segments received from the server. It reads audio data from a queue, decodes it, and plays it through the audio output stream. It also notifies the server when each segment has finished playing.
async def playback_worker(websocket, send_lock, playback_queue, playback_state, pa):
    global running

    # Open an audio output stream for playback
    output_stream = pa.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        output=True,
        frames_per_buffer=CHUNK,
    )

    try:
        while running:
            try:
                # Get the next payload from the playback queue, waiting if necessary
                payload = await playback_queue.get()
            except asyncio.CancelledError:
                break

            if payload is None:
                break

            if payload.get("_control") == "stop_audio":
                log_client(
                    f"stop_audio received in playback loop: reason={payload.get('reason')} "
                    f"utterance={int(payload.get('utterance_id') or 0)}"
                )
                request_playback_stop(
                    playback_state,
                    str(payload.get("reason") or "cancel"),
                    int(payload.get("utterance_id") or 0),
                )
                output_stream.stop_stream()
                output_stream.start_stream()
                await handle_stop_audio_control(websocket, send_lock, playback_queue, playback_state)
                continue

            # Extract segment information from the payload
            generation = playback_state.generation
            utterance_id = int(payload.get("utterance_id") or 0)
            segment_index = int(payload["segment_index"])
            segment_count = int(payload["segment_count"])

            if utterance_id <= playback_state.stopped_utterance_id:
                log_client(
                    f"audio skipped as stopped: utterance={utterance_id} segment={segment_index}/{segment_count} "
                    f"stopped_utterance={playback_state.stopped_utterance_id}"
                )
                continue

            if int(payload.get("_generation", generation)) != generation:
                log_client(
                    f"audio skipped as stale generation: utterance={utterance_id} "
                    f"segment={segment_index}/{segment_count} payload_generation={payload.get('_generation')} "
                    f"current_generation={generation}"
                )
                continue

            # Decode the base64-encoded WAV audio data and convert it to PCM bytes
            wav_bytes = base64.b64decode(payload["audio"])
            pcm_bytes = decode_wav_payload(wav_bytes)
            log_client(
                f"playback start: utterance={utterance_id} segment={segment_index}/{segment_count} "
                f"wav_bytes={len(wav_bytes)} pcm_bytes={len(pcm_bytes)} generation={generation}"
            )

            interrupted = await asyncio.to_thread(
                play_pcm_interruptible,
                output_stream,
                pcm_bytes,
                playback_state,
                generation,
            )

            if generation != playback_state.generation or interrupted:
                log_client(
                    f"playback interrupted: utterance={utterance_id} segment={segment_index}/{segment_count} "
                    f"start_generation={generation} current_generation={playback_state.generation}"
                )
                output_stream.stop_stream()
                output_stream.start_stream()
                continue

            log_client(
                f"playback finished: utterance={utterance_id} segment={segment_index}/{segment_count}"
            )

            # Notify the server that the TTS segment playback is done
            await send_tts_segment_playback_done(
                websocket,
                send_lock,
                utterance_id,
                segment_index,
                segment_count,
            )
    finally:
        output_stream.stop_stream()
        output_stream.close()


# handles incoming messages from the server over the WebSocket connection. It processes different types of events, such as audio data, session join notifications, and error messages. Audio data is added to a playback queue for processing by the playback worker.
async def receiver(websocket, playback_queue, playback_state):
    global running

    while running:
        # Wait for a message from the server
        message = json.loads(await websocket.recv())
        event = message["event"]

        if event == "audio_data":
            # Add the received audio data payload to the playback queue for processing by the playback worker
            print_aux_data(message)
            payload = dict(message["payload"])
            log_client(
                f"event audio_data: utterance={int(payload.get('utterance_id') or 0)} "
                f"segment={int(payload.get('segment_index') or 0)}/{int(payload.get('segment_count') or 0)} "
                f"wav_bytes={len(base64.b64decode(payload['audio']))} current_generation={playback_state.generation}"
            )
            if int(payload.get("utterance_id") or 0) <= playback_state.stopped_utterance_id:
                log_client(
                    f"audio_data dropped before queue: utterance={int(payload.get('utterance_id') or 0)} "
                    f"stopped_utterance={playback_state.stopped_utterance_id}"
                )
                continue
            payload["_generation"] = playback_state.generation
            await playback_queue.put(payload)
            log_client(
                f"audio queued: utterance={int(payload.get('utterance_id') or 0)} "
                f"segment={int(payload.get('segment_index') or 0)}/{int(payload.get('segment_count') or 0)} "
                f"queue_size={playback_queue.qsize()} generation={payload['_generation']}"
            )
        elif event == "stop_audio":
            print_aux_data(message)
            log_client(
                f"event stop_audio: reason={message.get('payload', {}).get('reason')} "
                f"utterance={int(message.get('payload', {}).get('utterance_id') or 0)}"
            )
            request_playback_stop(
                playback_state,
                str(message.get("payload", {}).get("reason") or "cancel"),
                int(message.get("payload", {}).get("utterance_id") or 0),
            )
            await playback_queue.put(
                {
                    "_control": "stop_audio",
                    "reason": playback_state.stop_reason,
                    "utterance_id": playback_state.stopped_utterance_id,
                }
            )
        elif event == "joined_session":
            print_aux_data(message)
            print("joined:", message["payload"]["session_id"], flush=True)
            log_client(f"joined session: {message['payload']['session_id']}")
        elif event == "error":
            print_aux_data(message)
            print("error:", message["payload"]["message"], flush=True)
            log_client(f"event error: {message['payload']['message']}")
        else:
            print_aux_data(message)
            log_client(f"event {event}: {json.dumps(message.get('payload', {}), ensure_ascii=False)}")


# runs the WebSocket client, connecting to the server and managing the microphone input, audio playback, and message handling. It sets up tasks for sending microphone data, receiving messages, and playing back audio segments.
async def run_client(session_id: str, server_url: str = "ws://localhost:5000") -> None:
    ws_url = f"{server_url}/dialogue/ws/{session_id}"
    print(f"Connecting to {ws_url}...", flush=True)

    # Initialize PyAudio for microphone input
    pa = pyaudio.PyAudio()

    # Open a microphone input stream with the specified format, channels, rate, and chunk size
    mic = pa.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK,
    )

    playback_queue = asyncio.Queue()
    playback_state = PlaybackState()
    send_lock = asyncio.Lock()

    try:
        # Connect to the WebSocket server and handle the dialogue session
        async with websockets.connect(ws_url) as websocket:
            print("✓ Connected\n", flush=True)

            # Receive the welcome message from the server and print it
            welcome_msg = await websocket.recv()
            welcome = json.loads(welcome_msg)
            print(f"Server: {welcome}\n", flush=True)

            print("Starting dialogue...", flush=True)

            # Notify the server that the dialogue session is starting
            await safe_send(
                websocket,
                send_lock,
                {"action": "start_dialogue", "aux_data": AUX_DATA_DEBUG},
            )

            # Create tasks for sending microphone data, receiving messages, and playing back audio segments
            send_task = asyncio.create_task(send_microphone(websocket, send_lock, mic, playback_state))
            recv_task = asyncio.create_task(receiver(websocket, playback_queue, playback_state))
            play_task = asyncio.create_task(
                playback_worker(websocket, send_lock, playback_queue, playback_state, pa)
            )

            try:
                while running:
                    # Keep the main loop running to allow tasks to operate concurrently
                    await asyncio.sleep(0.1)
            finally:
                # Cancel the tasks and clean up resources when stopping the client
                send_task.cancel()
                recv_task.cancel()
                play_task.cancel()
                await playback_queue.put(None)

                try:
                    # Notify the server that the dialogue session is ending
                    await safe_send(
                        websocket,
                        send_lock,
                        {"action": "end_dialogue", "aux_data": AUX_DATA_DEBUG},
                    )
                except Exception:
                    pass

    except Exception as e:
        print(e)

    finally:
        # Clean up the microphone and PyAudio resources
        mic.stop_stream()
        mic.close()
        pa.terminate()
        print("Exit")


async def main():
    parser = argparse.ArgumentParser(description="WebSocket client example")
    parser.add_argument("session_id", help="Session ID")
    parser.add_argument("server_url", nargs="?", default="ws://localhost:5000",
        help="WebSocket server URL (default: %(default)s)"
    )
    args = parser.parse_args()

    session_id = args.session_id
    server_url = args.server_url
    await run_client(session_id, server_url)


if __name__ == "__main__":
    asyncio.run(main())
