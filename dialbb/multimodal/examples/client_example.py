import asyncio
import base64
import io
import json
import signal
import sys
import argparse
import wave

import pyaudio
import websockets


RATE = 16000
CHANNELS = 1
FORMAT = pyaudio.paInt16
CHUNK = 1600
PLAYBACK_PRIME_CHUNKS = 1   # Number of audio chunks to buffer before playback to reduce latency

AUX_DATA_DEBUG = {
    "debug": True,
    "source": "client_example.py",
}

running = True


def signal_handler(sig, frame):
    global running
    running = False
    print("\nStopping...", flush=True)


signal.signal(signal.SIGINT, signal_handler)


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
async def send_microphone(websocket, send_lock, mic):
    global running

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


# decodes a WAV audio payload from bytes and returns the raw PCM audio data. It uses the wave module to read the WAV file format and extract the audio frames.
def decode_wav_payload(wav_bytes: bytes) -> bytes:
    with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
        # Read the WAV file and return the raw PCM audio data
        return wav_file.readframes(wav_file.getnframes())


# handles the playback of audio segments received from the server. It reads audio data from a queue, decodes it, and plays it through the audio output stream. It also notifies the server when each segment has finished playing.
async def playback_worker(websocket, send_lock, playback_queue, pa):
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

            # Extract segment information from the payload
            segment_index = int(payload["segment_index"])
            segment_count = int(payload["segment_count"])
            utterance_id = int(payload.get("utterance_id") or 0)

            buffered = [payload]
            # Buffer additional segments if available, up to PLAYBACK_PRIME_CHUNKS
            for _ in range(PLAYBACK_PRIME_CHUNKS - 1):
                try:
                    # Wait for the next payload with a short timeout to avoid blocking indefinitely
                    next_payload = await asyncio.wait_for(playback_queue.get(), timeout=0.03)
                except asyncio.TimeoutError:
                    break
                if next_payload is None:
                    break

                # Check if the next payload belongs to the same utterance and is the next segment
                buffered.append(next_payload)

            # Play the buffered audio segments in order
            for item in buffered:
                if not running:
                    break

                # Decode the base64-encoded WAV audio data and convert it to PCM bytes
                wav_bytes = base64.b64decode(item["audio"])
                pcm_bytes = decode_wav_payload(wav_bytes)

                # Play the PCM audio data in a separate thread to avoid blocking the event loop
                await asyncio.to_thread(output_stream.write, pcm_bytes)

                # Notify the server that the TTS segment playback is done
                await send_tts_segment_playback_done(
                    websocket,
                    send_lock,
                    int(item.get("utterance_id") or 0),
                    int(item["segment_index"]),
                    int(item["segment_count"]),
                )
    finally:
        output_stream.stop_stream()
        output_stream.close()


# handles incoming messages from the server over the WebSocket connection. It processes different types of events, such as audio data, session join notifications, and error messages. Audio data is added to a playback queue for processing by the playback worker.
async def receiver(websocket, playback_queue):
    global running

    while running:
        # Wait for a message from the server
        message = json.loads(await websocket.recv())
        event = message["event"]

        if event == "audio_data":
            # Add the received audio data payload to the playback queue for processing by the playback worker
            print_aux_data(message)
            await playback_queue.put(message["payload"])
        elif event == "joined_session":
            print_aux_data(message)
            print("joined:", message["payload"]["session_id"], flush=True)
        elif event == "error":
            print_aux_data(message)
            print("error:", message["payload"]["message"], flush=True)
        else:
            print_aux_data(message)


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
            send_task = asyncio.create_task(send_microphone(websocket, send_lock, mic))
            recv_task = asyncio.create_task(receiver(websocket, playback_queue))
            play_task = asyncio.create_task(playback_worker(websocket, send_lock, playback_queue, pa))

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
