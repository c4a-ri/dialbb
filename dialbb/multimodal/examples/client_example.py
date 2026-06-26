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
    """WebSocket クライアント（対話デモ）"""
    
    ws_url = f"{server_url}/dialogue/ws/{session_id}"
    print(f"Connecting to {ws_url}...")
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("✓ Connected\n")
            
            # 接続イベントを受信
            welcome_msg = await websocket.recv()
            welcome = json.loads(welcome_msg)
            print(f"Server: {welcome}\n")
            
            # 対話開始
            print("Starting dialogue...")
            await websocket.send(json.dumps({"action": "start_dialogue"}))
            
            # バックグラウンドタスク：サーバイベントを受信して表示
            async def listen_to_server():
                try:
                    while True:
                        message = await websocket.recv()
                        event = json.loads(message)
                        print(f"📨 Server: {event['event']}")
                        if event["event"] == "dialogue_event":
                            payload = event["payload"]
                            print(f"   → {payload['event_type']}: {payload['data']}")
                except websockets.exceptions.ConnectionClosed:
                    print("⚠️  Connection closed")
                except Exception as e:
                    print(f"❌ Error receiving: {e}")
            
            # バックグラウンドリスナーを起動
            listener_task = asyncio.create_task(listen_to_server())
            
            # 対話ループ
            try:
                while True:
                    user_input = await asyncio.get_event_loop().run_in_executor(None, input, "You: ")
                    
                    if user_input.lower() in ("exit", "quit", "q"):
                        print("Ending dialogue...")
                        await websocket.send(json.dumps({"action": "end_dialogue"}))
                        await asyncio.sleep(0.5)
                        break
                    
                    # テキスト発話を送信
                    await websocket.send(json.dumps({
                        "action": "send_text_utterance",
                        "text": user_input
                    }))
                    
            except KeyboardInterrupt:
                print("\n\nInterrupted. Closing...")
                await websocket.send(json.dumps({"action": "end_dialogue"}))
            finally:
                listener_task.cancel()
                try:
                    await listener_task
                except asyncio.CancelledError:
                    pass
    
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
