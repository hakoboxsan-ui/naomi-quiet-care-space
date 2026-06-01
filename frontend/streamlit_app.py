import streamlit as st
import sys
import os
import importlib
from dataclasses import asdict
from textwrap import dedent

# プロジェクトルートをPYTHONPATHに追加
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import agent.mode_selector as mode_selector_module
import agent.core as core_module
importlib.reload(mode_selector_module)
importlib.reload(core_module)
from agent.core import NaomiAgentCore
from agent.personal_baseline import load_profiles, get_profile, update_profile
from agent.proactive_care import generate_checkin_question

# ── 一般的なAIの固定返答（比較デモ用） ──
GENERIC_AI_RESPONSES = {
    "tired": "大変お疲れ様ですね。疲労回復のためには以下の3点をお勧めします：1. 十分な睡眠の確保、2. 軽いストレッチ、3. 明日のタスクの優先順位付け。まずはこれらを実践してみてください。",
    "anxiety": "不安を感じているのですね。不安を解消するための科学的な方法は深呼吸とマインドフルネス瞑想です。まずは5分間、呼吸にのみ集中してみることから始めましょう。",
    "lonely": "孤独感を感じているとのこと、コミュニティへの参加や、友人への連絡をお勧めします。誰かと話すことで孤独感は軽減されることが統計的に証明されています。",
    "exhausted_advice": "限界を感じつつも解決策を求めているのですね。現状を打破するためのステップは以下の通りです：1. タスクの優先順位付け、2. 不要な仕事の切り捨て、3. 周囲への相談。すぐに実行に移しましょう。",
    "overthinking_sleep": "睡眠不足は健康に悪影響を及ぼします。寝る前にスマホを控え、深呼吸し、頭の中のタスクを紙に書き出してリセットしましょう。",
    "always_tense": "緊張状態が続いているのですね。自律神経を整えるために、温かいお茶を飲み、軽いストレッチやヨガを行うことをお勧めします。",
    "decision_fatigue": "決断疲れ（Decision Fatigue）の症状です。重要な決断は午前中に行い、服装や食事など日常の選択をルーティン化して減らしましょう。",
    "cannot_rest": "完璧主義の傾向が見られます。休むことも重要なタスクであると認識し、スケジュールに『何もしない時間』を強制的に組み込んでください。",
    "silent_loneliness": "そのように感じる時は、趣味のコミュニティに参加したり、新しい習い事を始めることで、新しい人間関係を構築してみましょう。",
    "default": "ご相談ありがとうございます。あなたの状況を分析しました。最善の解決策は以下の通りです。まずこれを行い、次にこれを行ってください..."
}

# ── Page Config ──
st.set_page_config(
    page_title="NAOMI - 静かな場所",
    page_icon="🌙",
    layout="wide"
)

# ── Session State ──
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
    st.session_state.naomi_screen = "home"
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
        st.session_state.naomi_active_mode = ""
    st.session_state.naomi_screen = "state"

# ── 多言語テキスト辞書 (最小英語モード) ──
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
        "badge_3": "理屈を急がない",
        "guide_title": "💡 迷ったときの使い方",
        "guide_desc": "気になるカードを押すだけで大丈夫です。NAOMIが言葉の量や進み方を控えめにしながら、今の感じをそっと受け止めます。",
        "guide_step_title": "👉 迷ったときの目安：",
        "guide_step_1": "疲れている時は、まず 「🌙 少し疲れている」 を選んでください。",
        "guide_step_2": "考えが止まらない時は 「🧠 考えすぎている」 が近いかもしれません。",
        "guide_step_3": "体調や症状を伝えたい時は、「🩺 今の健康状態を一緒に整理しましょう」 を選んでください。",
        "today_feel": "今日は、どんな感じですか？",
        "today_feel_sub": "無理に話さなくても大丈夫です。",
        "disclaimer_title": "🛡️ 安全に関するご案内と免責事項",
        "disclaimer_text": "NAOMIは医療診断を行うサービスではなく、病名の特定や治療指示といった<b>医療診断行為は一切行いません</b>。<br>また、個人の心身の状態を完全に<b>断定するものでもありません</b>。<br>NAOMIは、ご本人や支援者が現在の状態を見つめ、必要な相談や専門機関へつなぎやすくするための静かな補助を目的としています。<br>強い精神的苦痛や緊急を要する心身の不調がある場合は、直ちに専門の医療機関や公的な相談窓口へ直接ご相談ください。",
        "card_1_title": "🌙 少し疲れている",
        "card_1_desc": "言葉にする余裕がない時も、<br>選ぶだけで始められます。",
        "card_2_title": "🧠 不安",
        "card_2_desc": "心の中がいっぱいな時、<br>急がず少しずつ整理します。",
        "card_3_title": "👂 聞こえ方",
        "card_3_desc": "音声なし・文字中心など、<br>受け取り方を楽にします。",
        "card_4_title": "🌿 整理したい",
        "card_4_desc": "体調や気持ちを、<br>相談前メモに整えます。",
        "btn_selected": "✓ 選択中",
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
        "why_naomi_long": "It is perfectly okay if you cannot speak well or run out of mental energy today. NAOMI will reduce response length and listen gently without forcing logic.<br>Not a medical diagnosis. A calm assistant to help communicate your current state.",
        "badge_1": "No talking required",
        "badge_2": "Click only is OK",
        "badge_3": "No logic forced",
        "guide_title": "💡 How to Use",
        "guide_desc": "Just click any card that matches your feelings today. NAOMI will adapt its response length and listen gently.",
        "guide_step_title": "👉 Quick Guideline:",
        "guide_step_1": "If you are tired, try selecting \"🌙 Slightly tired\" first.",
        "guide_step_2": "If your mind won't stop racing, \"🧠 Anxious & restless\" might fit best.",
        "guide_step_3": "To share physical symptoms, choose \"🩺 Let's gently organize your symptoms\".",
        "today_feel": "How are you feeling today?",
        "today_feel_sub": "You do not have to push yourself to speak.",
        "disclaimer_title": "🛡️ Safety Guidelines & Medical Disclaimer",
        "disclaimer_text": "NAOMI does not provide medical diagnosis, treatment instructions, or clinical assessment.<br>It does not definitively determine your physical or mental health status.<br>NAOMI is designed as a calm assistant to help you observe your state and communicate with caregivers or professionals.<br>If you are experiencing severe distress or a life-threatening emergency, please contact local emergency services immediately.",
        "card_1_title": "🌙 Slightly tired",
        "card_1_desc": "Start just by clicking,<br>even when words are hard to find.",
        "card_2_title": "🧠 Anxious & restless",
        "card_2_desc": "Gently organize thoughts<br>when your mind is overwhelmed.",
        "card_3_title": "👂 Accessibility",
        "card_3_desc": "Adjust font size and volume<br>for a stress-free experience.",
        "card_4_title": "🌿 Let's organize",
        "card_4_desc": "Prepare structured notes<br>for your next consultation.",
        "btn_selected": "✓ Selected",
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

def active_profile():
    profile = dict(get_profile(st.session_state.current_user_id))
    profile["language"] = st.session_state.get("language", "JP")
    return profile

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

COMMON_RESPONSE_EN = {
    "とてもお辛いですね。今は無理に言葉にしなくて大丈夫です。返事も、できる時だけで大丈夫です。": "That sounds very painful. You do not have to force words right now. Reply only when you can.",
    "今は、何も整えようとしなくて大丈夫です。ここに置いておくだけで大丈夫です。": "You do not have to organize anything right now. It is enough to leave it here.",
    "しんどい中で教えてくださってありがとうございます。返事は急がなくて大丈夫です。": "Thank you for telling me while things feel hard. There is no need to hurry your reply.",
    "かなりお辛い状態なのですね。今は、言葉を少なくして、静かに受け止めます。": "This sounds very hard. I will keep my words few and receive it quietly.",
    "たくさん抱えてきたのですね。まずは、今の重さをここに置いて大丈夫です。": "You have been carrying a lot. For now, it is okay to place that weight here.",
    "本当にがんばってきたのですね。急がなくて大丈夫です。少しずつでいいです。": "You have really been trying hard. There is no need to rush. Little by little is enough.",
    "どんな気持ちも、そのまま受け止めます。無理に説明しなくて大丈夫です。": "Whatever you feel, I will receive it as it is. You do not have to explain it forcefully.",
    "少しだけ、一緒に見ていきましょう。今いちばん重いものを、ひとつだけ置けそうですか。": "Let's look at this together, just a little. Could you place just the heaviest thing here?",
    "焦らなくて大丈夫です。言葉になるところから、少しずつで構いません。": "No need to rush. Start only where words are possible, little by little.",
    "頭の中がいっぱいなのですね。まずはひとつだけ、ゆっくりほどいていきましょう。": "Your mind feels full. Let's gently untangle just one thing first.",
    "夜は、考えが大きく感じられることがあります。今は返事をしなくても大丈夫です。": "At night, thoughts can feel larger. You do not have to reply right now.",
    "今日が少しでも静かに終わりますように。言葉は少なくて大丈夫です。": "I hope today can end a little more quietly. Few words are enough.",
    "眠れない時も、焦らなくて大丈夫です。ただ静かにここにいてください。": "Even when you cannot sleep, you do not have to rush. Just stay here quietly.",
    "今日もここまで来たのですね。まずは、そのままで大丈夫です。": "You made it this far today. For now, you are okay as you are.",
    "焦らなくて大丈夫です。あなたのペースを、ここではそのまま大切にします。": "No need to rush. Your pace is respected here exactly as it is.",
    "そうなんですね。話したいところだけ、ぽつぽつで大丈夫です。": "I see. It is okay to share only the parts you want to, piece by piece.",
}

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
    if st.session_state.get("language", "JP") != "EN" or not text:
        return text
    replacements = {
        "■ 状態整理メモ (Staff Note)": "■ Care handoff note (Staff Note)",
        "・現在の主訴": "・Current concern",
        "明日のことを考えると不安で落ち着かない": "Thinking about tomorrow makes me anxious and unsettled",
        "どうしたらいいか教えてほしいけど、正直もう疲れてる": "I want advice on what to do, but honestly I am already exhausted",
        "最近ちょっと疲れてて…": "I have been feeling a little tired lately...",
        "なんか一人でいる感じがして寂しい": "I feel like I am alone somehow, and it feels lonely",
        "明日も早いのに、考えごとが止まらなくて眠れない": "I have to wake up early tomorrow, but my thoughts will not stop and I cannot sleep",
        "休んでるはずなのに、ずっと気を張っている感じがする": "Even though I should be resting, I still feel tense all the time",
        "小さいことを決めるのも疲れてきた。何から考えればいいかわからない": "Even small decisions feel tiring. I do not know where to start",
        "疲れてるのに、休んでいい気がしない": "I am tired, but I do not feel like I am allowed to rest",
        "別に大きな問題があるわけじゃないけど、なんとなく一人で抱えてる感じがする": "There is no big problem, but I somehow feel like I am carrying it alone",
        "・不安/疲労の傾向": "・Estimated anxiety/fatigue trend",
        "・睡眠状態": "・Sleep condition",
        "・会話圧": "・Conversation pressure",
        "・提案": "・Suggested approach",
        "特筆事項なし": "No specific issues detected",
        "少しお疲れ、あるいはご負担を感じている可能性": "May be experiencing fatigue or emotional distress",
        "落ち着いている様子": "Seems calm and stable",
        "いつもより少し活気が低下している様子が見受けられます": "Energy appears slightly lower than usual",
        "いつもより少し活動的、あるいは気が張っている様子があります": "May be slightly more active or tense than usual",
        "いつもに比べて、言葉少なめでいらっしゃるようです": "Using fewer words than usual",
        "いつもよりご自身のお気持ちを多く話されている様子があります": "Sharing more feelings than usual",
        "普段はよく休まれているようですが、本日は少しお疲れ・眠気がある様子です": "Usually rests well, but today may be tired or sleepy",
        "継続して睡眠不足や眠気の傾向が見受けられます": "Ongoing lack of sleep or sleepiness may be present",
        "少しご負担や気疲れが重なっている様子がうかがえます": "Some emotional burden or fatigue may be building up",
        "低圧応対推奨": "Low-pressure response recommended",
        "極めて低い（推奨）": "Very low (recommended)",
        "低い（推奨）": "Low (recommended)",
        "標準": "Standard",
        "高い": "High",
        "※このメモはAIとの対話からの推定であり、医療的な判断や断定を行うものではありません。": "*This note is an estimate from the conversation and is not a medical judgment or diagnosis.",
    }
    out = text
    for jp, en in replacements.items():
        out = out.replace(jp, en)
    return out

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

# --- アクセシビリティキー同期 (Step 3: 重複回避 & 相互同期) ---
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

# ── デザインシステム CSS 注入 (Step 1: Calm Light / Quiet Night) ──
theme_mode = st.session_state.get("theme_mode", "light")
is_large = st.session_state.get("large_font", False)

# Google Fonts インポート
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
</style>
""", unsafe_allow_html=True)

# 共通フォントサイズ設定
base_font_size = "1.35rem" if is_large else "0.95rem"
h1_font_size = "2.8rem" if is_large else "1.9rem"
h2_font_size = "2.2rem" if is_large else "1.5rem"
h3_font_size = "1.8rem" if is_large else "1.25rem"
h4_font_size = "1.55rem" if is_large else "1.1rem"

if theme_mode == "light":
    # Calm Light Mode
    st.markdown(f"""
    <style>
    /* Streamlitデフォルトヘッダー・フッター非表示 (SaaS感の完全排除) */
    header[data-testid="stHeader"], footer {{
        visibility: hidden !important;
        height: 0px !important;
    }}
    
    /* アプリ全体背景 & フォント */
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
    
    /* コンテナの余白調整（縦長の静かな余白空間） */
    .block-container {{
        padding-top: 2.0rem !important;
        padding-bottom: 5rem !important;
        max-width: 950px !important;
    }}
    
    /* 横線の非表示・透過化 */
    hr {{
        border: none !important;
        height: 1px !important;
        background: linear-gradient(to right, transparent, rgba(106, 140, 175, 0.08), transparent) !important;
        margin: 2.5rem 0 !important;
    }}
    
    /* ガラスカード調 (stAlert, widgets) - ボーダー極細・シャドウ超ソフト化 */
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
    
    /* ボタンのQuiet Luxury化 */
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
    /* 選択済み (primary) ボタンの上質なQuiet Luxury化 (沈む背景・輪郭強調・身体感覚グロー) */
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
    
    /* 入力エリア */
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
    
    /* タブのスタイリング（SaaS管理画面感を極限まで消去） */
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
    
    /* 静かな選択カードの Calm Light スタイル */
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
    
    /* Selectbox (Theme Selector) のSaaS感排除 */
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
    
    /* Accessibility Mode コンテナ */
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
    
    /* 絵文字の半透過ノイズ低減 */
    .emoji-dim {{
        opacity: 0.6 !important;
        display: inline-block;
        margin-right: 0.2rem;
        transition: opacity 0.3s ease;
    }}
    .emoji-dim:hover {{
        opacity: 1.0 !important;
    }}
    
    /* スマホ幅での余白・崩れ防止レスポンシブクエリ (Night) */
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
        /* モバイル表示時の文字サイズと余白調整 */
        .stApp h1 {{ font-size: 1.5rem !important; }}
        .stApp h2 {{ font-size: 1.3rem !important; }}
        .stApp h3 {{ font-size: 1.1rem !important; }}
    }}
    
    /* スマホ幅での余白・崩れ防止レスポンシブクエリ */
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
        /* モバイル表示時の文字サイズと余白調整 */
        .stApp h1 {{ font-size: 1.5rem !important; }}
        .stApp h2 {{ font-size: 1.3rem !important; }}
        .stApp h3 {{ font-size: 1.1rem !important; }}
    }}

    /* 静かな待機中アニメーション定義 */
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
    /* Streamlitデフォルトヘッダー・フッター非表示 (SaaS感の完全排除) */
    header[data-testid="stHeader"], footer {{
        visibility: hidden !important;
        height: 0px !important;
    }}
    
    /* アプリ全体背景 & フォント (深夜のディープな空間演出) */
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
    
    /* コンテナの余白調整（縦長の静かな余白空間） */
    .block-container {{
        padding-top: 2.0rem !important;
        padding-bottom: 5rem !important;
        max-width: 950px !important;
    }}
    
    /* 横線の非表示・透過化 */
    hr {{
        border: none !important;
        height: 1px !important;
        background: linear-gradient(to right, transparent, rgba(197, 168, 128, 0.04), transparent) !important;
        margin: 2.5rem 0 !important;
    }}
    
    /* ガラスカード調 (stAlert, widgets) - ボーダー極細・シャドウ超ソフト化 */
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
    
    /* ボタンのQuiet Luxury化 (ゴールド・アンバー調) */
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
    /* 選択済み (primary) ボタンの上質なQuiet Luxury化 (沈む背景・輪郭強調・身体感覚グロー) */
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
    
    /* 入力エリア */
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
    
    /* タブのスタイリング（SaaS管理画面感を極限まで消去） */
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
    
    /* 静かな選択カードの Quiet Night スタイル */
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
    
    /* Selectbox (Theme Selector) のSaaS感排除 */
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
    
    /* Accessibility Mode コンテナ */
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
    
    /* 絵文字の半透過ノイズ低減 */
    .emoji-dim {{
        opacity: 0.5 !important;
        display: inline-block;
        margin-right: 0.2rem;
        transition: opacity 0.3s ease;
    }}
    .emoji-dim:hover {{
        opacity: 0.9 !important;
    }}

    /* 静かな待機中アニメーション定義 */
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

# ── モバイル時の初見導線を少しだけ前に出す共通調整 ──
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
    min-height: 680px;
    margin-top: 1.5rem;
    padding: clamp(2rem, 5vw, 4.8rem);
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
    margin: 5rem auto 0;
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
    margin-bottom: 3rem;
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
.naomi-home-action-card {
    min-height: 150px;
    padding: 1.7rem 1.4rem;
    border-radius: 28px;
    border: 1px solid rgba(255, 255, 255, 0.74);
    background: rgba(255, 255, 255, 0.50);
    box-shadow: 0 20px 48px rgba(106, 140, 175, 0.08), inset 0 1px 0 rgba(255,255,255,0.82);
    text-align: center;
    backdrop-filter: blur(20px) saturate(135%);
    -webkit-backdrop-filter: blur(20px) saturate(135%);
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
@media (max-width: 780px) {
    .naomi-home-shell {
        padding: 1.4rem;
        min-height: 0;
    }
    .naomi-home-still-life {
        opacity: 0.28;
        top: 6rem;
        right: 0.5rem;
    }
    .naomi-home-copy {
        margin-top: 2.8rem;
    }
    .naomi-home-actions {
        grid-template-columns: 1fr;
    }
}
</style>
""", unsafe_allow_html=True)

# ── Header & Mode Switcher ──
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
    lang_options = {"JP": "🇯🇵 日本語", "EN": "🇺🇸 English"}
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
    with st.popover("⚙", use_container_width=False):
        detail_result = st.session_state.last_result[1] if st.session_state.last_result else None
        has_detail = detail_result is not None

        st.markdown(tr("### 📊 Internal State & Response", "### 📊 内部の状態と応対"))
        if not has_detail:
            st.caption(tr("NAOMI has not responded yet. Detailed state will appear here after a response.", "まだNAOMIの返答はありません。返答後に、ここへ詳しい状態が入ります。"))

        col_state, col_strategy, col_mode = st.columns(3)

        with col_state:
            st.markdown(tr("##### 🧠 State Estimate", "##### 🧠 状態の見立て"))
            if has_detail:
                st.json({
                    tr("stress", "ストレス"): round(detail_result.state.stress, 2),
                    tr("loneliness", "孤独感"): round(detail_result.state.loneliness, 2),
                    "energy": round(detail_result.state.energy, 2),
                    "need_listening": round(detail_result.state.need_listening, 2),
                    "need_advice": round(detail_result.state.need_advice, 2),
                })
            else:
                st.markdown(tr("Not available", "未取得"))

        with col_strategy:
            st.markdown(tr("##### 🎯 Response Strategy", "##### 🎯 応対方針"))
            if has_detail:
                a_mode_map = {"WAIT": tr("Wait a little", "少し待つ"), "ON": tr("Only when needed", "必要な時だけ"), "OFF": tr("Hold back", "控える")}
                st.markdown(f"**{tr('Advice', '助言')}:** {a_mode_map.get(detail_result.strategy.advice_mode, detail_result.strategy.advice_mode)}")
                st.write(f"👂 **{tr('Listening stance', '聴く姿勢')}:** {tr('Priority', '優先') if detail_result.strategy.listening_mode else tr('Normal', '通常')}")
                st.write(f"🎭 **{tr('Tone', 'トーン')}:** `{detail_result.strategy.emotional_tone}`")
            else:
                st.markdown(tr("Not available", "未取得"))
                st.write(tr("Shown after NAOMI responds", "NAOMIの返答後に表示"))

        with col_mode:
            st.markdown(tr("##### 🔁 Response Intensity", "##### 🔁 応対の強さ"))
            if has_detail:
                mode_ja_map = {"Listening": tr("Listening", "聴く姿勢"), "Listening First": tr("Receive first", "まず受け止める"), "Advice": tr("Suggest only when needed", "必要な時だけ提案"), "Companion": tr("Quiet companion", "静かにそばにいる")}
                st.markdown(f"**{tr('Response', '応対')}:** `{mode_ja_map.get(detail_result.mode.value, detail_result.mode.value)}`")
                pressure_map = {"VERY_LOW": ("🫧", 0.1, tr("Very low", "極めて低い")), "LOW": ("🌙", 0.3, tr("Low", "低い")), "MEDIUM": ("⚠️", 0.6, tr("Standard", "標準")), "HIGH": ("🚨", 0.9, tr("High", "高い"))}
                p_icon, p_val, p_label = pressure_map.get(detail_result.pressure_level, ("⚪", 0.5, tr("Unknown", "不明")))
                st.markdown(f"**{tr('Amount of words', '言葉の量')}**: {p_icon} {p_label}")
                st.progress(p_val)
            else:
                st.markdown(tr("Not available", "未取得"))
                st.progress(0)

        if has_detail:
            st.divider()
            st.markdown(tr("### ⚖️ Word Amount Reference", "### ⚖️ 言葉の量の参考"))
            st.markdown(f"<p style='color:gray;'>{tr('Even with the same message, there is a difference between rushing and waiting gently.', '同じ言葉でも、急がせる返し方と、少し待つ返し方があります。')}</p>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            generic_text = GENERIC_AI_RESPONSES.get(detail_result.scenario_id, GENERIC_AI_RESPONSES["default"])
            if st.session_state.get("language", "JP") == "EN":
                generic_text = GENERIC_AI_RESPONSES_EN.get(detail_result.scenario_id, GENERIC_AI_RESPONSES_EN["default"])
            with c1:
                st.markdown(f'<div style="background-color:#f0f2f6;padding:1.5rem;border-radius:0.5rem;border-left:5px solid #9ca3af;"><b style="color:#333;">{tr("When there are too many words", "言葉が多すぎる時")}</b><br><br><span style="color:#333;">{generic_text}</span></div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);color:#e0e0e0;padding:1.5rem;border-radius:0.5rem;border-left:5px solid #7c83ff;"><b>🌙 NAOMI</b><br><br>{display_response_text(detail_result.text, detail_result.scenario_id)}</div>', unsafe_allow_html=True)

            if detail_result.facs_hint:
                st.divider()
                st.markdown("##### 🔮 FACS Hint")
                st.code("  ".join(detail_result.facs_hint), language=None)
        else:
            st.divider()
            st.markdown(tr("### ⚖️ Word Amount Reference", "### ⚖️ 言葉の量の参考"))
            st.caption(tr("After NAOMI responds, a word-amount comparison will appear here.", "NAOMIの返答後に、言葉の量の比較がここに表示されます。"))

if st.session_state.naomi_screen == "home":
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
                {t("welcome_subtitle")}
            </p>
        </div>
        <div class="naomi-home-actions">
            <div class="naomi-home-action-card">
                <div class="naomi-home-action-icon">🌿</div>
                <div class="naomi-home-action-title">{t("action_1_title")}</div>
                <div class="naomi-home-action-sub">{t("action_1_sub")}</div>
            </div>
            <div class="naomi-home-action-card">
                <div class="naomi-home-action-icon">💬</div>
                <div class="naomi-home-action-title">{t("action_2_title")}</div>
                <div class="naomi-home-action-sub">{t("action_2_sub")}</div>
            </div>
            <div class="naomi-home-action-card">
                <div class="naomi-home-action-icon">📋</div>
                <div class="naomi-home-action-title">{t("action_3_title")}</div>
                <div class="naomi-home-action-sub">{t("action_3_sub")}</div>
            </div>
        </div>
    </section>
    """, unsafe_allow_html=True)

    st.markdown('<div class="naomi-home-actions-buttons">', unsafe_allow_html=True)
    home_col1, home_col2, home_col3 = st.columns(3)
    current_lang = st.session_state.get("language", "JP")
    with home_col1:
        st.markdown(f'<a class="naomi-home-link-button" href="?screen=state&mode=tired&lang={current_lang}#naomi-menu-top" target="_self">{t("action_1_title")}</a>', unsafe_allow_html=True)
    with home_col2:
        st.markdown(f'<a class="naomi-home-link-button" href="?screen=state&mode=mental&lang={current_lang}#naomi-menu-top" target="_self">{t("action_2_title")}</a>', unsafe_allow_html=True)
    with home_col3:
        st.markdown(f'<a class="naomi-home-link-button" href="?screen=state&mode=health&lang={current_lang}#naomi-menu-top" target="_self">{t("action_3_title")}</a>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="naomi-home-note">{t("home_note")}</div>', unsafe_allow_html=True)
    st.stop()

# ── 🌿 NAOMIを使う方への静かな案内 ──
st.markdown("<div id='naomi-menu-top' style='height: 1px;'></div>", unsafe_allow_html=True)

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
    if st.button(btn_label_1, key="mode_btn_1", use_container_width=True, type="primary" if is_active_1 else "secondary"):
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
    if st.button(btn_label_3, key="mode_btn_3", use_container_width=True, type="primary" if is_active_3 else "secondary"):
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
    if st.button(btn_label_2, key="mode_btn_2", use_container_width=True, type="primary" if is_active_2 else "secondary"):
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
    if st.button(btn_label_4, key="mode_btn_4", use_container_width=True, type="primary" if is_active_4 else "secondary"):
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
with st.form("state_free_text_form", clear_on_submit=True):
    state_free_text = st.text_input(
        "任意の入力",
        placeholder="例：最近仕事が忙しくて疲れています",
        label_visibility="collapsed",
    )
    submitted_free_text = st.form_submit_button("そっと送る", use_container_width=False)
if submitted_free_text and state_free_text.strip():
    result = st.session_state.agent_core.process_input(state_free_text.strip(), active_profile())
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
            result = st.session_state.agent_core.process_input(text, active_profile())
            st.session_state.last_result = (text, result)
            st.session_state.proactive_question = None
            st.rerun()
            
    with row1_col2:
        st.markdown('<div class="status-btn-anxiety"></div>', unsafe_allow_html=True)
        if st.button(tr("😰 Feeling anxious", "😰 不安を感じる"), key="state_btn_anxiety", use_container_width=True):
            text = "明日のことを考えると不安で落ち着かない"
            result = st.session_state.agent_core.process_input(text, active_profile())
            st.session_state.last_result = (text, result)
            st.session_state.proactive_question = None
            st.rerun()
            
    with row1_col3:
        st.markdown('<div class="status-btn-tired"></div>', unsafe_allow_html=True)
        if st.button(tr("😮‍💨 Tired", "😮‍💨 疲れている"), key="state_btn_tired", use_container_width=True):
            text = "最近ちょっと疲れてて…"
            result = st.session_state.agent_core.process_input(text, active_profile())
            st.session_state.last_result = (text, result)
            st.session_state.proactive_question = None
            st.rerun()
            
    # 2行目
    with row2_col1:
        st.markdown('<div class="status-btn-insomnia"></div>', unsafe_allow_html=True)
        if st.button(tr("🌙 Sleepless night", "🌙 眠れない夜"), key="state_btn_insomnia", use_container_width=True):
            text = "明日も早いのに、考えごとが止まらなくて眠れない"
            profile = active_profile()
            result = st.session_state.agent_core.process_input(text, profile)
            st.session_state.last_result = (text, result)
            st.session_state.proactive_question = None
            # 眠れない夜を選択時は、低圧なQuiet Nightへ自動移行！
            st.session_state.theme_mode = "night"
            st.rerun()
            
    with row2_col2:
        st.markdown('<div class="status-btn-lonely"></div>', unsafe_allow_html=True)
        if st.button(tr("😢 Lonely", "😢 一人で寂しい"), key="state_btn_lonely", use_container_width=True):
            text = "なんか一人でいる感じがして寂しい"
            result = st.session_state.agent_core.process_input(text, active_profile())
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
        _tog1 = "Aa Large text" if st.session_state.get("language", "JP") == "EN" else "Aa 大きい文字"
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
                    result = st.session_state.agent_core.process_input(text, profile)
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

user_input = st.chat_input(tr("Example: I have been busy with work and feel tired", "例：最近仕事が忙しくて疲れています"))

if user_input:
    try:
        profile = active_profile()
        result = st.session_state.agent_core.process_input(user_input, profile)
        st.session_state.last_result = (user_input, result)
        # 手動クリックによるプロアクティブ質問は、一度返答があればクリアする
        st.session_state.proactive_question = None
        st.rerun()
    except Exception as e:
        st.error(f"Agent実行中にエラーが発生しました: {e}")

# --- 結果表示セクション ---
if st.session_state.last_result and not suppress_bottom_chat and st.session_state.naomi_screen != "state":
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
