import streamlit as st
import sys
import os
import importlib
from datetime import datetime
from dataclasses import asdict
from textwrap import dedent

# 繝励Ο繧ｸ繧ｧ繧ｯ繝医Ν繝ｼ繝医ｒPYTHONPATH縺ｫ霑ｽ蜉
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import agent.mode_selector as mode_selector_module
import agent.core as core_module
importlib.reload(mode_selector_module)
importlib.reload(core_module)
from agent.core import NaomiAgentCore
from agent.hackathon_integrations import process_with_hackathon_integrations
from agent.personal_baseline import load_profiles, get_profile, update_profile
from agent.proactive_care import generate_checkin_question

# 笏笏 荳闊ｬ逧・↑AI縺ｮ蝗ｺ螳夊ｿ皮ｭ費ｼ域ｯ碑ｼ・ョ繝｢逕ｨ・・笏笏
GENERIC_AI_RESPONSES = {
    "tired": "かなり疲れているようですね。休息のために、睡眠、軽い運動、明日のタスク整理をおすすめします。",
    "anxiety": "不安を感じているようですね。深呼吸をして、原因を書き出してみましょう。",
    "lonely": "孤独感があるなら、誰かに連絡したり、コミュニティに参加することが役立つかもしれません。",
    "exhausted_advice": "限界を感じているなら、まずタスクを整理して、不要なものを減らしましょう。",
    "overthinking_sleep": "眠れないときは、スマートフォンを置き、考えごとを紙に書き出しましょう。",
    "always_tense": "緊張が続いているなら、温かい飲み物や軽いストレッチを試してみましょう。",
    "decision_fatigue": "決断疲れには、重要な判断を午前中に回し、日常の選択を減らすことが有効です。",
    "cannot_rest": "休むことも大切な予定として、何もしない時間を確保しましょう。",
    "silent_loneliness": "理由のはっきりしない寂しさには、新しい習慣や人との接点が助けになる場合があります。",
    "default": "状況を分析し、優先順位を決め、次の行動を考えてみましょう。"
}

# 笏笏 Page Config 笏笏
st.set_page_config(
    page_title="NAOMI - 静かな場所",
    page_icon="🌙",
    layout="wide"
)

# 笏笏 Session State 笏笏
if "agent_core" not in st.session_state:
    st.session_state.agent_core = NaomiAgentCore()
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "proactive_question" not in st.session_state:
    st.session_state.proactive_question = None
if "current_user_id" not in st.session_state:
    st.session_state.current_user_id = "default"
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "light"
if "naomi_screen" not in st.session_state:
    st.session_state.naomi_screen = "start"
if "language" not in st.session_state:
    st.session_state.language = "JP"

query_screen = st.query_params.get("screen")
query_mode = st.query_params.get("mode")
query_lang = st.query_params.get("lang")

if query_screen == "home":
    if query_lang in ["JP", "EN"] and st.session_state.get("last_nav_key") != f"home:{query_lang}":
        st.session_state.language = query_lang
        st.session_state.last_nav_key = f"home:{query_lang}"
    st.session_state.naomi_screen = "home"
elif query_screen == "start":
    if query_lang in ["JP", "EN"] and st.session_state.get("last_nav_key") != f"start:{query_lang}":
        st.session_state.language = query_lang
        st.session_state.last_nav_key = f"start:{query_lang}"
        st.session_state.last_result = None
        st.session_state.proactive_question = None
    st.session_state.naomi_screen = "start"
elif query_screen == "state":
    nav_key = f"{query_screen}:{query_mode}:{st.session_state.get('language', 'JP')}"
    if query_lang in ["JP", "EN"]:
        nav_key = f"{query_screen}:{query_mode}:{query_lang}"
    if st.session_state.get("last_nav_key") != nav_key:
        if query_lang in ["JP", "EN"]:
            st.session_state.language = query_lang
        st.session_state.suppress_bottom_chat_once = True
        st.session_state.last_result = None
        st.session_state.proactive_question = None
        st.session_state.last_nav_key = nav_key
        mode_map = {
            "tired": "🌙 少し疲れている",
            "mental": "🧠 考えすぎている",
            "health": "🩺 今の健康状態を一緒に整理しましょう",
        }
        st.session_state.naomi_active_mode = mode_map.get(query_mode, "")
    st.session_state.naomi_screen = "state"
elif query_screen is None:
    if query_lang in ["JP", "EN"]:
        st.session_state.language = query_lang
    st.session_state.naomi_screen = "start"

# 笏笏 螟夊ｨ隱槭ユ繧ｭ繧ｹ繝郁ｾ樊嶌 (譛蟆剰恭隱槭Δ繝ｼ繝・ 笏笏
TEXT = {
    "JP": {
        "welcome_title": "おかえりなさい。<br>ここは、静かな場所です。",
        "welcome_subtitle": "疲れているときも、不安なときも、<br>そっと寄り添い、整理をお手伝いします。",
        "action_1_title": "今の状態を整理する",
        "action_1_sub": "体調や気持ちを<br>やさしく整理",
        "action_2_title": "話しかけ方の違いを試す",
        "action_2_sub": "NAOMIのやさしい対話を<br>体験",
        "action_3_title": "相談前メモを作る",
        "action_3_sub": "医療・介護・福祉の<br>相談に向けて",
        "home_note": "♡ 無理に話さなくても大丈夫です。あなたのペースで、ここに置いていけます。",
        "header_sub": "疲れているときも、不安なときも、そっと開ける静かな場所",
        "header_sub_large": "静かに、今を整える場所",
        "why_naomi_title": "🌿 この場所について",
        "why_naomi_subtitle": "疲れているときも、静かに使える場所",
        "why_naomi_desc": "答えを急がず、今の感じに合わせて言葉を少なくします。",
        "why_naomi_long": "うまく話せない日や、考える力が残っていない日でも大丈夫です。NAOMIは、あなたが選んだ状態に合わせて、言葉を少なく、静かに受け止めます。<br>※医療診断を行うものではありません。今の状態を伝えやすくするための静かな補助です。",
        "badge_1": "話さなくても大丈夫",
        "badge_2": "クリックだけでOK",
        "badge_3": "整理を急がない",
        "guide_title": "使い方",
        "guide_desc": "気になるカードを押すだけで大丈夫です。NAOMIが言葉の量や進み方を控えめにしながら、今の感じをそっと受け止めます。",
        "guide_step_title": "迷ったときの目安:",
        "guide_step_1": "疲れている時は、『少し疲れている』を選んでください。",
        "guide_step_2": "考えが止まらない時は、『不安』が近いかもしれません。",
        "guide_step_3": "体調や症状を伝えたい時は、『今の健康状態を一緒に整理しましょう』を選んでください。",
        "today_feel": "今日は、どんな感じですか？",
        "today_feel_sub": "無理に話さなくても大丈夫です。",
        "disclaimer_title": "安全に関する案内と免責事項",
        "disclaimer_text": "NAOMIは医療診断、治療指示、臨床判断を行うサービスではありません。<br>心身の状態を断定するものでもありません。<br>強い苦痛や緊急性がある場合は、身近な人、医療機関、または緊急窓口へ相談してください。",
        "card_1_title": "🌙 少し疲れている",
        "card_1_desc": "言葉にする余裕がない時も、<br>選ぶだけで始められます。",
        "card_2_title": "🧠 不安",
        "card_2_desc": "心の中がいっぱいな時、<br>急がず少しずつ整理します。",
        "card_3_title": "👂 聞こえ方",
        "card_3_desc": "音声なし・文字中心など、<br>受け取り方を楽にします。",
        "card_4_title": "🌿 整理したい",
        "card_4_desc": "体調や気持ちを、<br>相談前メモに整えます。",
        "btn_selected": "選択中",
        "btn_select": "ここを選ぶ"
    },
    "EN": {
        "welcome_title": "Welcome back.<br>This is a quiet place.",
        "welcome_subtitle": "Whether you are tired or anxious,<br>I will gently support and help organize your thoughts.",
        "action_1_title": "Organize Current State",
        "action_1_sub": "Gently organize<br>symptoms and feelings",
        "action_2_title": "Try Interactive Demo",
        "action_2_sub": "Experience NAOMI's<br>empathetic listening",
        "action_3_title": "Create Care Handoff Note",
        "action_3_sub": "Prepare simple notes<br>for consultations",
        "home_note": "♡ You do not have to explain everything. Leave your feelings here at your own pace.",
        "header_sub": "Whether tired or anxious, a quiet place you can open gently anytime",
        "header_sub_large": "Gently, a quiet place to organize today",
        "why_naomi_title": "🌿 About This Place",
        "why_naomi_subtitle": "A safe, quiet space when you are exhausted",
        "why_naomi_desc": "No rush for answers. Easing conversation pressure to fit your state.",
        "why_naomi_long": "It is okay if you cannot speak well today. NAOMI reduces response length and listens without forcing logic.<br>Not a medical diagnosis. A calm assistant to help communicate your current state.",
        "badge_1": "No talking required",
        "badge_2": "Click only is OK",
        "badge_3": "No logic forced",
        "guide_title": "How to Use",
        "guide_desc": "Just click any card that matches your feelings today. NAOMI will adapt its response length and listen gently.",
        "guide_step_title": "Quick guideline:",
        "guide_step_1": "If you are tired, try selecting 'Slightly tired' first.",
        "guide_step_2": "If your mind will not stop racing, 'Anxious & restless' may fit best.",
        "guide_step_3": "To share physical symptoms, choose 'Let's organize'.",
        "today_feel": "How are you feeling today?",
        "today_feel_sub": "You do not have to push yourself to speak.",
        "disclaimer_title": "Safety Guidelines & Medical Disclaimer",
        "disclaimer_text": "NAOMI does not provide medical diagnosis, treatment instructions, or clinical assessment.<br>If you are experiencing severe distress or a life-threatening emergency, please contact local emergency services immediately.",
        "card_1_title": "🌙 Slightly tired",
        "card_1_desc": "Start just by clicking,<br>even when words are hard to find.",
        "card_2_title": "🧠 Anxious & restless",
        "card_2_desc": "Gently organize thoughts<br>when your mind is overwhelmed.",
        "card_3_title": "👂 Accessibility",
        "card_3_desc": "Adjust font size and volume<br>for a stress-free experience.",
        "card_4_title": "🌿 Let's organize",
        "card_4_desc": "Prepare structured notes<br>for your next consultation.",
        "btn_selected": "Selected",
        "btn_select": "Select this"
    }
}
def t(key):
    lang = st.session_state.get("language", "JP")
    if key in TEXT[lang]:
        return TEXT[lang][key]
    if key in TEXT["JP"]:
        return TEXT["JP"][key]
    return key

def tr(en, jp):
    return en if st.session_state.get("language", "JP") == "EN" else jp

def home_greeting(hour=None, lang=None):
    hour = datetime.now().hour if hour is None else hour
    lang = st.session_state.get("language", "JP") if lang is None else lang
    if lang == "EN":
        if 5 <= hour < 11:
            return "Good morning. How are you feeling today?"
        if 11 <= hour < 16:
            return "Hello. Have you been able to take a short break?"
        if 16 <= hour < 19:
            return "Good evening. You have made it through another part of the day."
        if 19 <= hour < 24:
            return "Good evening. Thank you for getting through today."
        return "You are here late. Thank you for stopping by."
    if 5 <= hour < 11:
        return "おはようございます。今日の調子はいかがですか？"
    if 11 <= hour < 16:
        return "こんにちは。少し休憩は取れていますか？"
    if 16 <= hour < 19:
        return "夕方ですね。ここで少しだけ、息を置いていけます。"
    if 19 <= hour < 24:
        return "こんばんは。一日お疲れさまでした。"
    return "遅い時間までお疲れさまです。"

def active_profile():
    profile = dict(get_profile(st.session_state.current_user_id))
    profile["language"] = st.session_state.get("language", "JP")
    return profile

def naomi_process(text, profile=None, free_chat=False):
    with st.spinner("　ゆっくり、受け取っています…"):
        return process_with_hackathon_integrations(
            text,
            profile or active_profile(),
            st.session_state.agent_core,
            free_chat=free_chat,
        )

def hackathon_debug_payload(result):
    return getattr(result, "_hackathon_debug", {}) or {}

def show_hackathon_runtime_debug(result):
    payload = hackathon_debug_payload(result)
    if not payload:
        return
    status = payload.get("integration_status", {}) or {}
    with st.expander("Hackathon runtime integrations", expanded=False):
        st.write({
            "Gemini": status.get("gemini", "fallback"),
            "Agent Engine": status.get("agent_engine", "disabled"),
            "Arize MCP": status.get("arize_mcp", "disabled"),
            "Phoenix/OpenTelemetry": status.get("phoenix_otel", "disabled"),
            "Trace ID": status.get("trace_id") or payload.get("trace_id"),
        })
        if payload.get("arize_mcp_result"):
            st.write({"Arize MCP result": payload.get("arize_mcp_result")})

EN_RESPONSE_BY_SCENARIO = {
    "tired": "You've worked really hard today.\nYou don't have to organize anything right now. Let's just catch your breath here.",
    "anxiety": "Your mind is racing about tomorrow, making it hard to rest.\nYou don't have to find an answer right now. Let's look at what is bothering you most, step by step.",
    "lonely": "It feels lonely carrying all this alone, doesn't it?\nNo need to rush here. It is perfectly okay to leave your feelings exactly as they are.",
    "exhausted_advice": "You want to find a solution, but at the same time, you are running on empty.\nInstead of pushing immediate answers, let's gently untangle the situation together.",
    "overthinking_sleep": "On nights when thoughts will not stop, trying to sleep can feel even harder.\nYou do not have to solve anything right now. Let's start by placing just one thought beside you.",
    "always_tense": "Even after resting your body, your mind still feels on alert. That sounds painful.\nIf doing nothing feels scary, may I just help you slowly breathe out?",
    "decision_fatigue": "You have made so many decisions that your mind feels worn down.\nNo big decisions are needed today. Just tell me the smallest piece of how you feel now.",
    "cannot_rest": "You have kept running so long that resting itself feels wrong.\nFor now, it does not have to be 'resting'. Just pausing for a moment is enough. I am here.",
    "silent_loneliness": "The loneliness can feel heavier when there is no clear reason.\nYou do not have to put it into words. I just want you to know you are not alone.",
    "anxiety_insomnia": "You may be feeling very tense right now.\nYou do not have to force an answer. It may be okay to prioritize a little rest first.\nIf needed, I can help turn your current state into a note for someone else.",
    "state_support_memo": "You want to gently organize your current state so you can share it with someone.\nThis is not a medical judgment, but we can make a short note that helps communicate what is difficult.",
    "health_symptoms": "You want to organize your physical condition so it is easier to explain.\nEven listing symptoms, when they started, and their impact on daily life can make it easier to share with a consultant.",
}

COMMON_RESPONSE_EN = {}
GENERIC_AI_RESPONSES_EN = {
    "lonely": "When someone feels lonely, common advice is to join a community or contact friends. It is statistically shown that talking with someone may reduce loneliness.",
    "default": "Thank you for sharing. A typical solution-focused response might suggest analyzing the situation, prioritizing tasks, and taking immediate next steps.",
}

def display_response_text(text, scenario_id=None):
    if st.session_state.get("language", "JP") != "EN":
        return text
    if scenario_id in EN_RESPONSE_BY_SCENARIO:
        return EN_RESPONSE_BY_SCENARIO[scenario_id]
    return COMMON_RESPONSE_EN.get(text, text)

def display_note_text(text):
    return text

def phase_label(result):
    phase = (getattr(result, "asurada_state", {}) or {}).get("phase")
    if not phase:
        return None
    labels = {
        "LISTEN": "現在の応対: 傾聴中",
        "PROBE": "現在の応対: 確認中",
        "ORGANIZE": "現在の応対: 整理中",
        "ADVISE": "現在の応対: 提案中",
        "RED_FLAG": "現在の応対: 安全確認中",
    }
    return labels.get(phase, f"現在の応対: {phase}")

def reset_agent_session():
    if "agent_core" in st.session_state and hasattr(st.session_state.agent_core, "reset_session"):
        st.session_state.agent_core.reset_session()
    st.session_state.last_result = None
    st.session_state.proactive_question = None

def switch_mode(mode):
    reset_agent_session()
    st.session_state.naomi_active_mode = mode
    st.session_state.suppress_bottom_chat_once = True
    st.rerun()

def keep_menu_top_once():
    st.session_state.suppress_bottom_chat_once = True
    st.session_state.last_result = None
    st.session_state.proactive_question = None

def start_screen_link(extra_class=""):
    lang = st.session_state.get("language", "JP")
    label = "🏠 Start" if lang == "EN" else "🏠 はじめの画面へ"
    return f'<a class="naomi-return-start {extra_class}" href="?screen=start&lang={lang}" target="_self">{label}</a>'

def naomi_help_text(topic: str) -> str:
    lang = st.session_state.get("language", "JP")
    help_texts = {
        "pressure": {
            "JP": "会話圧を表します。NAOMIは急がせず、無理に結論を出さない接し方を大切にしています。Pressureが低いほど、落ち着いた接し方になります。",
            "EN": "Shows conversation pressure. Lower pressure means NAOMI responds more calmly, without rushing you toward an answer.",
        },
        "staff_note": {
            "JP": "今の状態を、人へ伝えやすく整理したメモです。診断ではありません。医師・看護師・介護士・支援者などへ状況を伝える補助として使えます。",
            "EN": "A shareable note about the current state. It is not a diagnosis. It can help explain the situation to clinicians, carers, or supporters.",
        },
        "human_state": {
            "JP": "会話から推定した現在の状態です。診断ではありません。NAOMIが接し方を決める参考として利用します。",
            "EN": "An estimated current state from the conversation. It is not a diagnosis; NAOMI uses it only to adjust how gently to respond.",
        },
        "mode": {
            "JP": "NAOMIが現在選んでいる接し方です。Listeningはまず受け止める段階、PROBEは少しだけ確認する段階、ORGANIZEはここまでを整理する段階、ADVISEは必要に応じて次の行動を案内する段階です。",
            "EN": "The response approach NAOMI is using. Listening receives first, PROBE asks only what is needed, ORGANIZE summarizes, and ADVISE gives next-step guidance when appropriate.",
        },
        "intake_summary": {
            "JP": "会話や入力内容を整理したメモです。あとで見返したり、人へ伝える補助として使えます。診断ではありません。",
            "EN": "A short organized note from the conversation. It can help you review or share the situation later. It is not a diagnosis.",
        },
        "red_flag": {
            "JP": "安全確認のサインです。強い負担や危険の可能性がある時に、安全を優先するための表示です。診断ではありません。",
            "EN": "A safety signal. It appears when NAOMI should prioritize safety because there may be strong distress or risk. It is not a diagnosis.",
        },
    }
    return help_texts.get(topic, {}).get(lang, help_texts.get(topic, {}).get("JP", ""))

def naomi_help(topic: str, label: str = "❓"):
    with st.popover(label, use_container_width=False):
        st.markdown(naomi_help_text(topic))

# --- 繧｢繧ｯ繧ｻ繧ｷ繝薙Μ繝・ぅ繧ｭ繝ｼ蜷梧悄 (Step 3: 驥崎､・屓驕ｿ & 逶ｸ莠貞酔譛・ ---
if "large_font" not in st.session_state:
    st.session_state.large_font = False
if "acc_large_font" not in st.session_state:
    st.session_state.acc_large_font = False

def sync_large_font_from_acc():
    st.session_state.large_font = st.session_state.acc_large_font

def sync_large_font_from_main():
    st.session_state.acc_large_font = st.session_state.large_font

for k in ["acc_button_only", "acc_short_response", "acc_no_audio", "acc_no_talk"]:
    if k not in st.session_state:
        st.session_state[k] = False

# 笏笏 繝・じ繧､繝ｳ繧ｷ繧ｹ繝・Β CSS 豕ｨ蜈･ (Step 1: Calm Light / Quiet Night) 笏笏
theme_mode = st.session_state.get("theme_mode", "light")
is_large = st.session_state.get("large_font", False)

# Google Fonts 繧､繝ｳ繝昴・繝・
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600&family=Noto+Serif+JP:wght@300;400;600&family=Inter:wght@300;400;500&display=swap');
.naomi-logo-link,
.naomi-logo-link:visited {
    color: inherit !important;
    text-decoration: none !important;
    cursor: pointer;
}
.naomi-logo-link:hover {
    opacity: 0.72;
}
.naomi-return-start,
.naomi-return-start:visited {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 38px;
    padding: 0.5rem 0.9rem;
    border-radius: 999px;
    border: 1px solid rgba(106, 140, 175, 0.18);
    background: rgba(255, 255, 255, 0.52);
    color: inherit !important;
    text-decoration: none !important;
    font-size: 0.92rem;
    font-weight: 400;
    box-shadow: 0 10px 28px rgba(106, 140, 175, 0.06);
}
.naomi-return-start:hover {
    opacity: 0.82;
    transform: translateY(-1px);
}
.naomi-return-row {
    max-width: 1060px;
    margin: 0.4rem auto 1rem auto;
}
</style>
""", unsafe_allow_html=True)

# 蜈ｱ騾壹ヵ繧ｩ繝ｳ繝医し繧､繧ｺ險ｭ螳・
base_font_size = "1.35rem" if is_large else "0.95rem"
h1_font_size = "2.8rem" if is_large else "1.9rem"
h2_font_size = "2.2rem" if is_large else "1.5rem"
h3_font_size = "1.8rem" if is_large else "1.25rem"
h4_font_size = "1.55rem" if is_large else "1.1rem"

if theme_mode == "light":
    # Calm Light Mode
    st.markdown(f"""
    <style>
    /* Streamlit繝・ヵ繧ｩ繝ｫ繝医・繝・ム繝ｼ繝ｻ繝輔ャ繧ｿ繝ｼ髱櫁｡ｨ遉ｺ (SaaS諢溘・螳悟・謗帝勁) */
    header[data-testid="stHeader"], footer {{
        visibility: hidden !important;
        height: 0px !important;
    }}
    
    /* 繧｢繝励Μ蜈ｨ菴楢レ譎ｯ & 繝輔か繝ｳ繝・*/
    .stApp, [data-testid="stAppViewContainer"] {{
        background: radial-gradient(circle at top, #fcfdfe 0%, #f5f8fc 50%, #ebeeec 100%) !important;
        color: #2c3e50 !important;
        font-family: 'Outfit', 'Inter', 'Noto Serif JP', sans-serif !important;
    }}
    .stApp p, .stApp span, .stApp label, .stApp li, .stApp div, .stApp .stMarkdown p {{
        font-size: {base_font_size} !important;
        color: #34495e !important;
        line-height: 1.8 !important;
    }}
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {{
        color: #2c3e50 !important;
        font-family: 'Noto Serif JP', 'Outfit', sans-serif !important;
        font-weight: 300 !important;
    }}
    .stApp h1 {{ font-size: {h1_font_size} !important; letter-spacing: -0.02em; }}
    .stApp h2 {{ font-size: {h2_font_size} !important; }}
    .stApp h3 {{ font-size: {h3_font_size} !important; }}
    .stApp h4 {{ font-size: {h4_font_size} !important; }}
    
    /* 繧ｳ繝ｳ繝・リ縺ｮ菴咏區隱ｿ謨ｴ・育ｸｦ髟ｷ縺ｮ髱吶°縺ｪ菴咏區遨ｺ髢難ｼ・*/
    .block-container {{
        padding-top: 2.0rem !important;
        padding-bottom: 5rem !important;
        max-width: 950px !important;
    }}
    
    /* 讓ｪ邱壹・髱櫁｡ｨ遉ｺ繝ｻ騾城℃蛹・*/
    hr {{
        border: none !important;
        height: 1px !important;
        background: linear-gradient(to right, transparent, rgba(106, 140, 175, 0.08), transparent) !important;
        margin: 2.5rem 0 !important;
    }}
    
    /* 繧ｬ繝ｩ繧ｹ繧ｫ繝ｼ繝芽ｪｿ (stAlert, widgets) - 繝懊・繝繝ｼ讌ｵ邏ｰ繝ｻ繧ｷ繝｣繝峨え雜・た繝輔ヨ蛹・*/
    div.stAlert, [data-testid="stExpander"] {{
        background-color: rgba(255, 255, 255, 0.6) !important;
        color: #2c3e50 !important;
        border: 1px solid rgba(255, 255, 255, 0.25) !important;
        border-radius: 24px !important;
        box-shadow: 0 15px 45px 0 rgba(31, 38, 135, 0.015) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        padding: 1.6rem !important;
        margin-bottom: 1.2rem !important;
    }}
    
    /* 繝懊ち繝ｳ縺ｮQuiet Luxury蛹・*/
    .stButton > button {{
        background-color: rgba(255, 255, 255, 0.5) !important;
        color: #2c3e50 !important;
        border: 1px solid rgba(106, 140, 175, 0.12) !important;
        border-radius: 24px !important;
        padding: 0.6rem 1.6rem !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.01) !important;
        backdrop-filter: blur(12px) !important;
        transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1) !important;
        font-family: 'Outfit', sans-serif !important;
        height: auto !important;
        font-size: {"1.5rem" if is_large else "0.92rem"} !important;
    }}
    .stButton > button:hover {{
        background-color: rgba(255, 255, 255, 0.95) !important;
        border-color: rgba(106, 140, 175, 0.4) !important;
        color: #6a8caf !important;
        box-shadow: 0 8px 25px rgba(106, 140, 175, 0.08) !important;
        transform: translateY(-1px);
    }}
    .stButton > button:active {{
        transform: translateY(0.5px) !important;
        box-shadow: 0 2px 8px rgba(106, 140, 175, 0.03) !important;
        background-color: rgba(106, 140, 175, 0.05) !important;
        transition: all 0.08s ease !important;
    }}
    .stButton > button:focus:not(:active) {{
        border-color: rgba(106, 140, 175, 0.5) !important;
        box-shadow: 0 0 0 3px rgba(106, 140, 175, 0.15) !important;
    }}
    div[data-testid="stForm"] button[kind="secondaryFormSubmit"],
    div[data-testid="stForm"] button[data-testid="baseButton-secondaryFormSubmit"] {{
        background-color: #EAF1F8 !important;
        color: #5E6F82 !important;
        border: 1px solid #D7E2EC !important;
        border-radius: 18px !important;
        font-weight: 500 !important;
        box-shadow: none !important;
    }}
    div[data-testid="stForm"] button[kind="secondaryFormSubmit"]:hover,
    div[data-testid="stForm"] button[data-testid="baseButton-secondaryFormSubmit"]:hover {{
        background-color: #DDEAF5 !important;
        color: #5E6F82 !important;
        border-color: #C7D7E6 !important;
        box-shadow: 0 6px 18px rgba(106, 140, 175, 0.08) !important;
        transform: translateY(-1px);
    }}
    div[data-testid="stForm"] div[data-baseweb="input"],
    div[data-testid="stForm"] .stTextInput input {{
        border-color: #D7E2EC !important;
        box-shadow: none !important;
    }}
    div[data-testid="stForm"] div[data-baseweb="input"]:focus-within,
    div[data-testid="stForm"] .stTextInput input:focus {{
        border-color: #BFD0E2 !important;
        box-shadow: 0 0 0 3px rgba(191, 208, 226, 0.24) !important;
        outline: none !important;
    }}
    /* 驕ｸ謚樊ｸ医∩ (primary) 繝懊ち繝ｳ縺ｮ荳願ｳｪ縺ｪQuiet Luxury蛹・(豐医・閭梧勹繝ｻ霈ｪ驛ｭ蠑ｷ隱ｿ繝ｻ霄ｫ菴捺─隕壹げ繝ｭ繝ｼ) */
    .stButton > button[kind="primary"], .stButton > button[data-testid="baseButton-primary"] {{
        background-color: rgba(106, 140, 175, 0.12) !important;
        color: #0f171e !important;
        border: 1px solid rgba(106, 140, 175, 0.6) !important;
        font-weight: 500 !important;
        box-shadow: 0 4px 15px rgba(106, 140, 175, 0.15) !important;
    }}
    .stButton > button[kind="primary"]:hover, .stButton > button[data-testid="baseButton-primary"]:hover {{
        background-color: rgba(106, 140, 175, 0.18) !important;
        border-color: rgba(106, 140, 175, 0.8) !important;
        color: #000000 !important;
    }}
    
    /* 蜈･蜉帙お繝ｪ繧｢ */
    .stChatInput textarea, .stTextArea textarea, .stTextInput input {{
        background-color: rgba(255, 255, 255, 0.75) !important;
        color: #2c3e50 !important;
        border: 1px solid rgba(106, 140, 175, 0.1) !important;
        border-radius: 20px !important;
        font-size: {"1.4rem" if is_large else "0.98rem"} !important;
    }}
    .stChatInput textarea::placeholder, .stTextArea textarea::placeholder, .stTextInput input::placeholder {{
        color: #8A8F98 !important;
        opacity: 1 !important;
    }}
    
    /* 繧ｿ繝悶・繧ｹ繧ｿ繧､繝ｪ繝ｳ繧ｰ・・aaS邂｡逅・判髱｢諢溘ｒ讌ｵ髯舌∪縺ｧ豸亥悉・・*/
    div[data-testid="stTabBar"] {{
        background: transparent !important;
        border: none !important;
        justify-content: center !important;
        margin-bottom: 2rem !important;
    }}
    button[data-baseweb="tab"] {{
        color: #8a9ba8 !important;
        background: transparent !important;
        border: none !important;
        font-size: 1.0rem !important;
        letter-spacing: 0.05em;
        padding: 0.8rem 2rem !important;
        border-bottom: 2px solid transparent !important;
        transition: all 0.4s ease !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: #6a8caf !important;
        border-bottom: 2px solid #6a8caf !important;
        font-weight: 500 !important;
    }}
    
    /* 髱吶°縺ｪ驕ｸ謚槭き繝ｼ繝峨・ Calm Light 繧ｹ繧ｿ繧､繝ｫ */
    div[class^="status-btn-"] + div div.stButton > button {{
        min-height: 140px !important;
        height: auto !important;
        border-radius: 26px !important;
        padding: 1.25rem 1.1rem !important;
        font-size: 1.08rem !important;
        font-weight: 300 !important;
        font-family: 'Noto Serif JP', sans-serif !important;
        border: 1px solid rgba(106, 140, 175, 0.07) !important;
        box-shadow: 0 18px 44px rgba(64, 86, 110, 0.035) !important;
        background: rgba(255, 255, 255, 0.38) !important;
        color: #2c3e50 !important;
        backdrop-filter: blur(22px) saturate(108%) !important;
        -webkit-backdrop-filter: blur(22px) saturate(108%) !important;
        transition: all 0.45s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }}
    div[class^="status-btn-"] + div div.stButton > button:hover {{
        background: rgba(255, 255, 255, 0.58) !important;
        border-color: rgba(106, 140, 175, 0.18) !important;
        color: #5f7f9e !important;
        box-shadow: 0 22px 52px rgba(106, 140, 175, 0.07) !important;
        transform: translateY(-1px);
    }}
    
    /* Selectbox (Theme Selector) 縺ｮSaaS諢滓賜髯､ */
    div[data-testid="stSelectbox"] > div {{
        background-color: transparent !important;
        border: none !important;
    }}
    div[data-testid="stSelectbox"] [data-baseweb="select"] {{
        background-color: rgba(255, 255, 255, 0.45) !important;
        border: 1px solid rgba(106, 140, 175, 0.1) !important;
        border-radius: 20px !important;
        box-shadow: 0 2px 10px rgba(0,0,0,0.01) !important;
    }}
    
    /* Accessibility Mode 繧ｳ繝ｳ繝・リ */
    div.accessibility-container {{
        background: rgba(255, 255, 255, 0.4) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: 24px !important;
        padding: 1.5rem !important;
        margin-top: 2rem !important;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.01) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
    }}
    
    /* 邨ｵ譁・ｭ励・蜊企城℃繝弱う繧ｺ菴取ｸ・*/
    .emoji-dim {{
        opacity: 0.6 !important;
        display: inline-block;
        margin-right: 0.2rem;
        transition: opacity 0.3s ease;
    }}
    .emoji-dim:hover {{
        opacity: 1.0 !important;
    }}
    
    /* 繧ｹ繝槭・蟷・〒縺ｮ菴咏區繝ｻ蟠ｩ繧碁亟豁｢繝ｬ繧ｹ繝昴Φ繧ｷ繝悶け繧ｨ繝ｪ (Night) */
    @media (max-width: 640px) {{
        .block-container {{
            padding-top: 1.0rem !important;
            padding-left: 0.7rem !important;
            padding-right: 0.7rem !important;
        }}
        div.stButton > button {{
            padding: 0.5rem 0.8rem !important;
            font-size: 0.85rem !important;
            white-space: normal !important;
        }}
        /* 繝｢繝舌う繝ｫ陦ｨ遉ｺ譎ゅ・譁・ｭ励し繧､繧ｺ縺ｨ菴咏區隱ｿ謨ｴ */
        .stApp h1 {{ font-size: 1.5rem !important; }}
        .stApp h2 {{ font-size: 1.3rem !important; }}
        .stApp h3 {{ font-size: 1.1rem !important; }}
    }}
    
    /* 繧ｹ繝槭・蟷・〒縺ｮ菴咏區繝ｻ蟠ｩ繧碁亟豁｢繝ｬ繧ｹ繝昴Φ繧ｷ繝悶け繧ｨ繝ｪ */
    @media (max-width: 640px) {{
        .block-container {{
            padding-top: 1.0rem !important;
            padding-left: 0.7rem !important;
            padding-right: 0.7rem !important;
        }}
        div.stButton > button {{
            padding: 0.5rem 0.8rem !important;
            font-size: 0.85rem !important;
            white-space: normal !important;
        }}
        /* 繝｢繝舌う繝ｫ陦ｨ遉ｺ譎ゅ・譁・ｭ励し繧､繧ｺ縺ｨ菴咏區隱ｿ謨ｴ */
        .stApp h1 {{ font-size: 1.5rem !important; }}
        .stApp h2 {{ font-size: 1.3rem !important; }}
        .stApp h3 {{ font-size: 1.1rem !important; }}
    }}

    /* 髱吶°縺ｪ蠕・ｩ滉ｸｭ繧｢繝九Γ繝ｼ繧ｷ繝ｧ繝ｳ螳夂ｾｩ */
    @keyframes slow-pulse {{
        0% {{ transform: scale(1); opacity: 0.25; }}
        50% {{ transform: scale(1.1); opacity: 0.6; }}
        100% {{ transform: scale(1); opacity: 0.25; }}
    }}
    .waiting-indicator {{
        display: inline-flex;
        align-items: center;
        gap: 10px;
        padding: 8px 18px;
        border-radius: 30px;
        background: rgba(255, 255, 255, 0.3) !important;
        border: 1px solid rgba(255, 255, 255, 0.25) !important;
        font-size: 0.85rem !important;
        color: #7f8c8d !important;
        font-family: 'Outfit', sans-serif;
        letter-spacing: 0.05em;
        backdrop-filter: blur(8px);
        box-shadow: 0 4px 15px rgba(0,0,0,0.005);
    }}
    .waiting-dot {{
        width: 8px;
        height: 8px;
        border-radius: 50%;
        animation: slow-pulse 3.5s infinite ease-in-out;
    }}
    </style>
    """, unsafe_allow_html=True)
else:
    # Quiet Night Mode
    st.markdown(f"""
    <style>
    /* Streamlit繝・ヵ繧ｩ繝ｫ繝医・繝・ム繝ｼ繝ｻ繝輔ャ繧ｿ繝ｼ髱櫁｡ｨ遉ｺ (SaaS諢溘・螳悟・謗帝勁) */
    header[data-testid="stHeader"], footer {{
        visibility: hidden !important;
        height: 0px !important;
    }}
    
    /* 繧｢繝励Μ蜈ｨ菴楢レ譎ｯ & 繝輔か繝ｳ繝・(豺ｱ螟懊・繝・ぅ繝ｼ繝励↑遨ｺ髢捺ｼ泌・) */
    .stApp, [data-testid="stAppViewContainer"] {{
        background: radial-gradient(circle at 30% 20%, #040810 0%, #020407 60%, #010204 100%) !important;
        color: #cbd5e1 !important;
        font-family: 'Outfit', 'Inter', 'Noto Serif JP', sans-serif !important;
    }}
    .stApp p, .stApp span, .stApp label, .stApp li, .stApp div, .stApp .stMarkdown p {{
        font-size: {base_font_size} !important;
        color: #8393a7 !important;
        line-height: 1.8 !important;
    }}
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {{
        color: #e2e8f0 !important;
        font-family: 'Noto Serif JP', 'Outfit', sans-serif !important;
        font-weight: 300 !important;
    }}
    .stApp h1 {{ font-size: {h1_font_size} !important; letter-spacing: -0.02em; }}
    .stApp h2 {{ font-size: {h2_font_size} !important; }}
    .stApp h3 {{ font-size: {h3_font_size} !important; }}
    .stApp h4 {{ font-size: {h4_font_size} !important; }}
    
    /* 繧ｳ繝ｳ繝・リ縺ｮ菴咏區隱ｿ謨ｴ・育ｸｦ髟ｷ縺ｮ髱吶°縺ｪ菴咏區遨ｺ髢難ｼ・*/
    .block-container {{
        padding-top: 2.0rem !important;
        padding-bottom: 5rem !important;
        max-width: 950px !important;
    }}
    
    /* 讓ｪ邱壹・髱櫁｡ｨ遉ｺ繝ｻ騾城℃蛹・*/
    hr {{
        border: none !important;
        height: 1px !important;
        background: linear-gradient(to right, transparent, rgba(197, 168, 128, 0.04), transparent) !important;
        margin: 2.5rem 0 !important;
    }}
    
    /* 繧ｬ繝ｩ繧ｹ繧ｫ繝ｼ繝芽ｪｿ (stAlert, widgets) - 繝懊・繝繝ｼ讌ｵ邏ｰ繝ｻ繧ｷ繝｣繝峨え雜・た繝輔ヨ蛹・*/
    div.stAlert, [data-testid="stExpander"] {{
        background-color: rgba(9, 14, 26, 0.35) !important;
        color: #cbd5e1 !important;
        border: 1px solid rgba(197, 168, 128, 0.05) !important;
        border-radius: 24px !important;
        box-shadow: 0 25px 60px 0 rgba(0, 0, 0, 0.3) !important;
        backdrop-filter: blur(24px) !important;
        -webkit-backdrop-filter: blur(24px) !important;
        padding: 1.6rem !important;
        margin-bottom: 1.2rem !important;
    }}
    
    /* 繝懊ち繝ｳ縺ｮQuiet Luxury蛹・(繧ｴ繝ｼ繝ｫ繝峨・繧｢繝ｳ繝舌・隱ｿ) */
    .stButton > button {{
        background-color: rgba(9, 14, 26, 0.5) !important;
        color: #94a3b8 !important;
        border: 1px solid rgba(197, 168, 128, 0.12) !important;
        border-radius: 24px !important;
        padding: 0.6rem 1.6rem !important;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15) !important;
        backdrop-filter: blur(12px) !important;
        transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1) !important;
        font-family: 'Outfit', sans-serif !important;
        height: auto !important;
        font-size: {"1.5rem" if is_large else "0.92rem"} !important;
    }}
    .stButton > button:hover {{
        background-color: rgba(17, 24, 39, 0.8) !important;
        border-color: rgba(197, 168, 128, 0.45) !important;
        color: #c5a880 !important;
        box-shadow: 0 6px 20px rgba(197, 168, 128, 0.08) !important;
        transform: translateY(-1px);
    }}
    .stButton > button:active {{
        transform: translateY(0.5px) !important;
        box-shadow: 0 2px 8px rgba(197, 168, 128, 0.03) !important;
        background-color: rgba(197, 168, 128, 0.05) !important;
        transition: all 0.08s ease !important;
    }}
    .stButton > button:focus:not(:active) {{
        border-color: rgba(197, 168, 128, 0.5) !important;
        box-shadow: 0 0 0 3px rgba(197, 168, 128, 0.15) !important;
    }}
    div[data-testid="stForm"] button[kind="secondaryFormSubmit"],
    div[data-testid="stForm"] button[data-testid="baseButton-secondaryFormSubmit"] {{
        background-color: #EAF1F8 !important;
        color: #5E6F82 !important;
        border: 1px solid #D7E2EC !important;
        border-radius: 18px !important;
        font-weight: 500 !important;
        box-shadow: none !important;
    }}
    div[data-testid="stForm"] button[kind="secondaryFormSubmit"]:hover,
    div[data-testid="stForm"] button[data-testid="baseButton-secondaryFormSubmit"]:hover {{
        background-color: #DDEAF5 !important;
        color: #5E6F82 !important;
        border-color: #C7D7E6 !important;
        box-shadow: 0 6px 18px rgba(106, 140, 175, 0.08) !important;
        transform: translateY(-1px);
    }}
    div[data-testid="stForm"] div[data-baseweb="input"],
    div[data-testid="stForm"] .stTextInput input {{
        border-color: #D7E2EC !important;
        box-shadow: none !important;
    }}
    div[data-testid="stForm"] div[data-baseweb="input"]:focus-within,
    div[data-testid="stForm"] .stTextInput input:focus {{
        border-color: #BFD0E2 !important;
        box-shadow: 0 0 0 3px rgba(191, 208, 226, 0.24) !important;
        outline: none !important;
    }}
    /* 驕ｸ謚樊ｸ医∩ (primary) 繝懊ち繝ｳ縺ｮ荳願ｳｪ縺ｪQuiet Luxury蛹・(豐医・閭梧勹繝ｻ霈ｪ驛ｭ蠑ｷ隱ｿ繝ｻ霄ｫ菴捺─隕壹げ繝ｭ繝ｼ) */
    .stButton > button[kind="primary"], .stButton > button[data-testid="baseButton-primary"] {{
        background-color: rgba(197, 168, 128, 0.08) !important;
        color: #e2e8f0 !important;
        border: 1px solid rgba(197, 168, 128, 0.6) !important;
        font-weight: 400 !important;
        box-shadow: 0 4px 20px rgba(197, 168, 128, 0.12) !important;
    }}
    .stButton > button[kind="primary"]:hover, .stButton > button[data-testid="baseButton-primary"]:hover {{
        background-color: rgba(197, 168, 128, 0.15) !important;
        border-color: rgba(197, 168, 128, 0.8) !important;
        color: #ffffff !important;
    }}
    
    /* 蜈･蜉帙お繝ｪ繧｢ */
    .stChatInput textarea, .stTextArea textarea, .stTextInput input {{
        background-color: rgba(9, 14, 26, 0.65) !important;
        color: #cbd5e1 !important;
        border: 1px solid rgba(197, 168, 128, 0.1) !important;
        border-radius: 20px !important;
        font-size: {"1.4rem" if is_large else "0.98rem"} !important;
    }}
    .stChatInput textarea::placeholder, .stTextArea textarea::placeholder, .stTextInput input::placeholder {{
        color: #9AA4B2 !important;
        opacity: 1 !important;
    }}
    
    /* 繧ｿ繝悶・繧ｹ繧ｿ繧､繝ｪ繝ｳ繧ｰ・・aaS邂｡逅・判髱｢諢溘ｒ讌ｵ髯舌∪縺ｧ豸亥悉・・*/
    div[data-testid="stTabBar"] {{
        background: transparent !important;
        border: none !important;
        justify-content: center !important;
        margin-bottom: 2rem !important;
    }}
    button[data-baseweb="tab"] {{
        color: #4b5563 !important;
        background: transparent !important;
        border: none !important;
        font-size: 1.0rem !important;
        letter-spacing: 0.05em;
        padding: 0.8rem 2rem !important;
        border-bottom: 2px solid transparent !important;
        transition: all 0.4s ease !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: #c5a880 !important;
        border-bottom: 2px solid #c5a880 !important;
        font-weight: 500 !important;
    }}
    
    /* 髱吶°縺ｪ驕ｸ謚槭き繝ｼ繝峨・ Quiet Night 繧ｹ繧ｿ繧､繝ｫ */
    div[class^="status-btn-"] + div div.stButton > button {{
        min-height: 140px !important;
        height: auto !important;
        border-radius: 26px !important;
        padding: 1.25rem 1.1rem !important;
        font-size: 1.08rem !important;
        font-weight: 300 !important;
        font-family: 'Noto Serif JP', sans-serif !important;
        border: 1px solid rgba(197, 168, 128, 0.055) !important;
        box-shadow: 0 20px 48px rgba(0, 0, 0, 0.18) !important;
        background: rgba(9, 14, 26, 0.32) !important;
        color: #96a4b5 !important;
        backdrop-filter: blur(22px) saturate(108%) !important;
        -webkit-backdrop-filter: blur(22px) saturate(108%) !important;
        transition: all 0.45s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }}
    div[class^="status-btn-"] + div div.stButton > button:hover {{
        background: rgba(17, 24, 39, 0.42) !important;
        border-color: rgba(197, 168, 128, 0.2) !important;
        color: #c5a880 !important;
        box-shadow: 0 22px 52px rgba(197, 168, 128, 0.08) !important;
        transform: translateY(-1px);
    }}
    
    /* Selectbox (Theme Selector) 縺ｮSaaS諢滓賜髯､ */
    div[data-testid="stSelectbox"] > div {{
        background-color: transparent !important;
        border: none !important;
    }}
    div[data-testid="stSelectbox"] [data-baseweb="select"] {{
        background-color: rgba(9, 14, 26, 0.5) !important;
        border: 1px solid rgba(197, 168, 128, 0.1) !important;
        border-radius: 20px !important;
        box-shadow: 0 4px 20px rgba(0,0,0,0.2) !important;
    }}
    
    /* Accessibility Mode 繧ｳ繝ｳ繝・リ */
    div.accessibility-container {{
        background: rgba(9, 14, 26, 0.35) !important;
        border: 1px solid rgba(197, 168, 128, 0.08) !important;
        border-radius: 24px !important;
        padding: 1.5rem !important;
        margin-top: 2rem !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.15) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
    }}
    
    /* 邨ｵ譁・ｭ励・蜊企城℃繝弱う繧ｺ菴取ｸ・*/
    .emoji-dim {{
        opacity: 0.5 !important;
        display: inline-block;
        margin-right: 0.2rem;
        transition: opacity 0.3s ease;
    }}
    .emoji-dim:hover {{
        opacity: 0.9 !important;
    }}

    /* 髱吶°縺ｪ蠕・ｩ滉ｸｭ繧｢繝九Γ繝ｼ繧ｷ繝ｧ繝ｳ螳夂ｾｩ */
    @keyframes slow-pulse-night {{
        0% {{ transform: scale(1); opacity: 0.15; }}
        50% {{ transform: scale(1.1); opacity: 0.5; }}
        100% {{ transform: scale(1); opacity: 0.15; }}
    }}
    .waiting-indicator {{
        display: inline-flex;
        align-items: center;
        gap: 10px;
        padding: 8px 18px;
        border-radius: 30px;
        background: rgba(9, 14, 26, 0.35) !important;
        border: 1px solid rgba(197, 168, 128, 0.06) !important;
        font-size: 0.85rem !important;
        color: #8393a7 !important;
        font-family: 'Outfit', sans-serif;
        letter-spacing: 0.05em;
        backdrop-filter: blur(8px);
        box-shadow: 0 10px 30px rgba(0,0,0,0.15);
    }}
    .waiting-dot {{
        width: 8px;
        height: 8px;
        border-radius: 50%;
        animation: slow-pulse-night 3.5s infinite ease-in-out;
    }}
    </style>
    """, unsafe_allow_html=True)

# 笏笏 繝｢繝舌う繝ｫ譎ゅ・蛻晁ｦ句ｰ守ｷ壹ｒ蟆代＠縺縺大燕縺ｫ蜃ｺ縺吝・騾夊ｪｿ謨ｴ 笏笏
st.markdown("""
<style>
@media (max-width: 640px) {
    .block-container {
        padding-top: 0.55rem !important;
    }
    [data-testid="stExpander"] {
        padding: 0.85rem 1.0rem !important;
        margin-bottom: 0.45rem !important;
    }
    .intro-prompt {
        padding: 1.0rem 0 0.65rem 0 !important;
    }
    .intro-prompt h3 {
        margin-bottom: 0.25rem !important;
        line-height: 1.38 !important;
    }
    .intro-prompt p {
        margin-top: 0.35rem !important;
        line-height: 1.55 !important;
    }
    .mode-card-spacer {
        margin-top: 0.65rem !important;
        margin-bottom: 0.35rem !important;
    }
    .mode-card {
        min-height: 108px !important;
        padding: 1.05rem 0.95rem !important;
    }
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.st-key-mode_btn_1 button,
.st-key-mode_btn_2 button,
.st-key-mode_btn_3 button,
.st-key-mode_btn_4 button {
    background: #eef6ff !important;
    border: 1px solid #d7e6f5 !important;
    color: #52677f !important;
    box-shadow: none !important;
    border-radius: 18px !important;
    font-weight: 500 !important;
}
.st-key-mode_btn_1 button:hover,
.st-key-mode_btn_2 button:hover,
.st-key-mode_btn_3 button:hover,
.st-key-mode_btn_4 button:hover,
.st-key-mode_btn_1 button:focus:not(:active),
.st-key-mode_btn_2 button:focus:not(:active),
.st-key-mode_btn_3 button:focus:not(:active),
.st-key-mode_btn_4 button:focus:not(:active) {
    background: #e4f1ff !important;
    border-color: #bdd7ef !important;
    color: #52677f !important;
    box-shadow: 0 6px 18px rgba(120, 170, 210, 0.12) !important;
}
.st-key-mode_btn_1 button[kind="primary"],
.st-key-mode_btn_2 button[kind="primary"],
.st-key-mode_btn_3 button[kind="primary"],
.st-key-mode_btn_4 button[kind="primary"],
.st-key-mode_btn_1 button[data-testid="baseButton-primary"],
.st-key-mode_btn_2 button[data-testid="baseButton-primary"],
.st-key-mode_btn_3 button[data-testid="baseButton-primary"],
.st-key-mode_btn_4 button[data-testid="baseButton-primary"] {
    background: linear-gradient(180deg, #e8f4ff 0%, #dcefff 100%) !important;
    border: 1px solid #9fc8ed !important;
    color: #315f86 !important;
    box-shadow: 0 8px 20px rgba(120, 170, 210, 0.18) !important;
}
.st-key-mode_btn_1 button[kind="primary"]:hover,
.st-key-mode_btn_2 button[kind="primary"]:hover,
.st-key-mode_btn_3 button[kind="primary"]:hover,
.st-key-mode_btn_4 button[kind="primary"]:hover,
.st-key-mode_btn_1 button[data-testid="baseButton-primary"]:hover,
.st-key-mode_btn_2 button[data-testid="baseButton-primary"]:hover,
.st-key-mode_btn_3 button[data-testid="baseButton-primary"]:hover,
.st-key-mode_btn_4 button[data-testid="baseButton-primary"]:hover {
    background: linear-gradient(180deg, #e8f4ff 0%, #dcefff 100%) !important;
    border-color: #8dbde6 !important;
    color: #315f86 !important;
    box-shadow: 0 10px 24px rgba(120, 170, 210, 0.20) !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
div[data-testid="stPopover"] > button {
    width: 46px !important;
    height: 46px !important;
    min-width: 46px !important;
    padding: 0 !important;
    border-radius: 999px !important;
    border: 1px solid rgba(255, 255, 255, 0.72) !important;
    background: linear-gradient(135deg, rgba(255,255,255,0.82), rgba(255,255,255,0.34)) !important;
    color: #6a8caf !important;
    box-shadow: 0 14px 34px rgba(106, 140, 175, 0.12), inset 0 1px 0 rgba(255,255,255,0.88) !important;
    backdrop-filter: blur(22px) saturate(145%) !important;
    -webkit-backdrop-filter: blur(22px) saturate(145%) !important;
    font-size: 1.18rem !important;
    line-height: 1 !important;
}
div[data-testid="stPopover"] button,
div[data-testid="stPopover"] button[data-testid^="baseButton"] {
    width: 46px !important;
    height: 46px !important;
    min-width: 46px !important;
    padding: 0 !important;
    border-radius: 999px !important;
    border: 1px solid rgba(255, 255, 255, 0.72) !important;
    background: linear-gradient(135deg, rgba(255,255,255,0.82), rgba(255,255,255,0.34)) !important;
    color: #6a8caf !important;
    box-shadow: 0 14px 34px rgba(106, 140, 175, 0.12), inset 0 1px 0 rgba(255,255,255,0.88) !important;
    backdrop-filter: blur(22px) saturate(145%) !important;
    -webkit-backdrop-filter: blur(22px) saturate(145%) !important;
}
div[data-testid="stPopover"] > button:hover {
    background: linear-gradient(135deg, rgba(255,255,255,0.96), rgba(255,255,255,0.56)) !important;
    border-color: rgba(255, 255, 255, 0.95) !important;
    color: #2c3e50 !important;
    box-shadow: 0 18px 42px rgba(106, 140, 175, 0.18), inset 0 1px 0 rgba(255,255,255,0.95) !important;
    transform: translateY(-1px);
}
div[data-testid="stPopover"] > button p,
div[data-testid="stPopover"] > button span {
    color: inherit !important;
}
div[data-testid="stSelectbox"] [data-baseweb="select"] {
    background: linear-gradient(135deg, rgba(255,255,255,0.78), rgba(255,255,255,0.32)) !important;
    border: 1px solid rgba(255, 255, 255, 0.72) !important;
    border-radius: 18px !important;
    box-shadow: 0 12px 30px rgba(106, 140, 175, 0.10), inset 0 1px 0 rgba(255,255,255,0.82) !important;
    backdrop-filter: blur(18px) saturate(140%) !important;
    -webkit-backdrop-filter: blur(18px) saturate(140%) !important;
}
div[data-testid="stSelectbox"] div[data-baseweb="select"],
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
div[data-testid="stSelectbox"] [role="combobox"] {
    background: linear-gradient(135deg, rgba(255,255,255,0.78), rgba(255,255,255,0.32)) !important;
    border-color: rgba(255, 255, 255, 0.72) !important;
    color: #34495e !important;
    box-shadow: 0 12px 30px rgba(106, 140, 175, 0.10), inset 0 1px 0 rgba(255,255,255,0.82) !important;
    backdrop-filter: blur(18px) saturate(140%) !important;
    -webkit-backdrop-filter: blur(18px) saturate(140%) !important;
}
div[data-testid="stSelectbox"] [data-baseweb="select"] * {
    color: #34495e !important;
}
div[data-testid="stSelectbox"] svg {
    color: #6a8caf !important;
    fill: #6a8caf !important;
}
div[data-baseweb="popover"] div[role="listbox"],
div[data-baseweb="popover"] ul,
div[data-baseweb="popover"] [role="option"] {
    background: rgba(255, 255, 255, 0.88) !important;
    color: #34495e !important;
    border-color: rgba(255, 255, 255, 0.72) !important;
    backdrop-filter: blur(24px) saturate(145%) !important;
    -webkit-backdrop-filter: blur(24px) saturate(145%) !important;
}
div[data-baseweb="popover"] {
    filter: drop-shadow(0 18px 42px rgba(106, 140, 175, 0.18)) !important;
}
div[data-baseweb="popover"] [role="option"]:hover,
div[data-baseweb="popover"] [aria-selected="true"] {
    background: rgba(106, 140, 175, 0.12) !important;
    color: #2c3e50 !important;
}
div[data-baseweb="popover"] [role="option"] * {
    color: inherit !important;
}
.naomi-status-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    margin-left: 1.1rem;
    padding: 0.24rem 0.78rem;
    border-radius: 999px;
    border: 1px solid rgba(106, 140, 175, 0.16);
    background: rgba(255, 255, 255, 0.58);
    box-shadow: 0 10px 28px rgba(106, 140, 175, 0.06);
    color: #6f8397;
    font-size: 0.78rem;
    letter-spacing: 0.04em;
    backdrop-filter: blur(18px) saturate(135%);
    -webkit-backdrop-filter: blur(18px) saturate(135%);
}
.naomi-status-dot {
    width: 0.52rem;
    height: 0.52rem;
    border-radius: 999px;
    background: #8aa6bf;
    box-shadow: 0 0 0 5px rgba(138, 166, 191, 0.12);
}
.naomi-home-shell {
    position: relative;
    overflow: hidden;
    min-height: 0;
    margin-top: 1.5rem;
    padding: clamp(1.6rem, 4vw, 3.4rem);
    border-radius: 34px;
    border: 1px solid rgba(255, 255, 255, 0.72);
    background:
        linear-gradient(100deg, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.78) 48%, rgba(242,247,252,0.62) 100%);
    box-shadow: 0 28px 80px rgba(106, 140, 175, 0.10), inset 0 1px 0 rgba(255,255,255,0.92);
    backdrop-filter: blur(24px) saturate(135%);
    -webkit-backdrop-filter: blur(24px) saturate(135%);
}
.naomi-home-shell::before {
    content: "";
    position: absolute;
    inset: 0;
    background:
        linear-gradient(100deg, transparent 62%, rgba(154, 174, 194, 0.16) 63%, transparent 64%),
        linear-gradient(0deg, transparent 32%, rgba(154, 174, 194, 0.10) 33%, transparent 34%);
    opacity: 0.45;
    pointer-events: none;
}
.naomi-home-still-life {
    position: absolute;
    right: clamp(1.2rem, 5vw, 4.2rem);
    top: clamp(7.5rem, 16vw, 12rem);
    width: min(24vw, 230px);
    min-width: 150px;
    height: 260px;
    opacity: 0.76;
    pointer-events: none;
}
.naomi-home-vase {
    position: absolute;
    right: 22px;
    bottom: 26px;
    width: 68px;
    height: 108px;
    border-radius: 34px 34px 18px 18px;
    background: linear-gradient(135deg, rgba(255,255,255,0.98), rgba(226,232,238,0.62));
    border: 1px solid rgba(183, 196, 207, 0.35);
    box-shadow: 0 18px 34px rgba(106, 140, 175, 0.10);
}
.naomi-home-branch {
    position: absolute;
    right: 55px;
    bottom: 118px;
    width: 1px;
    height: 130px;
    background: rgba(126, 152, 122, 0.55);
    transform: rotate(-18deg);
    transform-origin: bottom;
}
.naomi-home-branch::before,
.naomi-home-branch::after {
    content: "";
    position: absolute;
    width: 42px;
    height: 18px;
    border-radius: 50%;
    background: rgba(141, 164, 126, 0.34);
}
.naomi-home-branch::before {
    left: -40px;
    top: 22px;
    transform: rotate(28deg);
}
.naomi-home-branch::after {
    right: -38px;
    top: 62px;
    transform: rotate(-22deg);
}
.naomi-home-mug {
    position: absolute;
    right: 112px;
    bottom: 28px;
    width: 76px;
    height: 64px;
    border-radius: 0 0 24px 24px;
    background: linear-gradient(135deg, rgba(255,255,255,0.96), rgba(232,226,218,0.70));
    border: 1px solid rgba(184, 172, 158, 0.28);
    box-shadow: 0 18px 34px rgba(106, 140, 175, 0.08);
}
.naomi-home-mug::after {
    content: "";
    position: absolute;
    right: -20px;
    top: 15px;
    width: 28px;
    height: 30px;
    border: 7px solid rgba(232,226,218,0.78);
    border-left: 0;
    border-radius: 0 18px 18px 0;
}
.naomi-home-copy {
    position: relative;
    z-index: 1;
    max-width: 680px;
    margin: 1.8rem auto 0;
    text-align: center;
}
.naomi-home-symbol {
    width: 76px;
    height: 76px;
    margin: 0 auto 1.4rem;
    display: grid;
    place-items: center;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.62);
    border: 1px solid rgba(255,255,255,0.82);
    box-shadow: 0 16px 44px rgba(106, 140, 175, 0.10);
    color: #d9a94f;
    font-size: 2.2rem;
}
.naomi-home-title {
    font-family: 'Noto Serif JP', serif;
    color: #2f4964;
    font-size: clamp(2.1rem, 5vw, 3.25rem);
    line-height: 1.55;
    letter-spacing: 0.08em;
    font-weight: 300;
    margin: 0 0 1.3rem;
}
.naomi-home-sub {
    color: #6d8092;
    line-height: 2;
    font-size: 1.05rem;
    letter-spacing: 0.04em;
    margin-bottom: 2rem;
}
.naomi-home-actions {
    position: relative;
    z-index: 1;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 1.5rem;
    max-width: 980px;
    margin: 0 auto;
}
.naomi-home-action-card,
.naomi-home-action-card:visited {
    display: block;
    min-height: 124px;
    padding: 1.25rem 1.2rem;
    border-radius: 28px;
    border: 1px solid rgba(255, 255, 255, 0.74);
    background: rgba(255, 255, 255, 0.50);
    box-shadow: 0 20px 48px rgba(106, 140, 175, 0.08), inset 0 1px 0 rgba(255,255,255,0.82);
    text-align: center;
    backdrop-filter: blur(20px) saturate(135%);
    -webkit-backdrop-filter: blur(20px) saturate(135%);
    text-decoration: none !important;
    transition: transform 0.18s ease, background 0.18s ease, border-color 0.18s ease;
}
.naomi-home-action-card:hover {
    transform: translateY(-2px);
    border-color: rgba(106, 140, 175, 0.24);
    background: rgba(255, 255, 255, 0.62);
}
.naomi-home-action-icon {
    width: 58px;
    height: 58px;
    margin: 0 auto 0.75rem;
    display: grid;
    place-items: center;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.62);
    color: #6a8caf;
    font-size: 1.7rem;
}
.naomi-home-action-title {
    color: #2f4964;
    font-family: 'Noto Serif JP', serif;
    font-size: 1.05rem;
    letter-spacing: 0.05em;
    margin-bottom: 0.35rem;
}
.naomi-home-action-sub {
    color: #7d8fa0;
    font-size: 0.82rem;
    line-height: 1.65;
}
.naomi-home-note {
    position: relative;
    z-index: 1;
    width: fit-content;
    max-width: 100%;
    margin: 2.4rem auto 0;
    padding: 0.75rem 1.6rem;
    border-radius: 999px;
    background: rgba(236, 242, 248, 0.72);
    color: #5d7893;
    font-size: 0.9rem;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.68);
}
.naomi-home-chat-message {
    position: relative;
    z-index: 1;
}
.naomi-home-chat-form-anchor {
    max-width: 860px;
    margin: 0 auto;
}
.naomi-home-chat-form-anchor + div [data-testid="stForm"] {
    max-width: 860px;
    margin: 0 auto 1.6rem auto;
    border: 1px solid rgba(106, 140, 175, 0.13);
    border-radius: 22px;
    background: rgba(255, 255, 255, 0.30);
    box-shadow: 0 12px 34px rgba(106, 140, 175, 0.035);
}
.naomi-home-chat-form-anchor + div [data-testid="stForm"] input {
    border-radius: 999px !important;
}
.naomi-home-chat-form-anchor + div [data-testid="stForm"] div[data-baseweb="input"],
.naomi-home-chat-form-anchor + div [data-testid="stForm"] div[data-baseweb="input"] > div,
.naomi-start-form-anchor + div [data-testid="stForm"] div[data-baseweb="input"],
.naomi-start-form-anchor + div [data-testid="stForm"] div[data-baseweb="input"] > div,
.naomi-state-chat-form-anchor + div [data-testid="stForm"] div[data-baseweb="input"],
.naomi-state-chat-form-anchor + div [data-testid="stForm"] div[data-baseweb="input"] > div {
    background: rgba(255, 255, 255, 0.88) !important;
    border-color: rgba(106, 140, 175, 0.16) !important;
    border-radius: 999px !important;
    box-shadow: none !important;
}
.naomi-home-chat-form-anchor + div [data-testid="stForm"] div[data-baseweb="input"]:focus-within,
.naomi-start-form-anchor + div [data-testid="stForm"] div[data-baseweb="input"]:focus-within,
.naomi-state-chat-form-anchor + div [data-testid="stForm"] div[data-baseweb="input"]:focus-within {
    border-color: rgba(106, 140, 175, 0.28) !important;
    box-shadow: 0 0 0 3px rgba(106, 140, 175, 0.08), 0 10px 28px rgba(106, 140, 175, 0.045) !important;
}
.naomi-home-chat-form-anchor + div [data-testid="stForm"] input,
.naomi-start-form-anchor + div [data-testid="stForm"] input {
    background: rgba(255, 255, 255, 0.86) !important;
    border: 1px solid rgba(106, 140, 175, 0.16) !important;
    color: #33485d !important;
    box-shadow: 0 10px 28px rgba(106, 140, 175, 0.045), inset 0 1px 0 rgba(255,255,255,0.92) !important;
}
.naomi-home-chat-form-anchor + div [data-testid="stForm"] input:focus,
.naomi-start-form-anchor + div [data-testid="stForm"] input:focus {
    border-color: rgba(106, 140, 175, 0.28) !important;
    box-shadow: 0 0 0 3px rgba(106, 140, 175, 0.08), 0 10px 28px rgba(106, 140, 175, 0.045) !important;
    outline: none !important;
}
.naomi-home-chat-form-anchor + div [data-testid="stForm"] input::placeholder,
.naomi-start-form-anchor + div [data-testid="stForm"] input::placeholder {
    color: rgba(72, 91, 112, 0.48) !important;
    opacity: 1 !important;
}
.naomi-home-chat-form-anchor + div [data-testid="stForm"] [data-testid="stFormSubmitButton"],
.naomi-state-chat-form-anchor + div [data-testid="stForm"] [data-testid="stFormSubmitButton"] {
    display: flex !important;
    justify-content: center !important;
}
.naomi-home-chat-form-anchor + div [data-testid="stForm"] [data-testid="stFormSubmitButton"] > button,
.naomi-state-chat-form-anchor + div [data-testid="stForm"] [data-testid="stFormSubmitButton"] > button {
    margin-left: auto !important;
    margin-right: auto !important;
}
.naomi-state-chat-form-anchor {
    max-width: 860px;
    margin: 0 auto;
}
.naomi-state-chat-form-anchor + div [data-testid="stForm"] input {
    border-radius: 999px !important;
    background: rgba(255, 255, 255, 0.86) !important;
    border: 1px solid rgba(106, 140, 175, 0.16) !important;
    color: #33485d !important;
}
.naomi-state-chat-form-anchor + div [data-testid="stForm"] input:focus {
    border-color: rgba(106, 140, 175, 0.28) !important;
    box-shadow: 0 0 0 3px rgba(106, 140, 175, 0.08) !important;
    outline: none !important;
}
.naomi-state-chat-form-anchor + div [data-testid="stForm"] input::placeholder {
    color: rgba(72, 91, 112, 0.48) !important;
    opacity: 1 !important;
}
.naomi-home-actions-buttons [data-testid="column"] {
    padding: 0 0.45rem;
}
.naomi-home-actions-buttons .stButton > button {
    min-height: 52px !important;
    border-radius: 999px !important;
    margin-top: 0.7rem !important;
}
.naomi-home-link-button,
.naomi-home-link-button:visited {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 52px;
    width: 100%;
    margin-top: 0.7rem;
    border-radius: 999px;
    border: 1px solid rgba(106, 140, 175, 0.16);
    background: rgba(255, 255, 255, 0.42);
    color: #3f5870 !important;
    text-decoration: none !important;
    font-weight: 500;
    box-shadow: 0 8px 24px rgba(31, 38, 55, 0.025);
}
.naomi-home-link-button:hover {
    border-color: rgba(106, 140, 175, 0.35);
    background: rgba(255, 255, 255, 0.66);
}
.naomi-start-shell {
    position: relative;
    overflow: hidden;
    max-width: 860px;
    min-height: 360px;
    margin: 2.2rem auto 0;
    padding: 3.4rem 1.8rem 2.2rem;
    text-align: center;
    border-radius: 34px;
    background:
        linear-gradient(135deg, rgba(255,255,255,0.74), rgba(246,249,252,0.34)),
        radial-gradient(circle at 50% 0%, rgba(255, 255, 255, 0.92), rgba(255, 255, 255, 0.30) 52%, rgba(255, 255, 255, 0.16) 100%);
    border: 1px solid rgba(255, 255, 255, 0.62);
    box-shadow: 0 32px 96px rgba(106, 140, 175, 0.13), inset 0 1px 0 rgba(255,255,255,0.74);
    backdrop-filter: blur(24px) saturate(145%);
    -webkit-backdrop-filter: blur(24px) saturate(145%);
}
.naomi-start-shell::before {
    content: "";
    position: absolute;
    inset: 0;
    background:
        radial-gradient(circle at 30% 18%, rgba(255,255,255,0.74), transparent 24%),
        radial-gradient(circle at 76% 28%, rgba(219, 231, 241, 0.38), transparent 30%),
        linear-gradient(90deg, transparent 0%, rgba(106, 140, 175, 0.045) 50%, transparent 100%);
    pointer-events: none;
}
.naomi-start-shell::after {
    content: "";
    position: absolute;
    left: 10%;
    right: 10%;
    bottom: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(106, 140, 175, 0.16), transparent);
}
.naomi-start-copy {
    position: relative;
    z-index: 1;
    max-width: 560px;
    margin: 0 auto;
}
.naomi-start-still-life {
    position: absolute;
    right: 70px;
    bottom: 46px;
    width: 160px;
    height: 190px;
    opacity: 0.54;
    pointer-events: none;
}
.naomi-start-vase {
    position: absolute;
    right: 18px;
    bottom: 0;
    width: 58px;
    height: 112px;
    border-radius: 28px 28px 18px 18px;
    background: linear-gradient(150deg, rgba(255,255,255,0.82), rgba(223,229,232,0.46));
    border: 1px solid rgba(106, 140, 175, 0.13);
    box-shadow: 0 18px 34px rgba(106, 140, 175, 0.07);
}
.naomi-start-branch {
    position: absolute;
    right: 54px;
    bottom: 72px;
    width: 1px;
    height: 118px;
    background: rgba(126, 152, 122, 0.46);
    transform: rotate(-18deg);
    transform-origin: bottom;
}
.naomi-start-branch::before,
.naomi-start-branch::after {
    content: "";
    position: absolute;
    width: 36px;
    height: 15px;
    border-radius: 50%;
    background: rgba(141, 164, 126, 0.28);
}
.naomi-start-branch::before {
    left: -34px;
    top: 26px;
    transform: rotate(28deg);
}
.naomi-start-branch::after {
    right: -32px;
    top: 58px;
    transform: rotate(-22deg);
}
.naomi-start-mug {
    position: absolute;
    right: 70px;
    bottom: 4px;
    width: 58px;
    height: 48px;
    border-radius: 0 0 20px 20px;
    background: linear-gradient(135deg, rgba(255,255,255,0.90), rgba(232,226,218,0.58));
    border: 1px solid rgba(184, 172, 158, 0.22);
}
.naomi-start-mug::after {
    content: "";
    position: absolute;
    right: -16px;
    top: 11px;
    width: 22px;
    height: 24px;
    border: 5px solid rgba(232,226,218,0.60);
    border-left: 0;
    border-radius: 0 15px 15px 0;
}
.naomi-start-symbol {
    width: 64px;
    height: 64px;
    margin: 0 auto 1.4rem;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.66);
    border: 1px solid rgba(255,255,255,0.78);
    box-shadow: 0 18px 52px rgba(106, 140, 175, 0.12), inset 0 1px 0 rgba(255,255,255,0.92);
    color: #d9a94f;
    font-size: 1.7rem;
}
.naomi-start-greeting {
    font-family: 'Noto Serif JP', serif;
    font-size: 1.55rem;
    font-weight: 300;
    color: #40566d;
    letter-spacing: 0.06em;
    margin-bottom: 0.45rem;
}
.naomi-start-name {
    font-family: 'Noto Serif JP', serif;
    font-size: 1.65rem;
    font-weight: 300;
    color: #2f4053;
    margin-bottom: 1.75rem;
}
.naomi-start-main {
    font-family: 'Noto Serif JP', serif;
    font-size: 1.56rem;
    font-weight: 300;
    color: #2f4964;
    letter-spacing: 0.06em;
    margin-bottom: 1.25rem;
}
.naomi-start-sub {
    color: #6d8092;
    font-size: 0.96rem;
    line-height: 2.05;
    margin-bottom: 2rem;
}
.naomi-start-divider {
    height: 1px;
    max-width: 620px;
    margin: 1.55rem auto;
    background: linear-gradient(90deg, transparent, rgba(106, 140, 175, 0.16), transparent);
}
.naomi-start-form-anchor {
    max-width: 640px;
    margin: -0.55rem auto 0;
}
.element-container:has(.naomi-start-form-anchor) + div {
    max-width: 640px;
    margin: -0.55rem auto 0;
}
.element-container:has(.naomi-start-form-anchor) + div [data-testid="stForm"],
.element-container:has(.naomi-start-form-anchor) + div form {
    border: 0 !important;
    border-radius: 0 !important;
    background: transparent !important;
    box-shadow: none !important;
    padding: 0 !important;
}
.naomi-start-form-anchor + div [data-testid="stForm"] {
    max-width: 640px;
    margin: 0 auto 1.1rem auto;
    border: 0;
    border-radius: 0;
    background: transparent;
    box-shadow: none;
    padding: 0;
}
.naomi-start-form-anchor + div [data-testid="stForm"] .stTextInput,
.naomi-start-form-anchor + div [data-testid="stForm"] .stTextInput > div,
.naomi-start-form-anchor + div [data-testid="stForm"] .stTextInput > div > div {
    background: transparent !important;
    border-radius: 999px !important;
}
.naomi-start-form-anchor + div [data-testid="stForm"] .stTextInput div[data-baseweb="input"] {
    overflow: hidden !important;
    background: rgba(255, 255, 255, 0.90) !important;
    border: 1px solid rgba(106, 140, 175, 0.16) !important;
    border-radius: 999px !important;
}
.naomi-start-form-anchor + div [data-testid="stForm"] input {
    min-height: 54px;
    border-radius: 999px !important;
    background: rgba(255, 255, 255, 0.88) !important;
    border: 1px solid rgba(106, 140, 175, 0.16) !important;
    text-align: center !important;
    box-shadow: 0 12px 30px rgba(106, 140, 175, 0.05), inset 0 1px 0 rgba(255,255,255,0.86) !important;
}
.element-container:has(.naomi-start-form-anchor) + div .stButton {
    display: flex;
    justify-content: center;
}
.element-container:has(.naomi-start-form-anchor) + div [data-testid="stForm"] [data-testid="stFormSubmitButton"] {
    display: flex !important;
    justify-content: center !important;
}
.element-container:has(.naomi-start-form-anchor) + div [data-testid="stForm"] [data-testid="stFormSubmitButton"] > button,
.element-container:has(.naomi-start-form-anchor) + div [data-testid="stForm"] button[kind="secondaryFormSubmit"] {
    margin-left: auto !important;
    margin-right: auto !important;
}
.naomi-start-form-anchor + div [data-testid="stForm"] .stButton > button {
    min-height: 44px !important;
    border-radius: 999px !important;
    margin: 0.75rem auto 0 !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
    display: block !important;
    border-color: rgba(106, 140, 175, 0.14) !important;
    background: rgba(236, 242, 248, 0.70) !important;
}
.naomi-start-actions {
    position: relative;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 0.55rem;
    max-width: 820px;
    margin: 0.45rem auto 0;
    padding: 0.55rem;
    border-radius: 999px;
    border: 1px solid rgba(255, 255, 255, 0.58);
    background:
        linear-gradient(135deg, rgba(255,255,255,0.56), rgba(244,248,251,0.34));
    box-shadow: 0 22px 56px rgba(106, 140, 175, 0.09);
    backdrop-filter: blur(18px) saturate(135%);
    -webkit-backdrop-filter: blur(18px) saturate(135%);
}
.naomi-start-actions::before {
    content: "";
    position: absolute;
    left: 8%;
    right: 8%;
    top: -1.55rem;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(106, 140, 175, 0.12), transparent);
}
.naomi-start-action,
.naomi-start-action:visited {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.42rem;
    min-height: 52px;
    border-radius: 999px;
    border: 1px solid rgba(106, 140, 175, 0.12);
    background: rgba(255, 255, 255, 0.46);
    color: #40566d !important;
    text-decoration: none !important;
    font-weight: 500;
    font-size: 0.92rem;
    letter-spacing: 0.02em;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
    transition: transform 0.18s ease, background 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}
.naomi-start-action span {
    color: #d9a94f;
    font-size: 0.96rem;
    line-height: 1;
    opacity: 0.86;
}
.naomi-start-action:hover {
    border-color: rgba(106, 140, 175, 0.34);
    background: rgba(255, 255, 255, 0.82);
    box-shadow: 0 12px 28px rgba(106, 140, 175, 0.10);
    transform: translateY(-1px);
}
.naomi-start-response {
    max-width: 620px;
    margin: 1.4rem auto 0;
    padding: 1.25rem 1.35rem;
    border-radius: 22px;
    background: rgba(255, 255, 255, 0.62);
    border: 1px solid rgba(106, 140, 175, 0.14);
    box-shadow: 0 14px 40px rgba(0, 0, 0, 0.025);
    text-align: left;
}
@media (max-width: 780px) {
    .naomi-home-shell {
        padding: 1.1rem;
        min-height: 0;
        margin-top: 0.9rem;
    }
    .naomi-home-still-life {
        display: none;
    }
    .naomi-home-copy {
        margin-top: 1.1rem;
    }
    .naomi-home-symbol {
        width: 54px;
        height: 54px;
        margin-bottom: 0.8rem;
        font-size: 1.55rem;
    }
    .naomi-home-title {
        font-size: 1.55rem;
        line-height: 1.55;
        margin-bottom: 0.8rem;
    }
    .naomi-home-sub {
        font-size: 0.94rem;
        line-height: 1.85;
        margin-bottom: 1.1rem;
    }
    .naomi-home-actions {
        grid-template-columns: 1fr;
        gap: 0.75rem;
        display: none;
    }
    .naomi-home-action-card {
        min-height: 92px;
        padding: 0.9rem 1rem;
        border-radius: 18px;
    }
    .naomi-home-action-icon {
        width: 40px;
        height: 40px;
        margin-bottom: 0.45rem;
        font-size: 1.2rem;
    }
    .naomi-home-action-title {
        font-size: 0.98rem;
    }
    .naomi-home-action-sub {
        font-size: 0.78rem;
        line-height: 1.45;
    }
    .naomi-start-shell {
        margin-top: 1rem;
        padding: 2rem 1rem 1.25rem;
        border-radius: 24px;
        min-height: 0;
    }
    .naomi-start-still-life {
        display: none;
    }
    .naomi-start-greeting,
    .naomi-start-main {
        font-size: 1.25rem;
    }
    .naomi-start-name {
        font-size: 1.35rem;
    }
    .naomi-start-actions {
        max-width: 100%;
        grid-template-columns: 1fr;
        border-radius: 24px;
        padding: 0.5rem;
    }
}
.stTextInput div[data-baseweb="input"],
.stTextInput div[data-baseweb="input"] > div,
.stTextInput div[data-baseweb="base-input"],
.stTextInput div[data-baseweb="base-input"] > div {
    background: rgba(255, 255, 255, 0.92) !important;
    border-color: rgba(106, 140, 175, 0.16) !important;
    border-radius: 999px !important;
    box-shadow: none !important;
    overflow: hidden !important;
}
.stTextInput div[data-baseweb="input"] input,
.stTextInput div[data-baseweb="base-input"] input,
.stTextInput input {
    background: transparent !important;
    background-color: transparent !important;
    border: 0 !important;
    border-radius: 999px !important;
    color: #33485d !important;
    caret-color: #2f4964 !important;
    box-shadow: none !important;
}
.stTextInput div[data-baseweb="input"] input:focus,
.stTextInput div[data-baseweb="base-input"] input:focus,
.stTextInput input:focus {
    color: #24394f !important;
    caret-color: #1f5f8f !important;
    outline: none !important;
}
.stTextInput div[data-baseweb="input"]:focus-within,
.stTextInput div[data-baseweb="base-input"]:focus-within {
    background: rgba(255, 255, 255, 0.96) !important;
    border-color: rgba(106, 140, 175, 0.30) !important;
    box-shadow: 0 0 0 3px rgba(106, 140, 175, 0.08), 0 10px 26px rgba(106, 140, 175, 0.045) !important;
}
.stTextInput input::placeholder {
    color: rgba(72, 91, 112, 0.44) !important;
    opacity: 1 !important;
}
</style>
""", unsafe_allow_html=True)

# 笏笏 Header & Mode Switcher 笏笏
col_header_title, col_header_lang, col_header_theme, col_header_settings = st.columns([2.8, 0.8, 1, 0.6])

with col_header_title:
    header_title = f'<a class="naomi-logo-link" href="?screen=home&lang={st.session_state.get("language", "JP")}" target="_self" title="Home"><span class="emoji-dim">🌙</span> NAOMI</a>'
    header_sub = t("header_sub_large") if is_large else t("header_sub")
    
    st.markdown(f"""
    <div style="padding: 0.5rem 0 0.5rem 0;">
        <div style="display:flex; align-items:center; flex-wrap:wrap; gap:0.2rem;">
            <h1 style="margin-bottom:0; font-family:'Noto Serif JP', serif; font-size:1.8rem; font-weight: 300;">{header_title}</h1>
            <span class="naomi-status-pill"><span class="naomi-status-dot"></span>{"Active & Listening" if st.session_state.get("language") == "EN" else "静かに待機中"}</span>
        </div>
        <p style="color:gray; font-size:0.95rem; margin-top:0.3rem; margin-bottom:0; font-weight: 300;">
            {header_sub}
        </p>
    </div>
    """, unsafe_allow_html=True)

with col_header_lang:
    st.markdown("<div style='padding-top: 0.8rem;'></div>", unsafe_allow_html=True)
    lang_options = {"JP": "JP 日本語", "EN": "EN English"}
    st.markdown('<div class="header-lang-control"></div>', unsafe_allow_html=True)
    selected_lang = st.selectbox(
        "Language",
        options=list(lang_options.keys()),
        format_func=lambda x: lang_options[x],
        index=list(lang_options.keys()).index(st.session_state.get("language", "JP")),
        key="lang_selector"
    )
    if selected_lang != st.session_state.language:
        st.session_state.language = selected_lang
        st.rerun()

with col_header_theme:
    st.markdown("<div style='padding-top: 0.8rem;'></div>", unsafe_allow_html=True)
    theme_options = {"light": "☀️ Calm Light", "night": "🌙 Quiet Night"}
    st.markdown('<div class="header-theme-control"></div>', unsafe_allow_html=True)
    selected_theme = st.selectbox(
        "画面の雰囲気" if st.session_state.language == "JP" else "Atmosphere",
        options=list(theme_options.keys()),
        format_func=lambda x: theme_options[x],
        index=list(theme_options.keys()).index(st.session_state.get("theme_mode", "light")),
        key="theme_selector"
    )
    if selected_theme != st.session_state.theme_mode:
        st.session_state.theme_mode = selected_theme
        st.rerun()

with col_header_settings:
    st.markdown("<div style='padding-top: 0.8rem;'></div>", unsafe_allow_html=True)
    st.markdown('<div class="header-settings-control"></div>', unsafe_allow_html=True)
    with st.popover("❓", use_container_width=False):
        st.markdown("### Help")
        st.markdown(f"**Pressure**  \n{naomi_help_text('pressure')}")
        st.markdown(f"**Staff Note**  \n{naomi_help_text('staff_note')}")
        st.markdown(f"**HumanState**  \n{naomi_help_text('human_state')}")
        st.markdown(f"**Mode**  \n{naomi_help_text('mode')}")
        st.markdown(f"**Intake Summary**  \n{naomi_help_text('intake_summary')}")
        st.markdown(f"**Red Flag**  \n{naomi_help_text('red_flag')}")
    with st.popover("⚙", use_container_width=False):
        st.markdown(tr("### Internal State", "### 内部状態"))
        st.markdown(f"**HumanState**  \n{naomi_help_text('human_state')}")
        st.markdown(f"**Pressure**  \n{naomi_help_text('pressure')}")
        st.markdown(f"**Mode**  \n{naomi_help_text('mode')}")
        st.markdown(f"**Red Flag**  \n{naomi_help_text('red_flag')}")
        st.divider()
        if st.session_state.last_result:
            detail_result = st.session_state.last_result[1]
            st.json({
                "stress": round(detail_result.state.stress, 2),
                "energy": round(detail_result.state.energy, 2),
                "pressure": detail_result.pressure_level,
                "phase": (getattr(detail_result, "asurada_state", {}) or {}).get("phase"),
            })
        else:
            st.caption(tr("NAOMI has not responded yet.", "まだNAOMIの返答はありません。"))

if st.session_state.naomi_screen == "start":
    current_lang = st.session_state.get("language", "JP")
    hour_now = datetime.now().hour
    if current_lang == "EN":
        start_salutation = "Good morning" if 5 <= hour_now < 11 else "Hello" if 11 <= hour_now < 18 else "Good evening"
        start_main = "How are you feeling today?"
        start_sub = "There is no need to rush.<br>It is okay if what you want to say is not organized yet."
        start_placeholder = "You can leave a short phrase here"
        start_send = "Send quietly"
        start_state = "Organize my state"
        start_memo = "Create a care note"
        start_home = "Home"
    else:
        start_salutation = "おはようございます" if 5 <= hour_now < 11 else "こんにちは" if 11 <= hour_now < 18 else "こんばんは"
        start_main = "今日はどんな感じですか？"
        start_sub = "急がなくて大丈夫です<br>話したいことがまとまっていなくても大丈夫です"
        start_placeholder = "例：あなたの体調について教えてください"
        start_send = "そっと送る"
        start_state = "状態を整理する"
        start_memo = "相談前メモを作る"
        start_home = "ホームへ"

    st.markdown(f"""
    <section class="naomi-start-shell">
        <div class="naomi-start-still-life" aria-hidden="true">
            <div class="naomi-start-branch"></div>
            <div class="naomi-start-vase"></div>
            <div class="naomi-start-mug"></div>
        </div>
        <div class="naomi-start-copy">
            <div class="naomi-start-symbol">🌙</div>
            <div class="naomi-start-greeting">{start_salutation}</div>
            <div class="naomi-start-main">{start_main}</div>
            <div class="naomi-start-sub">{start_sub}</div>
            <div class="naomi-start-divider"></div>
        </div>
    </section>
    """, unsafe_allow_html=True)

    st.markdown('<div class="naomi-start-form-anchor"></div>', unsafe_allow_html=True)
    with st.form("start_free_chat_form", clear_on_submit=True):
        start_user_text = st.text_input(
            tr("Talk to NAOMI", "NAOMIに話しかける"),
            placeholder=start_placeholder,
            label_visibility="collapsed",
        )
        _, start_send_col, _ = st.columns([1, 1, 1])
        with start_send_col:
            submitted_start_chat = st.form_submit_button(start_send, use_container_width=True)

    if submitted_start_chat and start_user_text.strip():
        result = naomi_process(start_user_text.strip(), active_profile(), free_chat=True)
        st.session_state.last_result = (start_user_text.strip(), result)
        st.session_state.proactive_question = None
        st.rerun()

    if st.session_state.last_result:
        _, result = st.session_state.last_result
        if result.text:
            visible_phase_label = phase_label(result)
            if visible_phase_label:
                st.markdown(f"""
                <div style="text-align:center; margin-top:1rem;">
                    <span style="display:inline-block; background:rgba(106, 140, 175, 0.08); border:1px solid rgba(106, 140, 175, 0.16); color:#4f6f90; border-radius:999px; padding:0.35rem 0.75rem; font-size:0.85rem;">
                        {visible_phase_label}
                    </span>
                </div>
                """, unsafe_allow_html=True)
            result_text_display = display_response_text(result.text, result.scenario_id)
            st.markdown(f"""
            <div class="naomi-start-response">
                <h5 style="margin:0 0 0.7rem 0; font-family:'Noto Serif JP', serif; color:#4f6f90; font-size:1.05rem; letter-spacing:0.05em;">NAOMI</h5>
                <p style="font-size:1.02rem; line-height:1.85; margin:0;">{result_text_display}</p>
            </div>
            """, unsafe_allow_html=True)
            show_hackathon_runtime_debug(result)

    st.markdown(f"""
    <div class="naomi-start-divider"></div>
    <div class="naomi-start-actions">
        <a class="naomi-start-action" href="?screen=state&mode=tired&lang={current_lang}" target="_self"><span>🌿</span>{start_state}</a>
        <a class="naomi-start-action" href="?screen=state&mode=health&lang={current_lang}" target="_self"><span>📋</span>{start_memo}</a>
        <a class="naomi-start-action" href="?screen=home&lang={current_lang}" target="_self"><span>⌂</span>{start_home}</a>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

if st.session_state.naomi_screen == "home":
    greeting_text = home_greeting()
    current_lang = st.session_state.get("language", "JP")
    chat_bg = "rgba(255, 255, 255, 0.62)" if theme_mode == "light" else "rgba(13, 20, 35, 0.45)"
    chat_border = "rgba(106, 140, 175, 0.14)" if theme_mode == "light" else "rgba(197, 168, 128, 0.14)"
    chat_title = "#4f6f90" if theme_mode == "light" else "#c5a880"
    st.markdown(f'<div class="naomi-return-row">{start_screen_link()}</div>', unsafe_allow_html=True)
    home_chat_intro = tr(
        "You can speak from here without choosing a menu.",
        "メニューを選ばなくても、ここからそのまま話せます。"
    )
    home_chat_sub = tr(
        "A short phrase is enough. NAOMI first listens and asks only what is needed to understand the situation.",
        "短い言葉で大丈夫です。NAOMIはまず受け止めて、状況を知るために必要なことだけをそっと確認します。"
    )
    st.markdown(f"""
    <section class="naomi-home-shell">
        <div class="naomi-home-still-life" aria-hidden="true">
            <div class="naomi-home-branch"></div>
            <div class="naomi-home-vase"></div>
            <div class="naomi-home-mug"></div>
        </div>
        <div class="naomi-home-copy">
            <div class="naomi-home-symbol">🌙</div>
            <h2 class="naomi-home-title">{t("welcome_title")}</h2>
            <p class="naomi-home-sub">
                {greeting_text}<br>
                <span style="font-size:0.92em; opacity:0.82;">{t("welcome_subtitle")}</span>
            </p>
        </div>
        <div class="naomi-home-actions">
            <a class="naomi-home-action-card" href="?screen=state&mode=tired&lang={current_lang}" target="_self">
                <div class="naomi-home-action-icon">🌿</div>
                <div class="naomi-home-action-title">{t("action_1_title")}</div>
                <div class="naomi-home-action-sub">{t("action_1_sub")}</div>
            </a>
            <a class="naomi-home-action-card" href="?screen=state&mode=mental&lang={current_lang}" target="_self">
                <div class="naomi-home-action-icon">💬</div>
                <div class="naomi-home-action-title">{t("action_2_title")}</div>
                <div class="naomi-home-action-sub">{t("action_2_sub")}</div>
            </a>
            <a class="naomi-home-action-card" href="?screen=state&mode=health&lang={current_lang}" target="_self">
                <div class="naomi-home-action-icon">📋</div>
                <div class="naomi-home-action-title">{t("action_3_title")}</div>
                <div class="naomi-home-action-sub">{t("action_3_sub")}</div>
            </a>
        </div>
    </section>
    """, unsafe_allow_html=True)

    st.markdown(f'<div class="naomi-home-note">{t("home_note")}</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="naomi-home-chat-message" style="background:{chat_bg}; border:1px solid {chat_border}; border-radius:22px; padding:1.25rem 1.35rem; margin:1rem auto 1rem auto; max-width:860px; box-shadow:0 18px 48px rgba(106, 140, 175, 0.07);">
        <div style="font-family:'Noto Serif JP', serif; color:{chat_title}; font-size:1.08rem; margin-bottom:0.35rem; letter-spacing:0.04em;">
            {greeting_text}
        </div>
        <div style="color:gray; font-size:0.88rem; line-height:1.7;">
            {home_chat_intro}<br>
            {home_chat_sub}
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="naomi-home-chat-form-anchor"></div>', unsafe_allow_html=True)
    with st.form("home_free_chat_form", clear_on_submit=True):
        home_user_text = st.text_input(
            tr("Talk to NAOMI", "NAOMIに話しかける"),
            placeholder=tr("Example: I have been tired lately", "例：最近疲れていて"),
            label_visibility="collapsed",
        )
        _, home_send_col, _ = st.columns([1, 1, 1])
        with home_send_col:
            submitted_home_chat = st.form_submit_button(tr("Send quietly", "そっと送る"), use_container_width=True)
    if submitted_home_chat and home_user_text.strip():
        result = naomi_process(home_user_text.strip(), active_profile(), free_chat=True)
        st.session_state.last_result = (home_user_text.strip(), result)
        st.session_state.proactive_question = None
        st.rerun()

    if st.session_state.last_result:
        _, result = st.session_state.last_result
        if result.text:
            visible_phase_label = phase_label(result)
            if visible_phase_label:
                st.markdown(f"""
                <div style="display:inline-block; background:rgba(106, 140, 175, 0.08); border:1px solid rgba(106, 140, 175, 0.16); color:{chat_title}; border-radius:999px; padding:0.35rem 0.75rem; font-size:0.85rem; margin:0.8rem 0 0.1rem 0;">
                    {visible_phase_label}
                </div>
                """, unsafe_allow_html=True)
            result_text_display = display_response_text(result.text, result.scenario_id)
            st.markdown(f"""
            <div style="background:{chat_bg}; border:1px solid {chat_border}; border-radius:22px; padding:1.35rem 1.45rem; margin:1rem auto 1.4rem auto; max-width:860px; box-shadow:0 14px 40px rgba(0,0,0,0.025);">
                <h5 style="margin:0 0 0.7rem 0; font-family:'Noto Serif JP', serif; color:{chat_title}; font-size:1.05rem; letter-spacing:0.05em;">NAOMI</h5>
                <p style="font-size:1.02rem; line-height:1.85; margin:0;">{result_text_display}</p>
            </div>
            """, unsafe_allow_html=True)
            show_hackathon_runtime_debug(result)
    st.stop()

# ── 🌿 NAOMIを使う方への静かな案内 ──
st.markdown("<div id='naomi-menu-top' style='height: 1px;'></div>", unsafe_allow_html=True)
st.markdown(f'<div class="naomi-return-row">{start_screen_link()}</div>', unsafe_allow_html=True)

copy_title_color = "#2c3e50" if theme_mode == "light" else "#f1f5f9"
copy_sub_color = "#475569" if theme_mode == "light" else "#cbd5e1"
accent_color = "#6a8caf" if theme_mode == "light" else "#c5a880"
card_bg_hero = "rgba(255, 255, 255, 0.45)" if theme_mode == "light" else "rgba(13, 20, 35, 0.35)"
card_border_hero = "rgba(255, 255, 255, 0.5)" if theme_mode == "light" else "rgba(197, 168, 128, 0.12)"
badge_bg = "rgba(106, 140, 175, 0.1)" if theme_mode == "light" else "rgba(197, 168, 128, 0.1)"

with st.expander(t("why_naomi_title"), expanded=False):
    about_html = dedent(f"""
    <div style="background: {card_bg_hero}; border: 1px solid {card_border_hero}; border-radius: 20px; padding: 1.8rem; margin-bottom: 1.5rem; backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);">
        <div style="text-align: center; max-width: 850px; margin: 0 auto;">
            <span style="font-family: 'Outfit', sans-serif; font-size: 0.8rem; letter-spacing: 0.2em; color: {accent_color}; font-weight: 500; text-transform: uppercase;">
                quiet care space
            </span>
            <h2 style="font-family: 'Noto Serif JP', serif; font-weight: 300; color: {copy_title_color}; margin-top: 0.5rem; margin-bottom: 0.8rem; font-size: 1.8rem; letter-spacing: 0.05em;">
                {t("why_naomi_subtitle")}
            </h2>
            <p style="color: {copy_title_color}; font-size: 1.05rem; line-height: 1.6; margin-bottom: 1.0rem; font-weight: 400; font-family: 'Noto Serif JP', serif;">
                {t("why_naomi_desc")}
            </p>
            <p style="color: {copy_sub_color}; font-size: 0.9rem; line-height: 1.8; margin: 0 auto 1.2rem auto; font-weight: 300; max-width: 750px;">
                {t("why_naomi_long")}

            </p>
            <div style="display: flex; justify-content: center; gap: 0.6rem; flex-wrap: wrap; margin-bottom: 0.5rem;">
                <span style="background: {badge_bg}; color: {accent_color}; padding: 0.2rem 0.6rem; border-radius: 10px; font-size: 0.75rem; font-weight: 500; letter-spacing: 0.05em;"><span class="emoji-dim">🌙</span> {t("badge_1")}</span>
                <span style="background: {badge_bg}; color: {accent_color}; padding: 0.2rem 0.6rem; border-radius: 10px; font-size: 0.75rem; font-weight: 500; letter-spacing: 0.05em;"><span class="emoji-dim">🫧</span> {t("badge_2")}</span>
                <span style="background: {badge_bg}; color: {accent_color}; padding: 0.2rem 0.6rem; border-radius: 10px; font-size: 0.75rem; font-weight: 500; letter-spacing: 0.05em;"><span class="emoji-dim">🌿</span> {t("badge_3")}</span>
            </div>
        </div>
    </div>
    """).strip().replace("\n", " ")
    st.markdown(about_html, unsafe_allow_html=True)
    
    card_bg_guide = "rgba(106, 140, 175, 0.03)" if theme_mode == "light" else "rgba(197, 168, 128, 0.03)"
    border_color_guide = "rgba(106, 140, 175, 0.1)" if theme_mode == "light" else "rgba(197, 168, 128, 0.1)"
    text_color_guide = "#2c3e50" if theme_mode == "light" else "#e2e8f0"
    guide_html = dedent(f"""
    <div style="background: {card_bg_guide}; border: 1px solid {border_color_guide}; border-radius: 16px; padding: 1.2rem; font-size: 0.9rem; color: {text_color_guide}; font-weight: 300;">
        <h4 style="margin-top:0; font-family:'Noto Serif JP', serif; font-size: 1.05rem; color: {accent_color}; margin-bottom: 0.6rem; letter-spacing: 0.05em;"><span class="emoji-dim">💡</span> {t("guide_title")}</h4>
        <p style="font-size: 0.88rem; line-height: 1.6; margin-bottom: 0.8rem;">
            {t("guide_desc")}
        </p>
        <div style="font-size: 0.85rem; line-height: 1.6;">
            <b>{t("guide_step_title")}</b>
            <ol style="margin-top: 0.2rem; padding-left: 1.2rem;">
                <li>{t("guide_step_1")}</li>
                <li>{t("guide_step_2")}</li>
                <li>{t("guide_step_3")}</li>
            </ol>
        </div>
    </div>
    """).strip().replace("\n", " ")
    st.markdown(guide_html, unsafe_allow_html=True)

# ── 低圧メッセージ ──
st.markdown(f"""
<div class="intro-prompt" style="text-align: center; padding: 2.2rem 0 1.8rem 0; max-width: 800px; margin: 0 auto;">
    <h3 style="font-family: 'Noto Serif JP', serif; font-weight: 300; color: {copy_title_color}; margin-bottom: 0.6rem; font-size: 1.7rem; letter-spacing: 0.05em; line-height: 1.4;">
        {t("today_feel")}<br>
        <span style="font-size: 1.2rem; opacity: 0.85; font-weight: 300;">{t("today_feel_sub")}</span>
    </h3>
    <p style="color: {copy_sub_color}; font-size: 0.95rem; line-height: 1.8; margin-top: 0.8rem; font-weight: 300; opacity: 0.8;">
        {t("home_note")}
    </p>
</div>
""", unsafe_allow_html=True)

# ── 2x2 の静かな状態選択カードUI ──
if "naomi_active_mode" not in st.session_state:
    st.session_state.naomi_active_mode = ""
elif st.session_state.naomi_active_mode in ["🩺 体調を整理したい", "🧭 今の状態を一緒に整理する"]:
    st.session_state.naomi_active_mode = "🩺 今の健康状態を一緒に整理しましょう"
elif st.session_state.naomi_active_mode in ["🌙 Slightly tired"]:
    st.session_state.naomi_active_mode = "🌙 少し疲れている"
elif st.session_state.naomi_active_mode in ["🩺 Let's gently organize your symptoms"]:
    st.session_state.naomi_active_mode = "🩺 今の健康状態を一緒に整理しましょう"

# 状態を選ぶだけの静かな余白を確保
st.markdown("<div class='mode-card-spacer' style='margin-top: 1.5rem; margin-bottom: 1.0rem;'></div>", unsafe_allow_html=True)

card_col1, card_col2 = st.columns(2)

with card_col1:
    # 🌙 少し疲れている
    is_active_1 = st.session_state.naomi_active_mode == "🌙 少し疲れている"
    border_1 = "1px solid rgba(106, 140, 175, 0.28)" if is_active_1 else "1px solid rgba(106, 140, 175, 0.065)"
    bg_1 = "rgba(106, 140, 175, 0.045)" if is_active_1 else "rgba(255, 255, 255, 0.20)" if theme_mode == "light" else "rgba(13, 20, 35, 0.12)"
    shadow_1 = "0 18px 44px rgba(106, 140, 175, 0.045)" if is_active_1 else "0 16px 40px rgba(31, 38, 55, 0.018)"
    
    st.markdown(f"""
    <div class="mode-card" style="background: {bg_1}; border: {border_1}; border-radius: 26px; padding: 1.8rem 1.6rem; text-align: center; min-height: 140px; height: auto; display: flex; flex-direction: column; justify-content: center; align-items: center; box-shadow: {shadow_1}; backdrop-filter: blur(22px) saturate(108%); -webkit-backdrop-filter: blur(22px) saturate(108%); transition: all 0.45s cubic-bezier(0.16, 1, 0.3, 1);">
        <h4 style="margin: 0 0 0.5rem 0; font-family: 'Noto Serif JP', serif; font-size: 1.05rem; color: {accent_color}; font-weight: 300; letter-spacing: 0.05em;">
            {t("card_1_title")}
        </h4>
        <p style="font-size: 0.8rem; color: gray; margin: 0; line-height: 1.4; font-weight: 300;">
            {t("card_1_desc")}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    btn_label_1 = t("btn_selected") if is_active_1 else t("btn_select")
    if st.button(btn_label_1, key="mode_btn_1", use_container_width=True, type="primary" if is_active_1 else "secondary", help=naomi_help_text("mode")):
        switch_mode("🌙 少し疲れている")

    # ♿ 聞こえ方
    st.markdown("<div style='margin-top: 1.2rem;'></div>", unsafe_allow_html=True)
    is_active_3 = st.session_state.naomi_active_mode == "♿ 入力を楽にしたい"
    border_3 = "1px solid rgba(106, 140, 175, 0.28)" if is_active_3 else "1px solid rgba(106, 140, 175, 0.065)"
    bg_3 = "rgba(106, 140, 175, 0.045)" if is_active_3 else "rgba(255, 255, 255, 0.20)" if theme_mode == "light" else "rgba(13, 20, 35, 0.12)"
    shadow_3 = "0 18px 44px rgba(106, 140, 175, 0.045)" if is_active_3 else "0 16px 40px rgba(31, 38, 55, 0.018)"
    
    st.markdown(f"""
    <div class="mode-card" style="background: {bg_3}; border: {border_3}; border-radius: 26px; padding: 1.8rem 1.6rem; text-align: center; min-height: 140px; height: auto; display: flex; flex-direction: column; justify-content: center; align-items: center; box-shadow: {shadow_3}; backdrop-filter: blur(22px) saturate(108%); -webkit-backdrop-filter: blur(22px) saturate(108%); transition: all 0.45s cubic-bezier(0.16, 1, 0.3, 1);">
        <h4 style="margin: 0 0 0.5rem 0; font-family: 'Noto Serif JP', serif; font-size: 1.05rem; color: {accent_color}; font-weight: 300; letter-spacing: 0.05em;">
            {t("card_3_title")}
        </h4>
        <p style="font-size: 0.8rem; color: gray; margin: 0; line-height: 1.4; font-weight: 300;">
            {t("card_3_desc")}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    btn_label_3 = t("btn_selected") if is_active_3 else t("btn_select")
    if st.button(btn_label_3, key="mode_btn_3", use_container_width=True, type="primary" if is_active_3 else "secondary", help=naomi_help_text("mode")):
        switch_mode("♿ 入力を楽にしたい")

with card_col2:
    # 🧠 不安
    is_active_2 = st.session_state.naomi_active_mode == "🧠 考えすぎている"
    border_2 = "1px solid rgba(106, 140, 175, 0.28)" if is_active_2 else "1px solid rgba(106, 140, 175, 0.065)"
    bg_2 = "rgba(106, 140, 175, 0.045)" if is_active_2 else "rgba(255, 255, 255, 0.20)" if theme_mode == "light" else "rgba(13, 20, 35, 0.12)"
    shadow_2 = "0 18px 44px rgba(106, 140, 175, 0.045)" if is_active_2 else "0 16px 40px rgba(31, 38, 55, 0.018)"
    
    st.markdown(f"""
    <div class="mode-card" style="background: {bg_2}; border: {border_2}; border-radius: 26px; padding: 1.8rem 1.6rem; text-align: center; min-height: 140px; height: auto; display: flex; flex-direction: column; justify-content: center; align-items: center; box-shadow: {shadow_2}; backdrop-filter: blur(22px) saturate(108%); -webkit-backdrop-filter: blur(22px) saturate(108%); transition: all 0.45s cubic-bezier(0.16, 1, 0.3, 1);">
        <h4 style="margin: 0 0 0.5rem 0; font-family: 'Noto Serif JP', serif; font-size: 1.05rem; color: {accent_color}; font-weight: 300; letter-spacing: 0.05em;">
            {t("card_2_title")}
        </h4>
        <p style="font-size: 0.8rem; color: gray; margin: 0; line-height: 1.4; font-weight: 300;">
            {t("card_2_desc")}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    btn_label_2 = t("btn_selected") if is_active_2 else t("btn_select")
    if st.button(btn_label_2, key="mode_btn_2", use_container_width=True, type="primary" if is_active_2 else "secondary", help=naomi_help_text("mode")):
        switch_mode("🧠 考えすぎている")

    # 🩺 整理したい
    st.markdown("<div style='margin-top: 1.2rem;'></div>", unsafe_allow_html=True)
    is_active_4 = st.session_state.naomi_active_mode == "🩺 今の健康状態を一緒に整理しましょう"
    border_4 = "1px solid rgba(106, 140, 175, 0.30)" if is_active_4 else "1px solid rgba(106, 140, 175, 0.075)"
    bg_4 = "rgba(106, 140, 175, 0.05)" if is_active_4 else "rgba(255, 255, 255, 0.16)" if theme_mode == "light" else "rgba(13, 20, 35, 0.10)"
    shadow_4 = "0 18px 44px rgba(106, 140, 175, 0.045)" if is_active_4 else "0 16px 40px rgba(31, 38, 55, 0.018)"
    
    st.markdown(f"""
    <div class="mode-card" style="background: {bg_4}; border: {border_4}; border-radius: 26px; padding: 1.8rem 1.6rem; text-align: center; min-height: 140px; height: auto; display: flex; flex-direction: column; justify-content: center; align-items: center; box-shadow: {shadow_4}; backdrop-filter: blur(22px) saturate(108%); -webkit-backdrop-filter: blur(22px) saturate(108%); transition: all 0.45s cubic-bezier(0.16, 1, 0.3, 1);">
        <h4 style="margin: 0 0 0.5rem 0; font-family: 'Noto Serif JP', serif; font-size: 1.05rem; color: {accent_color}; font-weight: 300; letter-spacing: 0.05em;">
            {t("card_4_title")}
        </h4>
        <p style="font-size: 0.8rem; color: gray; margin: 0; line-height: 1.4; font-weight: 300;">
            {t("card_4_desc")}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    btn_label_4 = t("btn_selected") if is_active_4 else t("btn_select")
    if st.button(btn_label_4, key="mode_btn_4", use_container_width=True, type="primary" if is_active_4 else "secondary", help=naomi_help_text("mode")):
        switch_mode("🩺 今の健康状態を一緒に整理しましょう")

free_text_bg = "rgba(106, 140, 175, 0.045)" if theme_mode == "light" else "rgba(197, 168, 128, 0.06)"
free_text_border = "rgba(106, 140, 175, 0.14)" if theme_mode == "light" else "rgba(197, 168, 128, 0.14)"
free_text_color = "#4f6f90" if theme_mode == "light" else "#c5a880"
st.markdown(f"""
<div style="background:{free_text_bg}; border:1px solid {free_text_border}; border-radius:18px; padding:1rem 1.1rem; margin:1.4rem 0 1rem 0;">
    <div style="font-family:'Noto Serif JP', serif; color:{free_text_color}; font-size:0.98rem; margin-bottom:0.25rem;">言葉にできる範囲で、今の状態を書いても大丈夫です</div>
    <div style="color:gray; font-size:0.84rem;">ボタンだけでも使えます。無理に書かなくても大丈夫です。</div>
</div>
""", unsafe_allow_html=True)
st.markdown('<div class="naomi-state-chat-form-anchor"></div>', unsafe_allow_html=True)
with st.form("state_free_text_form", clear_on_submit=True):
    state_free_text = st.text_input(
        "任意の入力",
        placeholder="例：最近仕事が忙しくて疲れています",
        label_visibility="collapsed",
    )
    _, state_send_col, _ = st.columns([1, 1, 1])
    with state_send_col:
        submitted_free_text = st.form_submit_button("そっと送る", use_container_width=True)
if submitted_free_text and state_free_text.strip():
    result = naomi_process(state_free_text.strip(), active_profile())
    st.session_state.last_result = (state_free_text.strip(), result)
    st.session_state.proactive_question = None
    st.rerun()

if st.session_state.last_result:
    _, result = st.session_state.last_result
    if result.text:
        visible_phase_label = phase_label(result)
        if visible_phase_label:
            phase_bg = "rgba(106, 140, 175, 0.08)" if theme_mode == "light" else "rgba(197, 168, 128, 0.10)"
            phase_border = "rgba(106, 140, 175, 0.18)" if theme_mode == "light" else "rgba(197, 168, 128, 0.18)"
            phase_color = "#4f6f90" if theme_mode == "light" else "#c5a880"
            st.markdown(f"""
            <div style="display:inline-block; background:{phase_bg}; border:1px solid {phase_border}; color:{phase_color}; border-radius:999px; padding:0.35rem 0.75rem; font-size:0.85rem; margin:0.6rem 0 0.2rem 0;">
                {visible_phase_label}
            </div>
            """, unsafe_allow_html=True)
        result_text_display = display_response_text(result.text, result.scenario_id)
        result_bg = "rgba(255, 255, 255, 0.55)" if theme_mode == "light" else "rgba(13, 20, 35, 0.45)"
        result_border = "rgba(106, 140, 175, 0.14)" if theme_mode == "light" else "rgba(197, 168, 128, 0.14)"
        result_title = "#6a8caf" if theme_mode == "light" else "#c5a880"
        st.markdown(f"""
        <div style="background: {result_bg}; border: 1px solid {result_border}; border-radius: 20px; padding: 1.4rem 1.5rem; margin: 1.4rem 0 1.2rem 0; box-shadow: 0 10px 30px rgba(0,0,0,0.02);">
            <h5 style="margin:0 0 0.7rem 0; font-family:'Noto Serif JP', serif; color: {result_title}; font-size: 1.05rem; letter-spacing: 0.05em;">🌙 NAOMI</h5>
            <p style="font-size: 1.02rem; line-height: 1.8; margin: 0;">{result_text_display}</p>
        </div>
        """, unsafe_allow_html=True)
        show_hackathon_runtime_debug(result)

st.markdown("<hr style='border: 0; border-top: 1px solid rgba(106, 140, 175, 0.05); margin: 1.5rem 0;'>", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────
# Section 1: 少し疲れている
# ──────────────────────────────────────────────────────────
if st.session_state.naomi_active_mode == "🌙 少し疲れている":
    # 初見30秒で伝わるガイダンスを美しいカードで表示
    card_bg_guide = "rgba(106, 140, 175, 0.05)" if theme_mode == "light" else "rgba(197, 168, 128, 0.05)"
    border_color_guide = "rgba(106, 140, 175, 0.15)" if theme_mode == "light" else "rgba(197, 168, 128, 0.15)"
    text_color_guide = "#2c3e50" if theme_mode == "light" else "#e2e8f0"
    
    _exp_label = "💡 How to Use" if st.session_state.get("language", "JP") == "EN" else "💡 迷ったときの使い方"
    with st.expander(_exp_label, expanded=False):
        quick_guide_title = "Quick Guide" if st.session_state.get("language", "JP") == "EN" else "使い方の目安"
        quick_guide_body = tr(
            "Just choose the closest option. NAOMI will keep words gentle and receive your current state.<br>If needed, a small note will appear below.",
            "近いものを選ぶだけで大丈夫です。NAOMIが言葉の量を控えめにしながら、今の状態を受け止めます。<br>必要に応じて、画面下部に<b>小さなメモ</b>が表示されます。"
        )
        quick_guide_label = tr("👉 Quick guideline:", "👉 迷ったときの目安：")
        quick_guide_step_1 = tr(
            'If you are tired, start with <b>"🌙 Slightly tired"</b>.',
            "疲れている時は、まず <b>「🌙 少し疲れている」</b> を選んでください。"
        )
        quick_guide_step_2 = tr(
            'If your mind won\'t stop racing, <b>"🧠 Anxious & restless"</b> may fit.',
            "考えが止まらない時は <b>「🧠 考えすぎている」</b> が近いかもしれません。"
        )
        quick_guide_step_3 = tr(
            'For physical symptoms, choose <b>"🩺 Let\'s organize"</b>.',
            "体調や症状を伝えたい時は、<b>「🩺 今の健康状態を一緒に整理しましょう」</b> を選んでください。"
        )
        st.markdown(f"""
        <div style="background: {card_bg_guide}; border: 1px solid {border_color_guide}; border-radius: 20px; padding: 1.5rem; margin-bottom: 1rem;">
            <h4 style="margin-top:0; font-family:'Noto Serif JP', serif; font-size: 1.1rem; color: {accent_color}; margin-bottom: 0.8rem; letter-spacing: 0.05em;"><span class="emoji-dim">💡</span> {quick_guide_title}</h4>
        <p style="font-size: 0.95rem; line-height: 1.7; margin-bottom: 1rem; color: {text_color_guide}; font-weight: 300;">
            {quick_guide_body}
        </p>
        <div style="font-size: 0.9rem; line-height: 1.6; color: {text_color_guide}; font-weight: 300;">
            <b>{quick_guide_label}</b>
            <ol style="margin-top: 0.3rem; padding-left: 1.2rem;">
                <li>{quick_guide_step_1}</li>
                <li>{quick_guide_step_2}</li>
                <li>{quick_guide_step_3}</li>
            </ol>
        </div>
        </div>
        """, unsafe_allow_html=True)
    
    # 巨大状態選択カード (3列×2行)
    row1_col1, row1_col2, row1_col3 = st.columns(3)
    row2_col1, row2_col2, row2_col3 = st.columns(3)
    
    # 1行目
    with row1_col1:
        st.markdown('<div class="status-btn-exhausted"></div>', unsafe_allow_html=True)
        if st.button(tr("🔥 At my limit, need a little guidance", "🔥 限界で、少し助言がほしい"), key="state_btn_exhausted", use_container_width=True):
            text = "どうしたらいいか教えてほしいけど、正直もう疲れてる"
            result = naomi_process(text, active_profile())
            st.session_state.last_result = (text, result)
            st.session_state.proactive_question = None
            st.rerun()
            
    with row1_col2:
        st.markdown('<div class="status-btn-anxiety"></div>', unsafe_allow_html=True)
        if st.button(tr("😰 Feeling anxious", "😰 不安を感じる"), key="state_btn_anxiety", use_container_width=True):
            text = "明日のことを考えると不安で落ち着かない"
            result = naomi_process(text, active_profile())
            st.session_state.last_result = (text, result)
            st.session_state.proactive_question = None
            st.rerun()
            
    with row1_col3:
        st.markdown('<div class="status-btn-tired"></div>', unsafe_allow_html=True)
        if st.button(tr("😮‍💨 Tired", "😮‍💨 疲れている"), key="state_btn_tired", use_container_width=True):
            text = "最近ちょっと疲れてて…"
            result = naomi_process(text, active_profile())
            st.session_state.last_result = (text, result)
            st.session_state.proactive_question = None
            st.rerun()
            
    # 2行目
    with row2_col1:
        st.markdown('<div class="status-btn-insomnia"></div>', unsafe_allow_html=True)
        if st.button(tr("🌙 Sleepless night", "🌙 眠れない夜"), key="state_btn_insomnia", use_container_width=True):
            text = "明日も早いのに、考えごとが止まらなくて眠れない"
            profile = active_profile()
            result = naomi_process(text, profile)
            st.session_state.last_result = (text, result)
            st.session_state.proactive_question = None
            # 眠れない夜を選択時は、低圧なQuiet Nightへ自動移行！
            st.session_state.theme_mode = "night"
            st.rerun()
            
    with row2_col2:
        st.markdown('<div class="status-btn-lonely"></div>', unsafe_allow_html=True)
        if st.button(tr("😢 Lonely", "😢 一人で寂しい"), key="state_btn_lonely", use_container_width=True):
            text = "なんか一人でいる感じがして寂しい"
            result = naomi_process(text, active_profile())
            st.session_state.last_result = (text, result)
            st.session_state.proactive_question = None
            st.rerun()
            
    with row2_col3:
        st.markdown('<div class="status-btn-seiri"></div>', unsafe_allow_html=True)
        if st.button(tr("🩺 Organize health state", "🩺 健康状態を整理する"), key="state_btn_seiri", use_container_width=True):
            st.session_state.naomi_active_mode = "🩺 今の健康状態を一緒に整理しましょう"
            st.rerun()

    # Accessibility Mode ガラスカード
    st.markdown('<div class="accessibility-container">', unsafe_allow_html=True)
    _acc_title = "♿ Accessibility Options" if st.session_state.get("language", "JP") == "EN" else "♿ 入力を楽にしたい"

    st.markdown(f"<p style='text-align: center; font-family: \"Noto Serif JP\", serif; font-size: 1.1rem; margin-bottom: 1.2rem; font-weight: 400;'>{_acc_title}</p>", unsafe_allow_html=True)
    
    col_acc1, col_acc2, col_acc3, col_acc4, col_acc5 = st.columns(5)
    with col_acc1:
        _tog1 = "Large text" if st.session_state.get("language", "JP") == "EN" else "大きい文字"
        st.toggle(_tog1, key="acc_large_font", on_change=sync_large_font_from_acc)
    with col_acc2:
        _tog2 = "👆 Button only" if st.session_state.get("language", "JP") == "EN" else "👆 ボタン入力"
        st.toggle(_tog2, key="acc_button_only")
    with col_acc3:
        _tog3 = "💬 Short replies" if st.session_state.get("language", "JP") == "EN" else "💬 短い返答"
        st.toggle(_tog3, key="acc_short_response")
    with col_acc4:
        _tog4 = "🔇 No audio" if st.session_state.get("language", "JP") == "EN" else "🔇 音声なし"
        st.toggle(_tog4, key="acc_no_audio")
    with col_acc5:
        _tog5 = "🚫 No reply needed" if st.session_state.get("language", "JP") == "EN" else "🚫 返事不要"
        st.toggle(_tog5, key="acc_no_talk")
        
    st.markdown('</div>', unsafe_allow_html=True)
    
    _quiet_note = "🌿 You don't have to speak." if st.session_state.get("language", "JP") == "EN" else "🌿 話さなくても大丈夫です"
    st.markdown(f"<p style='text-align: center; color: gray; font-size: 0.95rem; margin-top: 1.8rem; font-style: italic; letter-spacing: 0.05em;'>{_quiet_note}</p>", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────
# Section 2: 考えすぎている
# ──────────────────────────────────────────────────────────
if st.session_state.naomi_active_mode == "🧠 考えすぎている":
    st.markdown(tr("### 🧠 Gently organize what's on your mind", "### 🧠 心の中を少しずつ整理します"))
    st.info(tr("When your mind feels full, NAOMI helps you gently organize your feelings before a consultation.", "心の中がいっぱいな時、気持ちを少しずつ整理します。相談前に今の状態を言葉にするための補助です。"))
    
    with st.expander(tr("🌙 Read how this place thinks", "🌙 この場所の考え方を読む"), expanded=False):
        if is_large:
            st.info(tr("NAOMI quietly receives fatigue and tension, and adjusts the amount of words to your state.", "NAOMIは、疲れや緊張を静かに受け止め、言葉の量をあなたの状態に合わせます。"))
        else:
            st.info(tr("**A quiet way to receive you**\n\nNAOMI quietly receives burdens that are not fully in words yet, such as fatigue, tension, loneliness, and decision fatigue. It leaves room to speak or stay silent, without rushing you.", "**静かな受け止め方**\n\nNAOMIは、疲れ、緊張、孤独感、決断疲れのような、まだ言葉になりきらない負担を静かに受け止めます。話しても、黙っていてもよい余白を残しながら、急がせない形で支えます。"))
            
            st.markdown(f"""
        <div style="display:flex; justify-content:space-between; margin-bottom: 1rem;">
            <div style="flex:1; margin-right: 1rem; padding: 1rem; background-color:#f0f2f6; border-radius: 0.5rem; color:#333;">
                <b style="color:#000;">{tr("When there are too many words", "言葉が多い場所")}</b><br>
                {tr("・Immediate solutions<br>・Adds actions or tasks<br>・Encourages with correct logic", "・解決策をすぐ出す<br>・行動を増やす（タスクを渡す）<br>・正論で励ます")}
            </div>
            <div style="flex:1; padding: 1rem; background:linear-gradient(135deg,#eef5fc 0%,#e4eef8 100%); color:#2c3e50 !important; border: 1px solid rgba(106, 140, 175, 0.18); border-radius: 0.5rem;">
                <b style="color:#2c3e50 !important;">🌙 NAOMI</b><br>
                <span style="color:#2c3e50 !important;">{tr("・Receives first<br>・Lowers conversation pressure<br>・Receives the current state without rushing", "・まず受け止める<br>・会話圧を下げる<br>・今の状態を急がず受け止める")}</span>
            </div>
        </div>
            """, unsafe_allow_html=True)

    mental_title_color = "#2c3e50" if theme_mode == "light" else "#f1f5f9"
    mental_bg = "rgba(106, 140, 175, 0.045)" if theme_mode == "light" else "rgba(197, 168, 128, 0.045)"
    mental_border = "rgba(106, 140, 175, 0.14)" if theme_mode == "light" else "rgba(197, 168, 128, 0.14)"

    def mental_clean_val(v):
        if isinstance(v, list):
            return ", ".join([str(x) for x in v if x]) if v else ("(Not selected)" if st.session_state.get("language", "JP") == "EN" else "（未選択）")
        return str(v) if v else ("(Not selected)" if st.session_state.get("language", "JP") == "EN" else "（未選択）")

    def mental_toggle_group(title, state_key, options, columns=3, help_text=""):
        st.markdown(f"<div style='font-size: 1.05rem; font-weight: 500; margin-top: 1.4rem; margin-bottom: 0.3rem; color: {mental_title_color}; font-family: \"Noto Serif JP\", serif;'>{title}</div>", unsafe_allow_html=True)
        if help_text:
            st.markdown(f"<p style='font-size: 0.88rem; color: gray; margin-top: 0; margin-bottom: 0.8rem;'>{help_text}</p>", unsafe_allow_html=True)
        cols = st.columns(columns) if not is_large else st.columns(1)
        current_values = st.session_state[state_key]
        if not isinstance(current_values, list):
            current_values = [current_values] if current_values else []
        for idx, opt in enumerate(options):
            with cols[idx % columns if not is_large else 0]:
                is_selected = opt in current_values
                btn_type = "primary" if is_selected else "secondary"
                if st.button(opt, key=f"{state_key}_{idx}", type=btn_type, use_container_width=True):
                    if is_selected:
                        current_values.remove(opt)
                    else:
                        current_values.append(opt)
                    st.session_state[state_key] = current_values
                    keep_menu_top_once()
                    st.rerun()

    for key in ["mental_state", "mental_sleep", "mental_life", "mental_support", "mental_note", "mental_memo_output", "mental_feedback_msg"]:
        if key not in st.session_state:
            st.session_state[key] = [] if key in ["mental_state", "mental_sleep", "mental_life", "mental_support"] else None if key in ["mental_memo_output", "mental_feedback_msg"] else ""

    st.markdown(f"""
    <div style="background: {mental_bg}; border: 1px solid {mental_border}; border-radius: 20px; padding: 1.4rem 1.5rem; margin: 1.4rem 0 1.2rem 0;">
        <h4 style="margin-top:0; font-family:'Noto Serif JP', serif; font-size: 1.15rem; color: {accent_color}; margin-bottom: 0.5rem; letter-spacing: 0.05em;">{"🧠 Mental Relief Intake" if st.session_state.get("language", "JP") == "EN" else "🧠 心の整理"}</h4>
        <p style="font-size: 0.95rem; line-height: 1.7; margin-bottom: 0; font-weight: 300;">
            {"Gently organize anxiety, fatigue, and life impacts before your consultation.<br>" if st.session_state.get("language", "JP") == "EN" else "不安・疲労・考え込み・日常への影響を、相談前に自分でも分かりやすい形へ整えます。<br>"}
            <span style="font-size: 0.84rem; color: gray;">{"*Not a medical diagnosis. A calm helper to organize your thoughts." if st.session_state.get("language", "JP") == "EN" else "※病名や危険度を決めるものではありません。"}</span>
        </p>
    </div>
    """, unsafe_allow_html=True)

    mental_toggle_group(
        tr("Mental state", "心の状態"),
        "mental_state",
        ["Strong anxiety", "Feeling low", "No motivation", "Close to tears", "Irritable", "Lonely", "Worried about the future", "Do not want to meet people", "Cannot stop overthinking", "Mind cannot rest"] if st.session_state.get("language", "JP") == "EN" else ["不安が強い", "気分が沈む", "何もする気が起きない", "涙が出そう", "イライラする", "孤独感がある", "将来が不安", "人に会いたくない", "ずっと考え込んでしまう", "頭が休まらない"],
        columns=3,
        help_text=tr("Choose what feels closest right now.", "今の心に近いものを選べます。")
    )
    mental_toggle_group(
        tr("Sleep / fatigue", "睡眠・疲労"),
        "mental_sleep",
        ["Sleep does not restore me", "Anxiety gets stronger at night", "Mornings are hard", "Always tired", "Cannot concentrate"] if st.session_state.get("language", "JP") == "EN" else ["寝ても休まらない", "夜に不安が強くなる", "朝がつらい", "ずっと疲れている", "集中できない"],
        columns=3,
        help_text=tr("Choose what feels close about sleep or tiredness.", "眠りや疲れ方について、近いものを選べます。")
    )
    mental_toggle_group(
        tr("Impact on daily life", "日常への影響"),
        "mental_life",
        ["Housework feels hard", "Work or school feels heavy", "Cannot make decisions", "Talking with people is hard", "Do not want to go outside"] if st.session_state.get("language", "JP") == "EN" else ["家事がしんどい", "仕事・学校が重い", "判断ができない", "人と話すのがつらい", "外へ出たくない"],
        columns=3,
        help_text=tr("Choose what feels heavy in daily life.", "生活の中で重くなっているところを選べます。")
    )
    mental_toggle_group(
        tr("Support you want now", "今ほしい支え"),
        "mental_support",
        ["Just receive me", "Help me organize a little", "Help me calm down", "Tell someone", "Prepare before consultation"] if st.session_state.get("language", "JP") == "EN" else ["ただ受け止めてほしい", "少し整理したい", "落ち着きたい", "誰かに伝えたい", "相談前に整理したい"],
        columns=3,
        help_text=tr("NAOMI will adjust the response and memo direction.", "NAOMIの返し方やメモの方向を合わせます。")
    )

    mental_selected = st.session_state.mental_state + st.session_state.mental_sleep + st.session_state.mental_life + st.session_state.mental_support
    if mental_selected:
        support_text = tr("If needed, this can become a short note that is easy to share before consultation.", "必要なら、相談前に伝えやすい短いメモにできます。")
        if "ただ受け止めてほしい" in st.session_state.mental_support:
            support_text = "今は、答えを急がず受け止めることを優先します。"
        elif "落ち着きたい" in st.session_state.mental_support:
            support_text = "まずは落ち着くことを優先して、言葉は少なめにします。"
        elif "相談前に整理したい" in st.session_state.mental_support:
            support_text = "相談前に伝えやすい形へ、短く整えられます。"
        st.markdown(f"""
        <div style="background: {mental_bg}; border-left: 4px solid {accent_color}; border-radius: 14px; padding: 1.1rem 1.2rem; margin-top: 1.6rem; line-height: 1.8;">
            <b style="color: {accent_color};">NAOMI:</b><br>
            {tr("A few burdens may be overlapping inside right now.<br>You do not have to force a conclusion. What you placed here is enough.<br>", "今は、心の中にいくつかの負荷が重なっているのかもしれません。<br>無理に結論を出さなくて大丈夫です。ここに置けた分だけで十分です。<br>")}
            {support_text}
        </div>
        """, unsafe_allow_html=True)

    st.session_state.mental_note = st.text_input(
        tr("Additional note (*Optional. Leaving it blank is fine)", "補足 (※空欄のままでも大丈夫です)"),
        value=st.session_state.mental_note,
        placeholder=tr("e.g. Stronger at night, mornings are especially hard, hard to explain to others, etc.", "例：夜になると強くなる、朝が特につらい、人に説明しづらい など"),
        key="mental_note_input"
    )

    mental_action_cols = st.columns(3)
    with mental_action_cols[0]:
        if st.button(tr("📝 Create consultation note", "📝 相談前メモを作る"), key="make_mental_memo", use_container_width=True):
            st.session_state.mental_feedback_msg = tr("Organized into a short form that is easy to share before consultation.", "相談前に伝えやすい形へ、短く整えました。")
            if st.session_state.get("language", "JP") == "EN":
                st.session_state.mental_memo_output = f"""
### 🧠 Mental Relief Memo (NAOMI)
*This is not a diagnosis or risk assessment. It is a note to help communicate your current state before consultation.*

---

🌧️ **Mental state**
* {mental_clean_val(st.session_state.mental_state)}

🌙 **Sleep / fatigue**
* {mental_clean_val(st.session_state.mental_sleep)}

🏠 **Impact on daily life**
* {mental_clean_val(st.session_state.mental_life)}

🤝 **Support wanted now**
* {mental_clean_val(st.session_state.mental_support)}

💬 **Additional note**
* {st.session_state.mental_note if st.session_state.mental_note else "None (leaving blank is fine)"}
"""
            else:
                st.session_state.mental_memo_output = f"""
### 🧠 心の整理メモ (NAOMI)
*病名や危険度を決めるものではありません。相談前に今の状態を伝えやすくするためのメモです。*

---

🌧️ **心の状態**
* {mental_clean_val(st.session_state.mental_state)}

🌙 **睡眠・疲労**
* {mental_clean_val(st.session_state.mental_sleep)}

🏠 **日常への影響**
* {mental_clean_val(st.session_state.mental_life)}

🤝 **今ほしい支え**
* {mental_clean_val(st.session_state.mental_support)}

💬 **補足**
* {st.session_state.mental_note if st.session_state.mental_note else "特になし（空欄のままで問題ありません）"}
"""
            st.rerun()
    with mental_action_cols[1]:
        if st.button(tr("⏱️ Summarize briefly", "⏱️ 短くまとめる"), key="make_mental_short", use_container_width=True):
            st.session_state.mental_feedback_msg = tr("Made it short and easy to communicate.", "短く伝えられる形にしました。")
            if st.session_state.get("language", "JP") == "EN":
                st.session_state.mental_memo_output = f"""
### 🧠 Mental Relief Memo (Brief)
*Not a medical judgment. A short memo to make your state easier to share before consultation.*

* **Mental state**: {mental_clean_val(st.session_state.mental_state)}
* **Sleep / fatigue**: {mental_clean_val(st.session_state.mental_sleep)}
* **Impact on daily life**: {mental_clean_val(st.session_state.mental_life)}
* **Support wanted**: {mental_clean_val(st.session_state.mental_support)}
* **Additional note**: {st.session_state.mental_note if st.session_state.mental_note else "None"}
"""
            else:
                st.session_state.mental_memo_output = f"""
### 🧠 心の整理メモ (短縮版)
*医療判断ではありません。相談前に伝えやすくするための短いメモです。*

* **心の状態**: {mental_clean_val(st.session_state.mental_state)}
* **睡眠・疲労**: {mental_clean_val(st.session_state.mental_sleep)}
* **日常への影響**: {mental_clean_val(st.session_state.mental_life)}
* **ほしい支え**: {mental_clean_val(st.session_state.mental_support)}
* **補足**: {st.session_state.mental_note if st.session_state.mental_note else "特になし"}
"""
            st.rerun()
    with mental_action_cols[2]:
        if st.button(tr("🔄 Finish for today", "🔄 今日はここまでにする"), key="reset_mental_memo", use_container_width=True):
            reset_agent_session()
            for key in ["mental_state", "mental_sleep", "mental_life", "mental_support"]:
                st.session_state[key] = []
            st.session_state.mental_note = ""
            st.session_state.mental_memo_output = None
            st.session_state.mental_feedback_msg = tr("Finished for today. You can return at your own pace.", "ここまでにしました。あなたのペースで、また戻れます。")
            st.rerun()

    if st.session_state.mental_feedback_msg:
        st.markdown(f"""
        <div style="background: {mental_bg}; border-left: 4px solid {accent_color}; padding: 1.0rem; border-radius: 12px; margin-top: 1rem;">
            <span style="color: {accent_color}; font-size: 0.95rem; font-weight: 500;">
                {st.session_state.mental_feedback_msg}
            </span>
        </div>
        """, unsafe_allow_html=True)

    if st.session_state.mental_memo_output:
        with st.container():
            st.markdown(st.session_state.mental_memo_output)

    col_prof, col_ops = st.columns([1, 2])
    profiles = load_profiles()
    
    with col_prof:
        st.markdown(tr("#### 👤 Your basic settings", "#### 👤 あなたの基本設定"))
        user_ids = list(profiles.keys())
        selected_id = st.selectbox(tr("Select user", "利用者を選択"), user_ids, index=user_ids.index(st.session_state.current_user_id))
        st.session_state.current_user_id = selected_id
        profile = profiles[selected_id]
        
        with st.expander(tr("Adjust basic settings", "基本設定を整える")):
            new_name = st.text_input(tr("Name", "名前"), value=profile["display_name"])
            new_energy = st.slider(tr("Usual energy", "普段の元気度"), 0.0, 1.0, value=float(profile["usual_energy"]))
            new_len = st.selectbox(tr("Usual talk length", "普段の会話量"), ["short", "medium", "long"], index=["short", "medium", "long"].index(profile["usual_talk_length"]))
            new_notes = st.text_area(tr("Care notes", "ケアメモ"), value=profile["care_notes"])
            if st.button(tr("Update profile", "プロフィール更新")):
                update_profile(selected_id, {"display_name": new_name, "usual_energy": new_energy, "usual_talk_length": new_len, "care_notes": new_notes})
                st.success("更新しました")
                st.rerun()

    with col_ops:
        st.markdown(tr("#### 🌙 Choose today's pace", "#### 🌙 今のペースを選ぶ"))
        
        # 通常ケア用
        st.write(tr("**💬 Is there anything slightly concerning right now?**", "**💬 今、少し気になるものはありますか？**"))
        c_cols = st.columns(3)
        contexts = [
            (tr("A little heavy since morning", "朝から少し重い"), "morning_checkin"),
            (tr("Sleep did not restore me", "眠っても休まらない"), "sleep_check"),
            (tr("Feeling tense", "張りつめている感じ"), "fatigue_check")
        ]
        for i, (label, ctx) in enumerate(contexts):
            with c_cols[i]:
                if st.button(label, key=f"ctx_{ctx}", use_container_width=True):
                    profile = active_profile()
                    st.session_state.proactive_question = generate_checkin_question(ctx, profile)
                    st.session_state.last_result = None
                    st.rerun()

        st.write(tr("**🩺 When physical symptoms are central**", "**🩺 体の症状が中心の時**"))
        st.markdown(f"<p style='font-size: 0.9rem; color: gray; margin-top: -0.5rem;'>{tr('For fever, cough, stomach discomfort, and similar symptoms, you can move to health-state organization.', '熱・咳・胃腸のつらさなどは、健康状態の整理へ移れます。')}</p>", unsafe_allow_html=True)
        if not st.session_state.agent_core.intake.active:
            if st.button(tr("🩺 Go to health-state organization", "🩺 健康状態の整理へ"), type="primary", use_container_width=True):
                st.session_state.naomi_active_mode = "🩺 今の健康状態を一緒に整理しましょう"
                st.rerun()
        else:
            # 数字よりも、今のペースを伝えるための柔らかい進み具合
            itk = st.session_state.agent_core.intake
            total_steps = len(itk.INTAKE_TYPES[itk.intake_type])
            progress_ratio = itk.current_step / total_steps
            progress_text = "今の状態をゆっくり整理しています"
            if progress_ratio >= 0.66:
                progress_text = "少し整理できてきました"
            elif progress_ratio >= 0.33:
                progress_text = "無理のない範囲で大丈夫です"
            st.markdown("<br>", unsafe_allow_html=True)
            st.progress(progress_ratio, text=progress_text)
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button(tr("⏹️ Finish for today", "⏹️ 今日はここまでにする"), use_container_width=True):
                st.session_state.agent_core.intake.stop_intake()
                st.session_state.proactive_question = None
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        st.write(tr("**🫧 Choose what feels close right now**", "**🫧 今の状態に近いものを選ぶ**"))
        st.markdown(f"<p style='font-size: 0.9rem; color: gray; margin-top: -0.5rem;'>{tr('It is okay if talking is hard. Just press what feels close and leave it here.', '話しづらくても大丈夫です。近いものを押すだけで、今の感じをここに置けます。')}</p>", unsafe_allow_html=True)
        p3_cols1, p3_cols2 = st.columns(2)
        p3_inputs = [
            (tr("🌃 Sleepless night", "🌃 眠れない夜"), "明日も早いのに、考えごとが止まらなくて眠れない", "overthinking_sleep"),
            (tr("🛡️ Still tense after resting", "🛡️ 休んでも張りつめる"), "休んでるはずなのに、ずっと気を張っている感じがする", "always_tense"),
            (tr("📉 Small decisions feel heavy", "📉 小さな判断も重い"), "小さいことを決めるのも疲れてきた。何から考えればいいかわからない", "decision_fatigue"),
            (tr("🛑 Resting feels wrong", "🛑 休むのが申し訳ない"), "疲れてるのに、休んでいい気がしない", "cannot_rest"),
            (tr("👤 Somehow lonely", "👤 なんとなく寂しい"), "別に大きな問題があるわけじゃないけど、なんとなく一人で抱えてる感じがする", "silent_loneliness"),
        ]
        
        for i, (label, text, sid) in enumerate(p3_inputs):
            col = p3_cols1 if i % 2 == 0 else p3_cols2
            with col:
                if st.button(label, key=f"demo_p3_{sid}", use_container_width=True):
                    profile = active_profile()
                    result = naomi_process(text, profile)
                    st.session_state.last_result = (text, result)
                    st.session_state.proactive_question = None
                    st.rerun()

    # NAOMIからの最新の問いかけを表示
    current_q = st.session_state.proactive_question
    if st.session_state.last_result:
        _, res = st.session_state.last_result
        if res.intake_active:
            current_q = res.text
            
    if current_q:
        st.info(f"🗨️ **NAOMI:** {current_q}")

# ──────────────────────────────────────────────────────────
# Section 3: Accessibility & やさしい入力 (Phase 4-A)
# ──────────────────────────────────────────────────────────
if st.session_state.naomi_active_mode == "♿ 入力を楽にしたい":
    st.markdown(tr("### ♿ Accessibility support", "### ♿ 入力を楽にしたい"))
    
    # 大きな文字モードのチェックボックス
    st.checkbox(tr("Large text mode (larger text and simpler screen)", "大きな文字モード (文字を大きくし、画面をシンプルにします)"), key="large_font", on_change=sync_large_font_from_main)
    
    if is_large:
        st.markdown(f"""
        <div style="padding: 1rem 0; border-bottom: 1px solid #eee; margin-bottom: 1.5rem;">
            <p style="font-weight: bold; color: #5865f2;">{tr("You can communicate your current state just by pressing buttons.", "ボタンを押すだけで、今の状態を簡単に伝えられます。")}</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="padding: 1rem 0; border-bottom: 1px solid #eee; margin-bottom: 1.5rem;">
            <p>{tr("NAOMI does not rely only on voice or long text. Even if hearing, speaking, or typing is difficult, buttons and short choices can help communicate your current state.", "NAOMIは、声だけ・文字だけに頼りません。聞こえにくい人、話しづらい人、文字入力が難しい人でも、ボタンや短い選択で今の状態を伝えられるようにします。")}</p>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown(tr("##### 1. Press a button for your current body or mood", "##### 1. 今の体調や気分のボタンを押してください"))
    
    # 状態ボタンを配置
    btn_cols = st.columns(3) if not is_large else st.columns(1)
    
    status_buttons = [
        (tr("Hard", "つらい"), "tsurai"),
        (tr("Anxious", "不安"), "fuan"),
        (tr("Tired", "疲れた"), "tsukarete"),
        (tr("Cannot sleep", "眠れない"), "nemurenai"),
        (tr("Pain", "痛い"), "itai"),
        (tr("Short of breath", "息苦しい"), "ikigurushii"),
        (tr("Just listen", "ただ聞いて"), "kiite_hoshii"),
        (tr("Put into words", "言葉にしたい"), "seiri_shitai"),
        (tr("Make a family note", "家族に伝えるメモを作る"), "kazoku_memo")
    ]
    
    for idx, (label, key) in enumerate(status_buttons):
        col_idx = idx % 3 if not is_large else 0
        with btn_cols[col_idx]:
            if st.button(label, key=f"access_status_{key}", use_container_width=True):
                result = st.session_state.agent_core.process_accessibility_input(key, st.session_state.get("language", "JP"))
                st.session_state.last_result = (f"「{label}」ボタン入力", result)
                st.session_state.proactive_question = None
                st.rerun()
                
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(tr("##### 2. Choose the response style", "##### 2. 返ってくる言葉の形を選んでください"))
    
    load_buttons = [
        (tr("Reply with text", "文字で答える"), "moji"),
        (tr("Buttons only", "ボタンだけで答える"), "button_only"),
        (tr("Short replies", "返事は短く"), "short"),
        (tr("Do not want to talk now", "今は話したくない"), "no_talk"),
        (tr("Continue later", "あとで続けたい"), "later")
    ]
    
    btn_cols2 = st.columns(2) if not is_large else st.columns(1)
    for idx, (label, key) in enumerate(load_buttons):
        col_idx = idx % 2 if not is_large else 0
        with btn_cols2[col_idx]:
            if st.button(label, key=f"access_load_{key}", use_container_width=True):
                result = st.session_state.agent_core.process_accessibility_input(key, st.session_state.get("language", "JP"))
                st.session_state.last_result = (f"「{label}」ボタン入力", result)
                st.session_state.proactive_question = None
                st.rerun()

    # 安全表示
    if st.session_state.last_result:
        _, result = st.session_state.last_result
        if result.text:
            result_text_display = display_response_text(result.text, result.scenario_id)
            result_bg = "rgba(255, 255, 255, 0.55)" if theme_mode == "light" else "rgba(13, 20, 35, 0.45)"
            result_border = "rgba(106, 140, 175, 0.14)" if theme_mode == "light" else "rgba(197, 168, 128, 0.14)"
            result_title = "#6a8caf" if theme_mode == "light" else "#c5a880"
            st.markdown(f"""
            <div style="background: {result_bg}; border: 1px solid {result_border}; border-radius: 20px; padding: 1.4rem 1.5rem; margin: 1.4rem 0 1.2rem 0; box-shadow: 0 10px 30px rgba(0,0,0,0.02);">
                <h5 style="margin:0 0 0.7rem 0; font-family:'Noto Serif JP', serif; color: {result_title}; font-size: 1.05rem; letter-spacing: 0.05em;">🌙 NAOMI</h5>
                <p style="font-size: 1.02rem; line-height: 1.8; margin: 0;">{result_text_display}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="background-color: #fcf8e3; border-left: 5px solid #f0ad4e; padding: 1rem; border-radius: 0.5rem;">
        <h6 style="color: #8a6d3b; margin: 0 0 0.5rem 0; font-weight: bold;">{tr("⚠️ Safety guidance", "⚠️ 安全のためのご案内")}</h6>
        <ul style="color: #8a6d3b; margin: 0; padding-left: 1.2rem; font-size: 0.9rem;">
            <li>{tr("NAOMI is not a doctor or specialist and does <b>not provide medical diagnosis</b>.", "NAOMIは医師や専門家ではありません。医療的な<b>診断は行いません</b>。")}</li>
            <li>{tr("Any observation is only a guide and does <b>not determine</b> specific symptoms.", "状態の見立ては目安であり、特定の症状を<b>断定しません</b>。")}</li>
            <li>{tr("This system is intended as support to make your condition and feelings <b>easier to communicate</b>.", "本システムは、ご自身の体調や気持ちを<b>伝えやすくする補助</b>を目的としています。")}</li>
            <li>{tr("If poor health or shortness of breath continues, or if it may be urgent, please consider consulting a medical institution promptly.", "体調不良や息苦しさなどが続く場合、または緊急を要する場合は、速やかに専門医療機関へのご相談を検討してください。")}</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────
# Section 4: 🩺 今の健康状態を一緒に整理しましょう
# ──────────────────────────────────────────────────────────
if st.session_state.naomi_active_mode == "🩺 今の健康状態を一緒に整理しましょう":
    health_section_title = "🩺 Let's gently organize your symptoms" if st.session_state.get("language", "JP") == "EN" else "🩺 今の健康状態を一緒に整理しましょう"
    st.markdown(f"### {health_section_title}")
    st.markdown(f'<div class="naomi-return-row">{start_screen_link()}</div>', unsafe_allow_html=True)
    
    # はじめの案内
    guide_bg_clinic = "rgba(106, 140, 175, 0.05)" if theme_mode == "light" else "rgba(197, 168, 128, 0.05)"
    guide_border_clinic = "rgba(106, 140, 175, 0.15)" if theme_mode == "light" else "rgba(197, 168, 128, 0.15)"
    
    st.markdown(f"""
    <div style="background: {guide_bg_clinic}; border: 1px solid {guide_border_clinic}; border-radius: 20px; padding: 1.8rem; margin-bottom: 2rem;">
        <h4 style="margin-top:0; font-family:'Noto Serif JP', serif; font-size: 1.25rem; color: {accent_color}; margin-bottom: 0.8rem; letter-spacing: 0.05em;">{"🩺 Organizing symptoms to help you communicate" if st.session_state.get("language", "JP") == "EN" else "🩺 体調や症状を、伝えやすく整理します"}</h4>
        <p style="font-size: 1.0rem; line-height: 1.7; margin-bottom: 0; font-weight: 300;">
            {"Organize concerns like fever, cough, and fatigue so they are easy to share.<br>" if st.session_state.get("language", "JP") == "EN" else "熱・咳・胃腸のつらさ・息苦しさなどを、病院・家族へ伝えやすく整理します。<br>"}
            <span style="font-size: 0.85rem; color: gray;">{"*Not a medical diagnosis. A calm assistant to help organize and communicate your symptoms." if st.session_state.get("language", "JP") == "EN" else "※これは医療判断ではありません。現在の健康状態を整理し、必要なら相談先へ伝えやすくするための補助です。"}</span>
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ヘルパー関数定義
    def get_clean_val(v):
        if isinstance(v, list):
            return ", ".join([str(x) for x in v if x]) if v else ("(Not selected)" if st.session_state.get("language", "JP") == "EN" else "（未選択）")
        return str(v) if v else ("(Not selected)" if st.session_state.get("language", "JP") == "EN" else "（未選択）")
        
    def has_val(v, target):
        if isinstance(v, list):
            return target in v
        return v == target

    def toggle_group(title, state_key, options, columns=3, help_text=""):
        st.markdown(f"<div style='font-size: 1.05rem; font-weight: 500; margin-top: 1.5rem; margin-bottom: 0.3rem; color: {title_color}; font-family: \"Noto Serif JP\", serif;'>{title}</div>", unsafe_allow_html=True)
        if help_text:
            st.markdown(f"<p style='font-size: 0.88rem; color: gray; margin-top: 0; margin-bottom: 0.8rem;'>{help_text}</p>", unsafe_allow_html=True)
        cols = st.columns(columns) if not is_large else st.columns(1)
        current_values = st.session_state[state_key]
        if not isinstance(current_values, list):
            current_values = [current_values] if current_values else []
        for idx, opt in enumerate(options):
            with cols[idx % columns if not is_large else 0]:
                is_selected = opt in current_values
                btn_type = "primary" if is_selected else "secondary"
                if st.button(opt, key=f"{state_key}_{idx}", type=btn_type, use_container_width=True):
                    if is_selected:
                        current_values.remove(opt)
                    else:
                        current_values.append(opt)
                    st.session_state[state_key] = current_values
                    keep_menu_top_once()
                    st.rerun()

    def choice_group(title, state_key, options, columns=3, help_text=""):
        st.markdown(f"<div style='font-size: 1.05rem; font-weight: 500; margin-top: 1.5rem; margin-bottom: 0.3rem; color: {title_color}; font-family: \"Noto Serif JP\", serif;'>{title}</div>", unsafe_allow_html=True)
        if help_text:
            st.markdown(f"<p style='font-size: 0.88rem; color: gray; margin-top: 0; margin-bottom: 0.8rem;'>{help_text}</p>", unsafe_allow_html=True)
        cols = st.columns(columns) if not is_large else st.columns(1)
        current_value = st.session_state[state_key]
        for idx, opt in enumerate(options):
            with cols[idx % columns if not is_large else 0]:
                btn_type = "primary" if current_value == opt else "secondary"
                if st.button(opt, key=f"{state_key}_{idx}", type=btn_type, use_container_width=True):
                    st.session_state[state_key] = "" if current_value == opt else opt
                    keep_menu_top_once()
                    st.rerun()

    # セッションステート初期化
    list_keys = ["clinic_main_worry", "clinic_location", "clinic_life_impact", "clinic_support_need"]
    for key in ["clinic_main_worry", "clinic_location", "clinic_life_impact", "clinic_support_need", "clinic_when", "clinic_severity", "clinic_anxiety", "clinic_ask", "clinic_memo_output", "clinic_active_btn", "clinic_feedback_msg"]:
        if key not in st.session_state:
            if key in list_keys:
                st.session_state[key] = []
            elif key in ["clinic_active_btn", "clinic_feedback_msg"]:
                st.session_state[key] = None
            else:
                st.session_state[key] = "" if key != "clinic_memo_output" else None

    # 緊急度表示
    is_emergency = (
        has_val(st.session_state.clinic_main_worry, "息苦しい") or has_val(st.session_state.clinic_main_worry, "Short of breath") or
        has_val(st.session_state.clinic_main_worry, "動悸") or has_val(st.session_state.clinic_main_worry, "Palpitations") or
        has_val(st.session_state.clinic_life_impact, "動くのがしんどい") or has_val(st.session_state.clinic_life_impact, "Hard to move") or
        st.session_state.clinic_when in ["急に悪くなった", "Sudden worsening"] or
        st.session_state.clinic_severity in ["かなりしんどい", "Severe / Exhausted"]
    )
    if is_emergency:
        st.markdown(f"""
        <div style="background-color: rgba(220, 53, 69, 0.08); border-left: 5px solid #d9534f; padding: 1.2rem; border-radius: 0.5rem; margin-bottom: 2rem;">
            <b style="color: #d9534f; font-size: 1.05rem;">{"⚠️ Urgent Notice" if st.session_state.get("language", "JP") == "EN" else "⚠️ 緊急のお知らせ"}</b><br>
            <span style="color: {accent_color}; font-size: 0.95rem; font-weight: 500;">
                {"If you are in severe pain or experiencing sudden changes, please don't wait. Tell nearby staff immediately." if st.session_state.get("language", "JP") == "EN" else "つらさが強い、または急な変化がある場合は、待たずに近くのスタッフへ早めに伝えてください。"}
            </span>
        </div>
        """, unsafe_allow_html=True)

    # 会話の流れに見えるよう、番号よりも問いかけを前面に出す
    title_color = "#2c3e50" if theme_mode == "light" else "#f1f5f9"

    toggle_group(
        "Current Symptoms" if st.session_state.get("language", "JP") == "EN" else "現在の症状",
        "clinic_main_worry",
        ["Feverish", "Headache", "Cough", "Sore throat", "Runny nose", "Stomach ache", "Nausea", "Diarrhea", "Dizzy", "Palpitations", "Short of breath", "Loss of appetite"] if st.session_state.get("language", "JP") == "EN" else ["熱っぽい", "頭痛", "咳", "喉が痛い", "鼻水", "胃が痛い", "吐き気", "下痢", "めまい", "動悸", "息苦しい", "食欲がない"],
        columns=4,
        help_text="Choose as many symptoms as you feel." if st.session_state.get("language", "JP") == "EN" else "近い症状をいくつでも選べます。"
    )
    choice_group(
        "Duration / When" if st.session_state.get("language", "JP") == "EN" else "症状の期間",
        "clinic_when",
        ["From today", "A few days ago", "1 week or more", "Happens repeatedly"] if st.session_state.get("language", "JP") == "EN" else ["今日から", "数日前から", "1週間以上", "繰り返している"],
        columns=4,
        help_text="Just your best estimate is fine." if st.session_state.get("language", "JP") == "EN" else "分かる範囲で大丈夫です。"
    )
    choice_group(
        "Severity / Intensity" if st.session_state.get("language", "JP") == "EN" else "強さ",
        "clinic_severity",
        ["Mild discomfort", "Affects daily life", "Severe / Exhausted"] if st.session_state.get("language", "JP") == "EN" else ["少しつらい", "日常に影響がある", "かなりしんどい"],
        columns=3,
        help_text="Select how strong your symptoms feel." if st.session_state.get("language", "JP") == "EN" else "今のつらさに近いものを選べます。"
    )
    toggle_group(
        "Impact on Daily Life" if st.session_state.get("language", "JP") == "EN" else "生活への影響",
        "clinic_life_impact",
        ["Hard to eat", "Hard to move", "Cannot sleep", "Hard to work/study"] if st.session_state.get("language", "JP") == "EN" else ["食事が難しい", "動くのがしんどい", "眠れない", "仕事・学校が難しい"],
        columns=2,
        help_text="Select what has been difficult in your day." if st.session_state.get("language", "JP") == "EN" else "生活の中で困っていることを選べます。"
    )
    toggle_group(
        "Who to Share With" if st.session_state.get("language", "JP") == "EN" else "相談相手",
        "clinic_support_need",
        ["Share with family", "Share with doctor", "Share with caregivers"] if st.session_state.get("language", "JP") == "EN" else ["家族へ伝えたい", "医師へ伝えたい", "介護・支援者へ共有したい"],
        columns=3,
        help_text="Select who you want this organized memo for." if st.session_state.get("language", "JP") == "EN" else "誰に伝えるためのメモにしたいかを選べます。"
    )

    selected_items = (
        st.session_state.clinic_main_worry
        + st.session_state.clinic_life_impact
        + st.session_state.clinic_support_need
    )
    if selected_items:
        support_text = ("If needed, we can compile a neat memo to share with your consultants." if st.session_state.get("language", "JP") == "EN" else "必要なら、このまま相談先に伝えやすいメモにまとめます。")
        if st.session_state.clinic_severity == "かなりしんどい" or is_emergency:
            support_text = ("If your symptoms are severe, please do not hesitate to contact caregivers or medical institutions early." if st.session_state.get("language", "JP") == "EN" else "つらさが強い時は、無理に様子を見続けず、早めに身近な人や医療機関へ伝えてください。")
        st.markdown(f"""
        <div style="background: {guide_bg_clinic}; border-left: 4px solid {accent_color}; border-radius: 14px; padding: 1.1rem 1.2rem; margin-top: 1.6rem; line-height: 1.8;">
            <b style="color: {accent_color};">NAOMI:</b><br>
            {"Thank you, sharing what you've selected so far is already a great help.<br>" if st.session_state.get("language", "JP") == "EN" else "今の体調について、ここまで選べた分だけでも十分です。<br>"}
            {"Although it is not a medical diagnosis, it serves as a valuable tool for sharing your condition.<br>" if st.session_state.get("language", "JP") == "EN" else "医療判断ではありませんが、伝える材料としては役に立ちます。<br>"}
            {support_text}
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"<br><div style='font-size: 1.05rem; font-weight: 500; margin-top: 1.5rem; margin-bottom: 0.8rem; color: {title_color}; font-family: \"Noto Serif JP\", serif;'>{'Feel free to write any additional details below' if st.session_state.get('language', 'JP') == 'EN' else '補足したいことがあれば、短く書けます'}</div>", unsafe_allow_html=True)
    st.session_state.clinic_ask = st.text_input(
        "Additional details (*Optional. A short sentence is perfectly fine.)" if st.session_state.get("language", "JP") == "EN" else "補足 (※空欄のままでも大丈夫です。長い文章を書かなくても大丈夫です。)",
        value=st.session_state.clinic_ask,
        placeholder="e.g. Fever spikes in evening, severe headache in morning, etc." if st.session_state.get("language", "JP") == "EN" else "例：朝が特につらい、夜になると不安が強くなる、誰かに伝えたい など"
    )

    # 8. アクションボタン
    st.markdown("<br>", unsafe_allow_html=True)
    
    # フィードバック案内（優しい誘導メッセージ）の表示
    if st.session_state.clinic_feedback_msg:
        feedback_bg = "rgba(106, 140, 175, 0.08)" if theme_mode == "light" else "rgba(197, 168, 128, 0.08)"
        st.markdown(f"""
        <div style="background: {feedback_bg}; border-left: 4px solid {accent_color}; padding: 1.0rem; border-radius: 12px; margin-bottom: 1.5rem;">
            <span style="color: {accent_color}; font-size: 0.95rem; font-weight: 500;">
                {st.session_state.clinic_feedback_msg}
            </span>
        </div>
        """, unsafe_allow_html=True)
        
    act_cols = st.columns(3)
    active_btn = st.session_state.clinic_active_btn
    
    with act_cols[0]:
        memo_btn_type = "primary" if active_btn == "memo" else "secondary"
        if st.button("📝 Create Shareable Memo" if st.session_state.get("language", "JP") == "EN" else "📝 伝えるメモを作る", type=memo_btn_type, use_container_width=True, key="make_memo_btn"):
            st.session_state.clinic_active_btn = "memo"
            st.session_state.clinic_feedback_msg = ("Your conditions have been organized into a shareable memo. It's gently presented below." if st.session_state.get("language", "JP") == "EN" else "今の状態を、伝えやすいメモに整えました。下にそっと残しています。")
            
            # メモの作成処理
            staff_tips = []
            if has_val(st.session_state.clinic_support_need, "家族へ伝えたい") or has_val(st.session_state.clinic_support_need, "Share with family"):
                staff_tips.append("Please briefly check symptoms, duration, and life impacts for easier sharing with family." if st.session_state.get("language", "JP") == "EN" else "家族へ共有しやすいよう、症状・期間・生活への影響を短く確認してください。")
            if has_val(st.session_state.clinic_support_need, "医師へ伝えたい") or has_val(st.session_state.clinic_support_need, "Share with doctor"):
                staff_tips.append("For sharing with a doctor, please concisely summarize symptoms, duration, severity, and life impacts." if st.session_state.get("language", "JP") == "EN" else "医師へ伝える前提で、症状の期間・強さ・生活への影響を簡潔に確認してください。")
            if has_val(st.session_state.clinic_support_need, "介護・支援者へ共有したい") or has_val(st.session_state.clinic_support_need, "Share with caregivers"):
                staff_tips.append("For sharing with caregivers, please check effects on daily actions, meals, and sleep." if st.session_state.get("language", "JP") == "EN" else "介護・支援者へ共有する前提で、日常動作や食事・睡眠への影響を確認してください。")
            if is_emergency:
                staff_tips.append("If there is short of breath, palpitations, difficulty moving, or severe pain, please consider seeking medical help early." if st.session_state.get("language", "JP") == "EN" else "息苦しさ・動悸・動きづらさ・強いしんどさがある場合は、早めの相談や受診を検討してください。")
            if not staff_tips:
                staff_tips.append("Please briefly check symptoms at the user's own pace." if st.session_state.get("language", "JP") == "EN" else "本人のペースに合わせ、症状を短く確認してください。")
                
            memo = f"""
### {"🩺 Health State Memo (NAOMI)" if st.session_state.get("language", "JP") == "EN" else "🩺 健康状態メモ (NAOMI)"}
*{"This memo is not a medical diagnosis, but a quiet assistant to help you communicate your current symptoms. Necessary judgments should be made by doctors or specialists." if st.session_state.get("language", "JP") == "EN" else "本メモは医療判断ではなく、現在の健康状態を伝えやすくするための補助です。必要な判断は医師や専門職が行います。"}*

---

🩺 **{"Current Symptoms" if st.session_state.get("language", "JP") == "EN" else "現在の症状"}**
* {get_clean_val(st.session_state.clinic_main_worry)}

⏱️ **{"Duration / When" if st.session_state.get("language", "JP") == "EN" else "症状の期間"}**
* {st.session_state.clinic_when if st.session_state.clinic_when else ("(Not selected)" if st.session_state.get("language", "JP") == "EN" else "（未選択）")}

⚡ **{"Severity / Intensity" if st.session_state.get("language", "JP") == "EN" else "強さ"}**
* {st.session_state.clinic_severity if st.session_state.clinic_severity else ("(Not selected)" if st.session_state.get("language", "JP") == "EN" else "（未選択）")}

🏠 **{"Impact on Daily Life" if st.session_state.get("language", "JP") == "EN" else "生活への影響"}**
* {get_clean_val(st.session_state.clinic_life_impact)}

🤝 **{"Who to Share With" if st.session_state.get("language", "JP") == "EN" else "相談相手"}**
* {get_clean_val(st.session_state.clinic_support_need)}

💬 **{"Additional Details" if st.session_state.get("language", "JP") == "EN" else "補足"}**
* {st.session_state.clinic_ask if st.session_state.clinic_ask else ("None (leaving blank is perfectly fine)" if st.session_state.get("language", "JP") == "EN" else "特になし（空欄のままで問題ありません）")}

🌿 **{"Things to Consider When Sharing" if st.session_state.get("language", "JP") == "EN" else "伝える時に配慮してほしいこと"}**
* {" ".join(staff_tips)}
"""
            st.session_state.clinic_memo_output = memo
            st.rerun()

    with act_cols[1]:
        short_btn_type = "primary" if active_btn == "short" else "secondary"
        if st.button("⏱️ Summarize Briefly" if st.session_state.get("language", "JP") == "EN" else "⏱️ 短くまとめる", type=short_btn_type, use_container_width=True, key="make_short_btn"):
            st.session_state.clinic_active_btn = "short"
            st.session_state.clinic_feedback_msg = ("Your conditions have been summarized briefly. It's gently presented below." if st.session_state.get("language", "JP") == "EN" else "短く伝えられる形に整えました。下にそっと残しています。")
            
            # 短縮版メモの作成処理
            memo = f"""
### {"🩺 Health State Memo (Brief)" if st.session_state.get("language", "JP") == "EN" else "🩺 健康状態メモ (短縮版)"}
*{"Not a medical diagnosis. A brief memo to help you communicate." if st.session_state.get("language", "JP") == "EN" else "医療判断ではありません。相談先へ伝えやすくするための短いメモです。"}*

* **{"Current Symptoms" if st.session_state.get("language", "JP") == "EN" else "現在の症状"}**: {get_clean_val(st.session_state.clinic_main_worry)}
* **{"Duration / When" if st.session_state.get("language", "JP") == "EN" else "期間"}**: {st.session_state.clinic_when if st.session_state.clinic_when else ("(Not selected)" if st.session_state.get("language", "JP") == "EN" else "（未選択）")}
* **{"Severity / Intensity" if st.session_state.get("language", "JP") == "EN" else "強さ"}**: {st.session_state.clinic_severity if st.session_state.clinic_severity else ("(Not selected)" if st.session_state.get("language", "JP") == "EN" else "（未選択）")}
* **{"Impact on Daily Life" if st.session_state.get("language", "JP") == "EN" else "生活への影響"}**: {get_clean_val(st.session_state.clinic_life_impact)}
* **{"Who to Share With" if st.session_state.get("language", "JP") == "EN" else "相談相手"}**: {get_clean_val(st.session_state.clinic_support_need)}
* **{"Additional Details" if st.session_state.get("language", "JP") == "EN" else "補足"}**: {st.session_state.clinic_ask if st.session_state.clinic_ask else ("None" if st.session_state.get("language", "JP") == "EN" else "特になし")}
"""
            st.session_state.clinic_memo_output = memo
            st.rerun()

    with act_cols[2]:
        reset_btn_type = "primary" if active_btn == "reset" else "secondary"
        if st.button("🔄 Finish for Today" if st.session_state.get("language", "JP") == "EN" else "🔄 今日はここまでにする", type=reset_btn_type, use_container_width=True, key="reset_btn"):
            reset_agent_session()
            st.session_state.clinic_active_btn = "reset"
            st.session_state.clinic_feedback_msg = ("Finished for today. You can return anytime at your own pace." if st.session_state.get("language", "JP") == "EN" else "ここまでにしました。あなたのペースで、またいつでも戻れます。")
            
            # 初期化
            for key in ["clinic_main_worry", "clinic_location", "clinic_life_impact", "clinic_support_need", "clinic_when", "clinic_severity", "clinic_anxiety", "clinic_ask", "clinic_memo_output"]:
                if key in ["clinic_main_worry", "clinic_location", "clinic_life_impact", "clinic_support_need"]:
                    st.session_state[key] = []
                else:
                    st.session_state[key] = "" if key != "clinic_memo_output" else None
            st.rerun()

    # 出力結果のレンダリング
    if st.session_state.clinic_memo_output:
        with st.container():
            st.markdown(st.session_state.clinic_memo_output)

    # アクセシビリティ将来構想
    st.markdown(f"""
    <div style="background: rgba(106, 140, 175, 0.03); border: 1px dashed rgba(106, 140, 175, 0.15); border-radius: 16px; padding: 1.2rem; margin-top: 2.5rem; font-size: 0.88rem; color: gray;">
        📢 <b>{"Voice Guidance Mode (Future Expansion): Scheduled to Support" if st.session_state.get("language", "JP") == "EN" else "音声案内モード（将来拡張構想）：対応予定"}</b><br>
        ♿ <i>{"We aim to create an environment where anyone—even those who find it hard to read small text or write sentences—can intuitively and smoothly communicate." if st.session_state.get("language", "JP") == "EN" else "文字が読みづらい方や書くのがつらい方でも、直感的かつ円滑に「伝える」ことができる環境を目指しています。"}</i>
    </div>
    """, unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────
# 共通処理: 入力と結果表示
# ──────────────────────────────────────────────────────────
suppress_bottom_chat = st.session_state.pop("suppress_bottom_chat_once", False)
show_bottom_chat = (
    not suppress_bottom_chat
    and st.session_state.naomi_screen != "state"
)

if show_bottom_chat:
    # ── 静かな待機中インジケーター ──
    dot_color = "#6a8caf" if theme_mode == "light" else "#c5a880"
    st.markdown(f"""
    <div style="display: flex; justify-content: center; margin-bottom: 1.5rem; margin-top: 1rem;">
        <div class="waiting-indicator">
            <div class="waiting-dot" style="background-color: {dot_color};"></div>
            <span>{tr("NAOMI is quietly waiting for you", "NAOMIは静かにあなたを待っています")}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

user_input = st.chat_input(
    tr("Example: I have been busy with work and feel tired", "例：最近仕事が忙しくて疲れています")
) if show_bottom_chat else None

if user_input:
    try:
        profile = active_profile()
        result = naomi_process(user_input, profile)
        st.session_state.last_result = (user_input, result)
        # 手動クリックによるプロアクティブ質問は、一度返答があればクリアする
        st.session_state.proactive_question = None
        st.rerun()
    except Exception as e:
        st.error(f"Agent実行中にエラーが発生しました: {e}")

# --- 結果表示セクション ---
if st.session_state.last_result and not suppress_bottom_chat:
    input_text, result = st.session_state.last_result
    profile = active_profile()

    visible_phase_label = phase_label(result)
    if visible_phase_label:
        phase_bg = "rgba(106, 140, 175, 0.08)" if theme_mode == "light" else "rgba(197, 168, 128, 0.10)"
        phase_border = "rgba(106, 140, 175, 0.18)" if theme_mode == "light" else "rgba(197, 168, 128, 0.18)"
        phase_color = "#4f6f90" if theme_mode == "light" else "#c5a880"
        st.markdown(f"""
        <div style="display:inline-block; background:{phase_bg}; border:1px solid {phase_border}; color:{phase_color}; border-radius:999px; padding:0.35rem 0.75rem; font-size:0.85rem; margin-bottom:0.8rem;">
            {visible_phase_label}
        </div>
        """, unsafe_allow_html=True)
        naomi_help("mode")
        with st.expander("Debug", expanded=False):
            internal_state = getattr(result, "asurada_state", {}) or {}
            core_state = getattr(st.session_state.agent_core, "asurada", {}) or {}
            red_flag_state = getattr(result, "red_flag", {}) or {}
            st.write({
                "phase": internal_state.get("phase"),
                "probe_count": core_state.get("probe_count", 0),
                "red_flag.triggered": red_flag_state.get("triggered", False),
            })
            if st.button("状態をリセット", key="reset_asurada_state_bottom"):
                reset_agent_session()
                st.rerun()

    # 1. レッドフラグ (段階的表示)
    if result.red_flags:
        for flag in result.red_flags:
            if flag['level'] == 'high':
                st.error(f"⚠️ **要注意の兆候**: {flag['label']} の様子が見受けられます。必要に応じて専門機関へのご相談もご検討ください。")
            elif flag['level'] == 'medium':
                st.warning(f"🔔 **確認事項**: {flag['label']} の傾向があります。")
            else:
                st.info(f"💡 **メモ**: {flag['label']}")
        st.markdown("<br>", unsafe_allow_html=True)
        
    # 1.3 NAOMIの返答 (やさしいガラスカード)
    if result.text:
        result_text_display = display_response_text(result.text, result.scenario_id)
        bg_color = "rgba(255, 255, 255, 0.55)" if theme_mode == "light" else "rgba(13, 20, 35, 0.45)"
        border_color = "rgba(255, 255, 255, 0.5)" if theme_mode == "light" else "rgba(197, 168, 128, 0.15)"
        title_color = "#6a8caf" if theme_mode == "light" else "#c5a880"
        st.markdown(f"""
        <div style="background: {bg_color}; padding: 1.8rem; border-radius: 20px; border: 1px solid {border_color}; margin-bottom: 2rem; box-shadow: 0 10px 30px rgba(0,0,0,0.02); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);">
            <h5 style="margin-top:0; font-family:'Noto Serif JP', serif; color: {title_color}; font-size: 1.15rem; margin-bottom: 0.8rem; letter-spacing: 0.05em;">🌙 NAOMI</h5>
            <p style="font-size: 1.05rem; line-height: 1.8; margin-bottom: 0;">{result_text_display}</p>
        </div>
        """, unsafe_allow_html=True)
        show_hackathon_runtime_debug(result)

    # 1.4 受け止め方の違い（表向きは静かな表現にする）
    stress_val = round(result.state.stress * 100)
    energy_val = round(result.state.energy * 100)
    pressure_map = {"VERY_LOW": tr("Very gentle", "極めて穏やか"), "LOW": tr("Gentle", "穏やか"), "MEDIUM": tr("Standard", "標準"), "HIGH": tr("Interactive", "対話的")}
    p_label = pressure_map.get(result.pressure_level, tr("Gentle", "穏やか"))
    accent_color = "#6a8caf" if theme_mode == "light" else "#c5a880"
    
    c1_bg = "rgba(220, 53, 69, 0.03)" if theme_mode == 'light' else "rgba(220, 53, 69, 0.07)"
    c1_text_color = '#d9534f' if theme_mode == 'light' else '#ef6a6a'
    c1_span_color = '#2c3e50' if theme_mode == 'light' else '#cbd5e1'
    
    c2_bg = "linear-gradient(135deg, rgba(106, 140, 175, 0.12) 0%, rgba(106, 140, 175, 0.04) 100%)" if theme_mode == 'light' else "linear-gradient(135deg, rgba(197, 168, 128, 0.12) 0%, rgba(13, 20, 35, 0.5) 100%)"
    c2_text_color = '#2c3e50' if theme_mode == 'light' else '#e2e8f0'
    
    st.markdown(f"<h3 style='font-family: \"Noto Serif JP\", serif; text-align: center; margin-top: 2rem; margin-bottom: 0.5rem; font-weight: 300; letter-spacing: 0.05em;'>{tr('🌙 How NAOMI Receives You', '🌙 NAOMIの受け止め方')}</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center; color:gray; font-size: 0.95rem; margin-bottom: 2rem; font-weight: 300;'>{tr('Rather than rushing to answers, NAOMI first reduces words to match your current state.', '急いで答えを出すよりも、まずは今の状態に合わせて言葉を減らします。')}</p>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    generic_text = GENERIC_AI_RESPONSES.get(result.scenario_id, GENERIC_AI_RESPONSES["default"])
    if st.session_state.get("language", "JP") == "EN":
        generic_text = GENERIC_AI_RESPONSES_EN.get(result.scenario_id, GENERIC_AI_RESPONSES_EN["default"])
    
    with c1:
        st.markdown(f"""
        <div style="background-color: {c1_bg}; padding: 1.8rem; border-radius: 24px; border: 1px solid rgba(220, 53, 69, 0.15); min-height: 220px; box-shadow: 0 4px 15px rgba(0,0,0,0.01);">
            <b style="color: {c1_text_color}; font-size: 1.05rem; font-family: 'Noto Serif JP', serif; font-weight: 500;">{tr("When there are too many words", "言葉が多すぎる時")}</b><br><br>
            <span style="color: {c1_span_color}; font-size: 0.95rem; line-height: 1.8; font-weight: 300;">“{generic_text}”</span><br><br>
            <span style="font-size: 0.8rem; color: gray; font-weight: 300; line-height: 1.4; display: block; border-top: 1px solid rgba(220, 53, 69, 0.08); padding-top: 0.8rem; margin-top: 0.8rem;">
                {tr("When you feel worn down, correct advice or extra tasks can feel heavy.", "少ししんどい時は、正論やタスクが重く感じられることがあります。")}
            </span>
        </div>
        """, unsafe_allow_html=True)
        
    with c2:
        st.markdown(f"""
        <div style="background: {c2_bg}; color: {c2_text_color}; padding: 1.8rem; border-radius: 24px; border: 1px solid {border_color}; min-height: 220px; box-shadow: 0 4px 20px rgba(0,0,0,0.01);">
            <b style="color: {accent_color}; font-size: 1.05rem; font-family: 'Noto Serif JP', serif; font-weight: 500;">🌙 NAOMI</b><br><br>
            <span style="font-size: 0.95rem; line-height: 1.8; font-weight: 300;">“{result_text_display}”</span><br><br>
            <span style="font-size: 0.8rem; color: {accent_color}; font-weight: 300; line-height: 1.4; display: block; border-top: 1px solid rgba(197, 168, 128, 0.15); padding-top: 0.8rem; margin-top: 0.8rem;">
                🌿 <b>{tr("Quiet receiving", "静かな受け止め")}</b>: {tr("Keeps words minimal so you can organize your current state without being rushed.", "言葉の量を控えめにし、今の状態を急がず整理できるようにします。")}
            </span>
        </div>
        """, unsafe_allow_html=True)

    # 1.5 今のメモ（完了後の上部ガラスカード）
    if result.intake_summary and not result.staff_note:
        box_bg = "rgba(255, 255, 255, 0.65)" if theme_mode == "light" else "rgba(13, 20, 35, 0.45)"
        box_border = "rgba(255, 255, 255, 0.5)" if theme_mode == "light" else "rgba(197, 168, 128, 0.12)"
        summary_title_color = "#2c3e50" if theme_mode == "light" else "#f1f5f9"
        naomi_help("intake_summary")
        st.markdown(f"""
        <div style="background-color: {box_bg}; padding: 2rem; border-radius: 24px; border: 1px solid {box_border}; margin-bottom: 2.5rem; box-shadow: 0 10px 30px rgba(0,0,0,0.02); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);">
            <h4 style="color: {summary_title_color}; margin-top: 0; font-family: 'Noto Serif JP', serif; letter-spacing: 0.05em;">{tr("📝 Current Note", "📝 今のメモ")}</h4>
            <pre style="background: transparent; border: none; color: inherit; font-family: inherit; font-size: 1rem; margin: 0; padding: 0; white-space: pre-wrap; line-height: 1.8;">
{display_note_text(result.intake_summary)}
            </pre>
        </div>
        """, unsafe_allow_html=True)

    # 2. 巨大磨りガラス 2カラムレイアウト (左: メモ / 右: 今の様子)
    st.markdown(f"<h3 style='font-family: \"Noto Serif JP\", serif; text-align: center; margin-top: 3.5rem; margin-bottom: 2.5rem; font-weight: 300; letter-spacing: 0.05em;'>{tr('🩹 Quietly Saved Note', '🩹 そっと残したメモ')}</h3>", unsafe_allow_html=True)
    
    col_out_left, col_out_right = st.columns([7, 5])
    
    with col_out_left:
        # 左側：巨大磨りガラス調のメモ
        card_bg = "rgba(255, 255, 255, 0.45)" if theme_mode == "light" else "rgba(13, 20, 35, 0.35)"
        card_border = "rgba(255, 255, 255, 0.5)" if theme_mode == "light" else "rgba(197, 168, 128, 0.12)"
        title_c = "#2c3e50" if theme_mode == "light" else "#c5a880"
        text_c = "#34495e" if theme_mode == "light" else "#e2e8f0"
        naomi_help("staff_note")
        
        # staff_note を美しくパース
        notes_html = ""
        raw_note = display_note_text(result.staff_note or result.handoff_note or "")
        if raw_note:
            lines = [line.strip() for line in raw_note.split("\n") if line.strip()]
            for line in lines:
                if line.startswith("-") or line.startswith("・") or line.startswith("*"):
                    line_content = line.lstrip("-・* ").strip()
                    notes_html += f"<li style='margin-bottom: 1.2rem; font-family: \"Noto Serif JP\", serif; line-height: 2.0; font-weight: 300;'>{line_content}</li>"
                else:
                    notes_html += f"<p style='margin-bottom: 1.2rem; font-family: \"Noto Serif JP\", serif; line-height: 2.0; font-weight: 300;'>{line}</p>"
        else:
            empty_note_text = tr("Based on today's conversation, NAOMI will gently organize this into an easier-to-share form.", "本日の対話をもとに、伝えやすい形へそっと整えます。")
            notes_html = f"<p style='font-style: italic; color: gray; font-weight: 300;'>{empty_note_text}</p>"

        st.markdown(f"""
        <div style="background: {card_bg}; border: 1px solid {card_border}; border-radius: 28px; padding: 2.5rem; box-shadow: 0 20px 50px rgba(0,0,0,0.02); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);">
            <h4 style="color: {title_c}; margin-top:0; font-family: 'Noto Serif JP', serif; letter-spacing: 0.08em; border-bottom: 1px solid {card_border}; padding-bottom: 1rem; margin-bottom: 1.5rem; font-weight: 400;">
                {tr("📝 Current Note", "📝 今のメモ")}
            </h4>
            <div style="background: rgba(106, 140, 175, 0.05) if theme_mode=='light' else rgba(197, 168, 128, 0.05); padding: 0.8rem 1.2rem; border-radius: 12px; margin-bottom: 1.8rem; font-size: 0.85rem; color: {accent_color}; line-height: 1.5; border: 1px solid {card_border};">
                💡 <b>{tr("Memo for you and supporters:", "本人や支援者のためのメモ：")}</b><br>
                {tr("This is not a medical diagnosis. It is a short summary to help you or supporters review the current state and share it gently when consultation is needed.", "医療的な診断を行うものではありません。本人や支援者が「今の状態」を見つめ直し、必要な相談の場へそっと渡しやすくするための短いサマリーです。")}
            </div>
            <div style="color: {text_c}; font-size: 1.05rem;">
                <ul style="padding-left: 1.2rem; margin: 0; list-style-type: square;">
                    {notes_html}
                </ul>
            </div>
            <p style='font-size:0.8rem; color:gray; margin-top:3.5rem; margin-bottom:0; font-style: italic; text-align: right; font-weight: 300;'>
                {tr("*This is not a medical diagnosis. It is a note to make your current state easier to communicate.", "※これは医療診断ではなく、今の状態を伝えやすくするためのメモです。")}
            </p>
        </div>
        """, unsafe_allow_html=True)

    with col_out_right:
        # 右側：静かな様子カード
        box_bg = "rgba(255, 255, 255, 0.45)" if theme_mode == "light" else "rgba(13, 20, 35, 0.35)"
        box_border = "rgba(255, 255, 255, 0.5)" if theme_mode == "light" else "rgba(197, 168, 128, 0.12)"
        title_c = "#2c3e50" if theme_mode == "light" else "#c5a880"
        state_help_cols = st.columns(3)
        with state_help_cols[0]:
            naomi_help("human_state")
        with state_help_cols[1]:
            naomi_help("pressure")
        with state_help_cols[2]:
            naomi_help("mode")
        
        stress_val = round(result.state.stress * 100)
        energy_val = round(result.state.energy * 100)
        listening_need = tr("Priority", "優先") if result.strategy.listening_mode else tr("Normal", "通常")
        
        # 会話圧
        pressure_map = {"VERY_LOW": tr("Very gentle", "極めて穏やか"), "LOW": tr("Gentle", "穏やか"), "MEDIUM": tr("Standard", "標準"), "HIGH": tr("Interactive", "対話的")}
        p_label = pressure_map.get(result.pressure_level, tr("Gentle", "穏やか"))
        
        # 返答形式の連動
        talk_style = tr("Gentle short replies", "やさしい短い返答") if st.session_state.get("acc_short_response", False) else tr("Careful listening", "丁寧な傾聴")
        stress_label = tr("High", "高い") if stress_val > 60 else tr("Calm", "穏やか")
        energy_label = tr("Enough", "十分") if energy_val > 50 else tr("Low", "低下気味")
        
        # カラー・背景の事前評価
        bar_bg = "rgba(0,0,0,0.05)" if theme_mode == "light" else "rgba(255,255,255,0.05)"
        
        st.markdown(f"""
        <div style="background: {box_bg}; border: 1px solid {box_border}; border-radius: 28px; padding: 2.2rem; box-shadow: 0 15px 35px rgba(0,0,0,0.02); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); height: 100%;">
            <h4 style="color: {title_c}; margin-top:0; font-family: 'Noto Serif JP', serif; letter-spacing: 0.08em; padding-bottom: 1rem; border-bottom: 1px solid {box_border}; margin-bottom: 2rem; font-weight: 400;">
                {tr("🧠 Current State", "🧠 今の様子")}
            </h4>
            <div style="margin-bottom: 2rem;">
                <p style="margin:0 0 0.4rem 0; font-size: 0.85rem; color: gray; letter-spacing: 0.05em;">{tr("Mental tension", "こころの張りつめ度")}</p>
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size: 1.2rem; font-family: 'Noto Serif JP', serif; font-weight: 300;">{stress_val} %</span>
                    <span style="font-size: 0.85rem; color: {accent_color}; font-weight: 300;">{stress_label}</span>
                </div>
                <div style="height: 3px; background: {bar_bg}; border-radius: 2px; margin-top: 0.5rem;">
                    <div style="height: 100%; width: {stress_val}%; background: {accent_color}; border-radius: 2px;"></div>
                </div>
            </div>
            <div style="margin-bottom: 2rem;">
                <p style="margin:0 0 0.4rem 0; font-size: 0.85rem; color: gray; letter-spacing: 0.05em;">{tr("Remaining energy", "残りのエネルギー")}</p>
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size: 1.2rem; font-family: 'Noto Serif JP', serif; font-weight: 300;">{energy_val} %</span>
                    <span style="font-size: 0.85rem; color: gray; font-weight: 300;">{energy_label}</span>
                </div>
                <div style="height: 3px; background: {bar_bg}; border-radius: 2px; margin-top: 0.5rem;">
                    <div style="height: 100%; width: {energy_val}%; background: {accent_color}; border-radius: 2px;"></div>
                </div>
            </div>
            <div style="margin-bottom: 1.8rem; border-top: 1px solid {box_border}; padding-top: 1.5rem;">
                <p style="margin:0 0 0.3rem 0; font-size: 0.85rem; color: gray; letter-spacing: 0.05em;">{tr("Care from the space", "空間からの配慮")}</p>
                <p style="font-size: 1.25rem; font-family: 'Noto Serif JP', serif; margin:0; font-weight: 300;">🌿 {p_label}</p>
            </div>
            <div style="margin-bottom: 1rem;">
                <p style="margin:0 0 0.3rem 0; font-size: 0.85rem; color: gray; letter-spacing: 0.05em;">{tr("Response approach for you", "あなたへの応対方針")}</p>
                <p style="font-size: 1.0rem; font-family: 'Noto Serif JP', serif; margin:0; color: gray; font-weight: 300; line-height: 1.6;">・{talk_style}</p>
                <p style="font-size: 1.0rem; font-family: 'Noto Serif JP', serif; margin:0; color: gray; font-weight: 300; line-height: 1.6;">・{tr("Listening", "傾聴")} {listening_need}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ── コンテンツが下部チャットバーに隠れないための十分な Padding ──
if st.session_state.naomi_screen != "state":
    st.markdown("<div style='margin-bottom: 15rem;'></div>", unsafe_allow_html=True)

# ── アプリ最下部の安全表示（免責事項フッター） ──
footer_html = dedent(f"""
<div style="margin-top: 5rem; padding: 2rem 1.5rem; border-top: 1px solid rgba(106, 140, 175, 0.15); text-align: center; font-size: 0.85rem; color: gray; line-height: 1.6; max-width: 900px; margin-left: auto; margin-right: auto;">
    <p style="margin: 0 0 0.5rem 0; font-weight: bold; color: gray;">{t("disclaimer_title")}</p>
    <div style="margin: 0; font-weight: 300;">{t("disclaimer_text")}</div>
</div>
""").strip().replace("\n", " ")
st.markdown(footer_html, unsafe_allow_html=True)
