#!/usr/bin/env python3
"""
mm_client Phase 1/2 動作確認スクリプト
"""
import json
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: requests ライブラリが必要です")
    print("  pip install requests")
    sys.exit(1)

try:
    from socketio import Client
except ImportError:
    print("Error: python-socketio ライブラリが必要です")
    print("  pip install python-socketio")
    sys.exit(1)


BASE_URL = "http://localhost:5000"
SOCKETIO_URL = "http://localhost:5000"


def test_health():
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


def test_rest_api():
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


def test_websocket():
    """WebSocket API テスト"""
    print("\n=== WebSocket API テスト ===")
    
    sio = Client()
    
    @sio.event(namespace="/dialogue")
    def connect():
        print("✓ WebSocket 接続成功")
        # セッション作成
        print("\n1. セッション作成")
        resp = requests.post(f"{BASE_URL}/sessions", timeout=5)
        session_id = resp.json()["session_id"]
        print(f"Session ID: {session_id}")
        
        # セッション参加
        print("\n2. セッション参加")
        sio.emit("join_session", {"session_id": session_id}, namespace="/dialogue")
    
    @sio.event(namespace="/dialogue")
    def joined_session(data):
        print(f"✓ セッション参加成功: {data}")
    
    @sio.event(namespace="/dialogue")
    def dialogue_event(data):
        print(f"📨 イベント受信: {data['event_type']}")
        if data['event_type'] in ('status', 'chat', 'error'):
            print(f"   → {data['data']}")
    
    @sio.on("error", namespace="/dialogue")
    def on_error(data):
        print(f"❌ エラー: {data}")
    
    try:
        sio.connect(SOCKETIO_URL, namespaces=["/dialogue"], wait_timeout=10)
        time.sleep(3)
        sio.disconnect()
        print("\n✓ WebSocket テスト完了")
    except Exception as e:
        print(f"❌ エラー: {e}")


def main():
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
    test_rest_api()
    
    # 3. WebSocket API テスト
    try:
        test_websocket()
    except ImportError:
        print("\n⚠️ WebSocket テスト: python-socketio がインストールされていません")
        print("  pip install python-socketio")
    
    print("\n" + "=" * 60)
    print("✓ 動作確認完了")
    print("=" * 60)


if __name__ == "__main__":
    main()
