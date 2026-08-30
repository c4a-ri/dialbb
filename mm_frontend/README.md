# DialBB Multimodal Mobile Frontend

DialBB multimodal server向けのモバイルPWAクライアントです。

## 開発

```bash
npm install
npm run dev
```

既定の開発URLは `http://localhost:5173` です。

## 本番ビルド

```bash
npm run build
```

ビルド結果は `dialbb/multimodal/static/mobile` に出力されます。
この出力を `dialbb/multimodal/server.py` が `/` で配信します。

## 接続先

`?server=` クエリか `VITE_MM_SERVER_URL` で明示しない限り、
本番時は同一originのmultimodal API (`/sessions`, `/dialogue/ws/*`) へ接続します。
