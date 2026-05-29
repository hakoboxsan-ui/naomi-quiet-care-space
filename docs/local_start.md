# NAOMI local desktop startup

Windows のローカルデモでは、プロジェクト直下の `start_naomi_desktop.bat` をダブルクリックします。

## 起動方法

1. `D:\NAOMI_Project\start_naomi_desktop.bat` をダブルクリックします。
2. 既定ブラウザで `http://localhost:8507` が開きます。
3. デモ中は黒い起動ウィンドウを閉じずに残します。
4. 終了するときは起動ウィンドウで `Ctrl+C` を押します。

## 動作

- `frontend/streamlit_app.py` を Streamlit で起動します。
- ポートは `8507` を使います。
- すでに NAOMI が `8507` で起動している場合は、新しい Streamlit プロセスを増やさずブラウザだけ開きます。
- `8507` が別プロセスで使用中の場合は、理由を表示して停止します。
- ランチャーログは `D:\NAOMI_Project\logs\start_naomi_desktop.log` に追記されます。
- Streamlit の実行ログは `D:\NAOMI_Project\logs\streamlit_8507.log` に追記されます。

## Python / Streamlit エラー

起動時に Python または Streamlit が見つからない場合は、黒い画面に原因とインストール例が表示されます。画面は自動で閉じないので、表示内容を確認してください。

## デスクトップショートカットを作る場合

自動でデスクトップにファイルは作りません。必要な場合は、`D:\NAOMI_Project\start_naomi_desktop.bat` を右クリックして「送る」から「デスクトップ (ショートカットを作成)」を選んでください。
