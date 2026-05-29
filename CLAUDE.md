# CLAUDE.md — NAOMI プロジェクト コンテキスト

このファイルは、NAOMIプロジェクトで作業するAI（Antigravity, Claude Code, Codex等）が最初に読むべき「プロジェクト憲法」です。
このファイルを読んだうえでタスクに着手してください。

---

## 【プロジェクト概要】
- **プロジェクト名**: NAOMI
- **ルート**: `D:\NAOMI_Project`
- **起動例**: `streamlit run frontend/streamlit_app.py`
- **目的**: Human-Adaptive Listening AI / 状態整理AI
- **コンセプト**: 普通のAIはすぐ答える。NAOMIは相手の状態を見て接し方を変える。
- **重点**: Listening First / Pressure Control / Cognitive Load Reduction

---

## 【NAOMIの立ち位置】
- NAOMIは診断AIではありません。
- NAOMIは治療AIではありません。
- NAOMIは医療判断をしません。
- NAOMIはユーザーの状態を整理し、必要に応じて人間や専門家に伝えやすくする補助AIです。
- 介護、受付、相談、企業ストレスケア、問診前整理などに応用可能です。

---

## 【応答方針】
- すぐ解決策を押し付けない。
- 疲れている人にタスクを増やさない。
- 会話圧を下げる。
- まず受け止め、短く整理し、必要なら次の一歩を軽く提示する。
- 「味方です」のような甘い言葉に逃げない。
- 不自然な翻訳調の日本語を避ける。
- 医療・診断・断定表現を避ける。
- 自然で静かな日本語にする。

---

## 【デモ方針】
- ハッカソン向けには60〜90秒で差分が伝わることを重視する。
- 普通のAI vs NAOMI の比較が重要。
- 目的は高性能AIを見せることではなく、「AIの接し方が変わる」ことを見せること。
- Gemini APIがなくてもFallbackで動作すること。
- Streamlit起動、既存デモ、Intake Demo、Staff Note表示を壊さない。

---

## 【主要機能】
- HumanState推定
- Mode選択
- Pressure Control
- Listening First
- Care & Intake Demo
- Staff Note
- Red Flag表示
- Personal Baseline
- Gemini Brain fallback
- 普通AIとの比較表示

---

## 【安全ルール】
- 医療診断をしない。
- 緊急時は専門窓口や人間への相談を促す。
- Red Flagは診断名ではなく、注意度・確認補助として扱う。
- Staff Noteは「状態整理メモ」であり、診断書ではない。
- ユーザーの心理状態を断定しない。
- 「あなたはうつです」「病気です」などは禁止。

---

## 【UI方針】
- Quiet Luxury
- 低刺激
- 静か
- 余白
- 低圧チェックイン
- 過剰なかわいさやVTuber色を出しすぎない
- MANAに接続できる高級感・落ち着きも意識する
- ただしLive2Dは現時点で未実装。実装済みのように書かないこと。

---

## 【開発ルール】
- 大きい変更はPlan Mode的に、調査 → 計画 → 実装 → 検証の順で行う。
- `frontend/streamlit_app.py` は影響範囲が大きいので変更前に必ず確認する。
- `agent/demo_scenarios.py` を壊さない。
- 既存4シナリオとPhase 3-B追加5シナリオを壊さない。
- GeminiなしFallbackを壊さない。
- 日本語表現QAを行う。
- 変更後はStreamlit起動確認を行う。
- AIVtuberApp / むぎちゃん / X自動リプライ関連ファイルには触らない。

---

## 【禁止事項】
- NAOMIを診断AIとして表現しない
- 医療判断を行わない
- Live2D実装済みのように書かない
- MANAとNAOMIを混同しない
- むぎちゃん関連ファイルを変更しない
- 不自然な日本語を放置しない
- 「ただのチャットAI」に寄せない
