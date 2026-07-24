#!/usr/bin/env python3
"""
mm_client WebSocket client example for FastAPI server (Phase 1/2)

Usage:
    python client_example.py <session_id> [server_url]

Example:
    python client_example.py 550e8400-e29b-41d4-a716-446655440000
    python client_example.py 550e8400-e29b-41d4-a716-446655440000 ws://192.168.1.100:5000
"""

import asyncio
import json
import sys
import websockets


async def run_client(session_id: str, server_url: str = "ws://localhost:5000") -> None:
    """WebSocket クライアント（音声イベント確認用）"""

    ws_url = f"{server_url}/dialogue/ws/{session_id}"
    print(f"Connecting to {ws_url}...")

    try:
        async with websockets.connect(ws_url) as websocket:
            print("✓ Connected\n")

            welcome_msg = await websocket.recv()
            welcome = json.loads(welcome_msg)
            print(f"Server: {welcome}\n")

            print("Starting dialogue...")
            await websocket.send(json.dumps({"action": "start_dialogue"}))

            try:
                while True:
                    message = json.loads(await websocket.recv())
                    print(f"📨 Server: {message['event']}")
                    if message["event"] == "audio_data":
                        payload = message["payload"]
                        print(
                            f"   → audio_data utterance={payload['utterance_id']}"
                        )
                    elif message["event"] == "joined_session":
                        print(f"   → joined_session: {message['payload']['session_id']}")
                    elif message["event"] == "error":
                        print(f"   → error: {message['payload']['message']}")
                        
            except KeyboardInterrupt:
                print("\n\nInterrupted. Closing...")
                await websocket.send(json.dumps({"action": "end_dialogue"}))
            except websockets.exceptions.ConnectionClosed:
                print("⚠️  Connection closed")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


async def main():
    if len(sys.argv) < 2:
        print("Usage: python client_example.py <session_id> [server_url]")
        print("Example: python client_example.py 550e8400-e29b-41d4-a716-446655440000")
        sys.exit(1)
    
    session_id = sys.argv[1]
    server_url = sys.argv[2] if len(sys.argv) > 2 else "ws://localhost:5000"
    
    await run_client(session_id, server_url)


if __name__ == "__main__":
    asyncio.run(main())
