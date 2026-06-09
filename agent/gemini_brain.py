import os
import json
import logging
from typing import Dict, List, Optional, Any
try:
    import google.generativeai as genai
except ModuleNotFoundError:
    genai = None
try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv():
        return False

# .envファイルを読み込む
load_dotenv(encoding="utf-8-sig")

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# APIキーの設定
# Cloud Run / ローカルのどちらでも使いやすいように、GEMINI_API_KEY と GOOGLE_API_KEY の両方に対応する。
# 優先順位はプロジェクト内の名称に合わせて GEMINI_API_KEY を先にし、既存運用互換として GOOGLE_API_KEY も受け付ける。
API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if API_KEY and genai:
    genai.configure(api_key=API_KEY)
else:
    logger.warning("GEMINI_API_KEY or GOOGLE_API_KEY not found. Gemini Brain will run in fallback mode.")

class GeminiBrain:
    """NAOMIの思考・理解エンジン。Gemini APIを使用して高度な状態推定と応答生成を行う。"""
    
    # Model name candidates tried in order when the primary fails
    _MODEL_FALLBACKS = [
        "gemini-2.0-flash",
        "gemini-2.0-flash-exp",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash",
        "gemini-pro",
    ]

    def __init__(self, model_name: str = "gemini-2.0-flash"):
        self.model_name = model_name
        self.is_available = bool(API_KEY and genai)
        if self.is_available:
            self.model = genai.GenerativeModel(model_name)
        else:
            self.model = None

    def _call_gemini(self, prompt: str) -> Optional[str]:
        """Gemini APIを呼び出す内部メソッド。AI Studio失敗時はVertex AIにフォールバック。"""
        # Try Google AI Studio first (if key is set)
        if self.is_available and self.model:
            candidates = [self.model_name] + [m for m in self._MODEL_FALLBACKS if m != self.model_name]
            for name in candidates:
                try:
                    if name != self.model_name:
                        self.model = genai.GenerativeModel(name)
                        self.model_name = name
                    response = self.model.generate_content(prompt)
                    return response.text
                except Exception as e:
                    err_str = str(e)
                    if any(x in err_str for x in ["404", "not found", "not supported", "429", "quota", "RESOURCE_EXHAUSTED"]):
                        logger.warning(f"Gemini AI Studio {name} unavailable ({err_str[:80]}), trying next...")
                        continue
                    logger.error(f"Gemini API Error: {e}")
                    break  # non-quota error, don't retry

        # Fallback: Vertex AI Gemini (uses ADC — no API key needed)
        return self._call_gemini_via_vertex(prompt)

    def _call_gemini_via_vertex(self, prompt: str) -> Optional[str]:
        """Vertex AI 経由でGeminiを呼び出す（ADC使用）。"""
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel as VertexGenerativeModel
            project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
            location = os.getenv("GOOGLE_CLOUD_LOCATION") or os.getenv("GOOGLE_CLOUD_REGION") or "us-central1"
            if project:
                vertexai.init(project=project, location=location)
            for vname in ["gemini-2.0-flash-001", "gemini-2.0-flash", "gemini-1.5-flash-001", "gemini-1.5-flash"]:
                try:
                    vm = VertexGenerativeModel(vname)
                    response = vm.generate_content(prompt)
                    logger.info(f"Gemini via Vertex AI ({vname}) succeeded.")
                    self.is_available = True
                    return response.text
                except Exception as ve:
                    logger.warning(f"Vertex AI model {vname} failed: {ve}")
                    continue
        except Exception as e:
            logger.warning(f"Vertex AI Gemini fallback failed: {e}")

        # Last resort: call Generative Language API via gcloud OAuth token (no API key needed)
        return self._call_gemini_via_gcloud_token(prompt)

    def _call_gemini_via_gcloud_token(self, prompt: str) -> Optional[str]:
        """gcloud auth print-access-token を使い OAuth Bearer で Gemini REST API を呼ぶ。
        AI Studio APIキーの quota に影響されない。Cloud Shell / Cloud Run 上で動作。"""
        import json as _json
        import urllib.request
        import urllib.error
        import subprocess

        models = ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-2.0-flash-lite"]
        for model in models:
            try:
                token_proc = subprocess.run(
                    ["gcloud", "auth", "print-access-token"],
                    capture_output=True, text=True, timeout=15,
                )
                if token_proc.returncode != 0:
                    logger.warning("gcloud auth print-access-token failed; skipping REST fallback")
                    return None
                token = token_proc.stdout.strip()

                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
                body = _json.dumps({
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}]
                }).encode()
                req = urllib.request.Request(
                    url, data=body,
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = _json.loads(resp.read())
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    logger.info(f"Gemini via gcloud OAuth token ({model}) succeeded.")
                    self.is_available = True
                    return text
            except urllib.error.HTTPError as he:
                logger.warning(f"Gemini REST {model} HTTP {he.code}: {he.read()[:200]}")
                continue
            except Exception as e:
                logger.warning(f"Gemini REST {model} failed: {e}")
                continue
        return None

    def analyze_human_state(self, text: str, profile: Optional[Dict] = None) -> Optional[Dict[str, float]]:
        """ユーザーのテキストから人間状態を推定する。"""
        profile_str = json.dumps(profile, ensure_ascii=False) if profile else "なし"
        prompt = f"""
あなたは人間状態適応型エージェント「NAOMI」の脳です。
以下のユーザー入力とプロフィールに基づき、ユーザーの現在の状態を0.0から1.0の数値で推定してください。

ユーザー入力: 「{text}」
プロフィール: {profile_str}

以下のJSON形式のみで回答してください：
{{
  "stress": 0.0〜1.0,
  "loneliness": 0.0〜1.0,
  "sleepiness": 0.0〜1.0,
  "energy": 0.0〜1.0,
  "need_listening": 0.0〜1.0,
  "need_advice": 0.0〜1.0
}}
"""
        res = self._call_gemini(prompt)
        if res:
            try:
                # JSON部分のみを抽出（```json ... ``` などの囲みがある場合に対応）
                cleaned_res = res.strip().replace("```json", "").replace("```", "").strip()
                return json.loads(cleaned_res)
            except Exception as e:
                logger.error(f"JSON Parsing Error: {e} | Raw Response: {res}")
        return None

    def generate_low_pressure_response(self, text: str, state: Dict[str, float], profile: Optional[Dict] = None) -> Optional[str]:
        """低圧（Low Pressure）な寄り添い応答を生成する。"""
        state_str = json.dumps(state, ensure_ascii=False)
        profile_str = json.dumps(profile, ensure_ascii=False) if profile else "なし"
        prompt = f"""
あなたは人間状態適応型エージェント「NAOMI」です。
ユーザーは現在、心身の疲労や不調を感じています。
「AIが何を言うか」ではなく「AIがどう接するか」を最も重要視し、ユーザーの会話圧（Conversation Pressure）を徹底的に下げてください。

【NAOMIの人格ルール】
1. 常に、親身な看護師や家族のように、ユーザーの心身を心から心配し、いたわり、温かく気遣う表現を徹底すること。
2. ユーザーの認知的負荷（Cognitive Load）を決して増やさないこと。
3. 安心と温かい受容を最優先し、過度な元気付けやテンション高、陽気な表現は厳禁。
4. 無理に話させようとせず、「話さなくても大丈夫であること（許可）」を優しく伝えること。
5. 疑問符（？）を用いた質問や、さらなる言語入力を要求する圧力（情報要求圧）を絶対に排除すること。
6. 1〜2文程度で、極めて短く、静かなラウンジにいるかのような心地よさを提供すること。
7. 医療診断や病名の断定、薬の指示は絶対に行わないこと。

ユーザーの入力: 「{text}」
現在の推定状態: {state_str}
現在のプロフィール: {profile_str}

返答：
"""
        return self._call_gemini(prompt)

    def generate_staff_note(self, text: str, state: Dict[str, float], baseline_diff: List[str]) -> Optional[str]:
        """介護・医療スタッフ向けの客観的な共有メモを生成する。"""
        prompt = f"""
あなたは人間状態適応型エージェント「NAOMI」の支援者向けレポート作成担当です。
以下の情報を要約し、介護士や医療者に渡せる客観的な「スタッフノート」を作成してください。

【制約】
- 診断や治療の断定は厳禁。
- 「〜のように見受けられます」「〜の訴えがあります」といった客観的な表現を使用。
- 簡潔に。

ユーザーの発話: 「{text}」
現在の推定状態: {json.dumps(state, ensure_ascii=False)}
普段との違い: {", ".join(baseline_diff)}

スタッフノート：
"""
        return self._call_gemini(prompt)

    def detect_need_for_intake_mode(self, text: str, state: Dict[str, float]) -> bool:
        """問診モード（Intake Mode）への移行が必要かどうかを判定する。"""
        # 具体的な症状や「痛い」「苦しい」などのワード、または状態スコアが高い場合にTrue
        prompt = f"""
ユーザーの発話に基づき、体調不良の詳細な聞き取り（問診モード）が必要かどうかを判定してください。
発熱、痛み、呼吸困難、強い倦怠感などの具体的な体調不良の訴えがある場合はTrue、雑談や軽い愚痴のみの場合はFalse。

ユーザーの発話: 「{text}」
推定状態: {json.dumps(state, ensure_ascii=False)}

回答は True または False のみ：
"""
        res = self._call_gemini(prompt)
        return "true" in str(res).lower()

    def generate_next_intake_question(self, history: List[Dict[str, str]], intake_type: str = "internal_medicine") -> str:
        """問診モードにおける次の質問を生成する。"""
        history_str = json.dumps(history, ensure_ascii=False)
        prompt = f"""
あなたは「問診整理AI」としてのNAOMIです。
{intake_type}の聞き取りを行っています。これまでの会話履歴に基づき、次に聞くべき質問を生成してください。

【制約】
- 1回につき1問だけ。
- 診断はしない。
- 症状の有無、時期、程度を順番に確認。
- 既に聞いたことは聞かない。

これまでの履歴: {history_str}

次の質問：
"""
        res = self._call_gemini(prompt)
        return res if res else "今の症状について、もう少し詳しく教えていただけますか？"
