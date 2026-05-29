# NAOMI Project Cloud Run デプロイ手順

このドキュメントは、NAOMI Project を Google Cloud Run に提出・デプロイするための最小手順をまとめたものです。既存の Streamlit UI、デモシナリオ、Gemini 未設定時の fallback 構造を維持したまま、Cloud Run 上で起動できる構成を前提にしています。

## 起動方法

ローカルで Cloud Run 相当の待ち受け設定を確認する場合は、プロジェクトルートで次のコマンドを実行します。

```bash
streamlit run frontend/streamlit_app.py --server.port=8080 --server.address=0.0.0.0 --server.headless=true
```

Docker コンテナでは `Dockerfile` の `CMD` により、Cloud Run が注入する `PORT` 環境変数を使って Streamlit を起動します。`PORT` が未設定の場合は `8080` を使用します。

```bash
streamlit run frontend/streamlit_app.py --server.address=0.0.0.0 --server.port=${PORT:-8080} --server.headless=true
```

## 必要環境変数

Gemini API を有効にする場合は、次のいずれかの環境変数を設定してください。どちらも未設定の場合、NAOMI は既存のルールベース fallback で動作します。

| 環境変数 | 用途 | 備考 |
|---|---|---|
| `GEMINI_API_KEY` | Gemini API キー | 推奨名です。 |
| `GOOGLE_API_KEY` | Gemini API キー | 既存運用との互換用です。 |
| `PORT` | Cloud Run の待ち受けポート | Cloud Run が自動注入します。通常は手動設定不要です。 |

## Cloud Run デプロイ手順

Google Cloud CLI が設定済みで、対象プロジェクトが選択されている状態で、プロジェクトルートから以下を実行します。

```bash
gcloud run deploy naomi-project \
  --source . \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=YOUR_GEMINI_API_KEY
```

API キーをコマンド履歴に残したくない場合は、Google Secret Manager を使用し、Cloud Run の環境変数またはシークレット参照として設定してください。Gemini を使わないデモ提出では、`GEMINI_API_KEY` と `GOOGLE_API_KEY` を未設定にしても fallback で起動します。

## fallback 説明

`agent/gemini_brain.py` は `GEMINI_API_KEY` または `GOOGLE_API_KEY` が設定されている場合のみ Gemini API を初期化します。どちらも未設定の場合、`GeminiBrain.is_available` は `False` となり、API 呼び出しは行われません。

Gemini が利用できない場合でも、NAOMI は既存のローカル処理により、状態推定、応答生成、ケア提案、スタッフノート生成を継続します。このため、Cloud Run 提出時に API キーが未設定でもアプリ自体は起動可能です。ただし、Gemini による高度な応答生成や状態解析は無効になります。

## 注意事項

`data/personal_profiles.json` などローカルファイルへの保存は、Cloud Run ではコンテナインスタンス内の一時的な保存になります。提出・デモ用途では動作確認に使えますが、永続保存が必要な本番運用では Cloud Storage、Firestore、Cloud SQL などの外部ストレージへ移行してください。
