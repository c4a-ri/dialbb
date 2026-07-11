#!/usr/bin/env python3
"""
mm_client Phase 1/2 動作確認スクリプト
"""
import json
import asyncio
import sys
import base64
import os

try:
    import requests
except ImportError:
    print("Error: requests ライブラリが必要です")
    print("  pip install requests")
    sys.exit(1)

try:
    import websockets
except ImportError:
    print("Error: websockets ライブラリが必要です")
    print("  pip install websockets")
    sys.exit(1)


BASE_URL = "http://localhost:5000"
WS_BASE_URL = "ws://localhost:5000"


def test_health() -> bool:
    """ヘルスチェック"""
    print("\n=== ヘルスチェック ===")
    try:
        resp = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_rest_api() -> str | None:
    """REST API テスト"""
    print("\n=== REST API テスト ===")
    
    # セッション作成
    print("\n1. セッション作成")
    try:
        resp = requests.post(f"{BASE_URL}/sessions", timeout=5)
        if resp.status_code != 201:
            print(f"Error: Status {resp.status_code}")
            return None
        session_data = resp.json()
        session_id = session_data["session_id"]
        print(f"✓ Session ID: {session_id}")
    except Exception as e:
        print(f"Error: {e}")
        return None
    
    # セッション開始
    print("\n2. セッション開始")
    try:
        resp = requests.post(f"{BASE_URL}/sessions/{session_id}/start", timeout=5)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")
    except Exception as e:
        print(f"Error: {e}")
    
    # テキスト発話（REST）
    print("\n3. テキスト発話送信")
    try:
        resp = requests.post(
            f"{BASE_URL}/sessions/{session_id}/utterance",
            json={"text": "テストメッセージです"},
            timeout=5,
        )
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")
    except Exception as e:
        print(f"Error: {e}")
    
    # セッション一覧
    print("\n4. セッション一覧確認")
    try:
        resp = requests.get(f"{BASE_URL}/sessions", timeout=5)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")
    except Exception as e:
        print(f"Error: {e}")
    
    # セッション停止
    print("\n5. セッション停止")
    try:
        resp = requests.post(f"{BASE_URL}/sessions/{session_id}/stop", timeout=5)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")
    except Exception as e:
        print(f"Error: {e}")
    
    # セッション削除
    print("\n6. セッション削除")
    try:
        resp = requests.delete(f"{BASE_URL}/sessions/{session_id}", timeout=5)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")
    except Exception as e:
        print(f"Error: {e}")
    
    return session_id

AUDIO_DATA = ["testUser-taro.wav", "testUser-yes.wav", "testUser-yes.wav",
              "testUser-syou.wav", "testUser-no.wav"]

async def test_websocket() -> None:
    """FastAPI ネイティブ WebSocket API テスト"""
    print("\n=== WebSocket API テスト ===")

    print("\n1. セッション作成")
    resp = requests.post(f"{BASE_URL}/sessions", timeout=5)
    print(f"Status: {resp.status_code}")
    if resp.status_code != 201:
        print(f"❌ セッション作成失敗: {resp.status_code} {resp.text}")
        return
    session_id = resp.json()["session_id"]
    print(f"✓ Session ID: {session_id}")

    ws_url = f"{WS_BASE_URL}/dialogue/ws/{session_id}"
    print(f"\n2. WebSocket 接続: {ws_url}")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        async with websockets.connect(ws_url) as ws:
            joined_raw = await ws.recv()
            joined = json.loads(joined_raw)
            print(f"✓ 接続イベント: {joined}")

            print("\n3. 対話開始")
            await ws.send(json.dumps({"action": "start_dialogue"}))

            print("\n4. 音声データ送信")
            if AUDIO_DATA:
                audio_file = AUDIO_DATA.pop(0)
                file_path = os.path.join(current_dir, "data", audio_file)
                print(f"  - 音声ファイル: {audio_file}")
                with open(file_path, "rb") as f:
                    audio_data = f.read()
                # base64 PCM16kHz 16bit mono 形式でエンコードする
                audio_base64 = base64.b64encode(audio_data).decode("utf-8")
                print(f"  - 音声データサイズ: {len(audio_data)} bytes, base64サイズ: {len(audio_base64)} chars")
                await ws.send(json.dumps({"action": "send_audio_chunk", "audio_data": audio_base64}))

            print("\n5. サーバイベント受信(最大10件 / 各15秒待ち)")
            for _ in range(50):
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=15)
                except TimeoutError:
                    print("  - (timeout) 追加イベントなし")
                    break
                event = json.loads(message)
                if event.get("event") == "audio_data":
                    print(f"📨 {event.get('event')}: audio: AAAAA...")
                else:
                    print(f"📨 {event.get('event')}: {event.get('payload')}")
                print(f"  - 発話: {event.get('payload', {}).get('data', {}).get('message')}")

            print("\n6. 対話終了")
            await ws.send(json.dumps({"action": "end_dialogue"}))

        print("\n✓ WebSocket テスト完了")
    except Exception as e:
        print(f"❌ エラー: {e}")


def main() -> None:
    print("=" * 60)
    print("mm_client Phase 1/2 動作確認")
    print("=" * 60)
    
    # 1. ヘルスチェック
    if not test_health():
        print("\n❌ サーバが起動していません")
        print("以下を実行してください:")
        print("  dialbb-mm-client-server --config config/mm_client_config.yml")
        sys.exit(1)
    
    # 2. REST API テスト
    # test_rest_api()
    
    # 3. WebSocket API テスト
    asyncio.run(test_websocket())
    
    print("\n" + "=" * 60)
    print("✓ 動作確認完了")
    print("=" * 60)


if __name__ == "__main__":
    main()
