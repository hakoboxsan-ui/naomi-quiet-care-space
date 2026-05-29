"""
NAOMI の静かな応答パターン

疲れ・不安・孤独感・考えすぎなど、
一般利用者がその日の状態に近い入口を選べるようにするための
固定応答パターンを定義する。

facs_hint は将来の表情・表示連携用の予約フィールド。
今回はUI表示のみで、実制御は行わない。
"""

from dataclasses import dataclass, field
from typing import Optional
from .state_engine import HumanState
from .mode_selector import Mode


@dataclass
class DemoScenario:
    """静かな応答パターンの出力データ"""
    scenario_id: str
    scenario_name: str
    response: str
    state: HumanState
    mode: Mode
    pressure_level: str           # VERY_LOW / LOW / MEDIUM / HIGH
    facs_hint: list = field(default_factory=list)  # 将来拡張用
    scenario_name_en: Optional[str] = None
    response_en: Optional[str] = None


# ── 固定応答パターン定義 ──

DEMO_SCENARIOS = {
    "tired": DemoScenario(
        scenario_id="tired",
        scenario_name="少し疲れている",
        response="今日は、かなり頑張ってきたんだね。\n今は無理に整理しなくても大丈夫。少しだけ、ここで息を整えよう。",
        state=HumanState(
            stress=0.78,
            loneliness=0.15,
            sleepiness=0.30,
            energy=0.10,
            need_listening=0.85,
            need_advice=0.25,
        ),
        mode=Mode.LISTENING_FIRST,
        pressure_level="LOW",
        facs_hint=["AU41", "AU15", "AU61"],
        scenario_name_en="Slightly tired",
        response_en="You've worked really hard today.\nShared with me, you don't have to organize anything right now. Let's just catch your breath here.",
    ),
    "anxiety": DemoScenario(
        scenario_id="anxiety",
        scenario_name="不安で落ち着かない",
        response="明日のことが頭から離れなくて、心が休まらないんだね。\n今すぐ答えを出さなくても大丈夫。まず、何が一番ひっかかっているか一緒に見ていこう。",
        state=HumanState(
            stress=0.82,
            loneliness=0.20,
            sleepiness=0.10,
            energy=0.18,
            need_listening=0.88,
            need_advice=0.45,
        ),
        mode=Mode.LISTENING_FIRST,
        pressure_level="LOW",
        facs_hint=["AU1", "AU15", "AU41"],
        scenario_name_en="Anxious & restless",
        response_en="Your mind is racing about tomorrow, making it hard to rest.\nYou don't have to find an answer right now. Let's look at what is bothering you most, step by step.",
    ),
    "lonely": DemoScenario(
        scenario_id="lonely",
        scenario_name="少し寂しい",
        response="一人で抱えている感じがして、少し寂しかったんだね。\nここでは急がなくていいよ。今の気持ちを、そのまま置いていって大丈夫。",
        state=HumanState(
            stress=0.25,
            loneliness=0.88,
            sleepiness=0.10,
            energy=0.15,
            need_listening=0.82,
            need_advice=0.10,
        ),
        mode=Mode.SILENT_COMPANION,
        pressure_level="VERY_LOW",
        facs_hint=["AU41", "AU6", "AU12"],
        scenario_name_en="Feeling lonely",
        response_en="It feels lonely carrying all this alone, doesn't it?\nNo need to rush here. It is perfectly okay to leave your feelings exactly as they are.",
    ),
    "exhausted_advice": DemoScenario(
        scenario_id="exhausted_advice",
        scenario_name="限界が近い",
        response="解決したい気持ちもあるけど、その前に少し限界が近い感じなんだね。\nすぐに答えを押しつけるより、まず状況を一緒にほどいていこうか。",
        state=HumanState(
            stress=0.90,
            loneliness=0.30,
            sleepiness=0.20,
            energy=0.08,
            need_listening=0.92,
            need_advice=0.85,
        ),
        mode=Mode.LISTENING_FIRST,
        pressure_level="LOW",
        facs_hint=["AU1", "AU15", "AU41", "AU25"],
        scenario_name_en="Close to my limit",
        response_en="You want to find a solution, but at the same time, you are running on empty.\nInstead of pushing immediate answers, let's gently untangle the situation together.",
    ),
    "overthinking_sleep": DemoScenario(
        scenario_id="overthinking_sleep",
        scenario_name="考えごとが止まらない夜",
        response="考えごとが止まらない夜って、眠ろうとするほど苦しくなりますよね。\n今は解決しなくて大丈夫なので、頭の中にあるものを一つだけ横に置くところから一緒にやりましょうか。",
        state=HumanState(stress=0.85, loneliness=0.30, sleepiness=0.60, energy=0.15, need_listening=0.90, need_advice=0.10),
        mode=Mode.LISTENING_FIRST,
        pressure_level="VERY_LOW",
        facs_hint=["AU41", "AU15"],
        scenario_name_en="Sleepless night",
        response_en="On nights when thoughts will not stop, trying to sleep can feel even harder.\nYou do not have to solve anything right now. Let's start by placing just one thought beside you.",
    ),
    "always_tense": DemoScenario(
        scenario_id="always_tense",
        scenario_name="休んでも張りつめる",
        response="体を休めても、心がずっと警戒モードのままでお辛いですね。\n何もしないのが怖い時は、ただゆっくり息を吐くことだけ、手伝わせてもらえませんか。",
        state=HumanState(stress=0.88, loneliness=0.25, sleepiness=0.20, energy=0.20, need_listening=0.85, need_advice=0.15),
        mode=Mode.LISTENING_FIRST,
        pressure_level="LOW",
        facs_hint=["AU1", "AU15", "AU41"],
        scenario_name_en="Still tense after resting",
        response_en="Even after resting your body, your mind still feels on alert. That sounds painful.\nIf doing nothing feels scary, may I just help you slowly breathe out?",
    ),
    "decision_fatigue": DemoScenario(
        scenario_id="decision_fatigue",
        scenario_name="小さな判断も重い",
        response="たくさん決断してきて、心がすり減ってしまったんですね。\n今日はもう大きな決定は下ろして、まずは一番小さな『今の気持ち』だけ聞かせてください。",
        state=HumanState(stress=0.75, loneliness=0.20, sleepiness=0.30, energy=0.05, need_listening=0.80, need_advice=0.50),
        mode=Mode.LISTENING_FIRST,
        pressure_level="LOW",
        facs_hint=["AU1", "AU15", "AU41", "AU25"],
        scenario_name_en="Small decisions feel heavy",
        response_en="You have made so many decisions that your mind feels worn down.\nNo big decisions are needed today. Just tell me the smallest piece of how you feel now.",
    ),
    "cannot_rest": DemoScenario(
        scenario_id="cannot_rest",
        scenario_name="休むのが申し訳ない",
        response="休むことに罪悪感を感じてしまうくらい、ずっと走り続けてこられたのですね。\n今は『休む』ではなく『一旦止まる』だけで大丈夫です。私がここにいます。",
        state=HumanState(stress=0.80, loneliness=0.40, sleepiness=0.25, energy=0.15, need_listening=0.88, need_advice=0.20),
        mode=Mode.SILENT_COMPANION,
        pressure_level="VERY_LOW",
        facs_hint=["AU41", "AU15"],
        scenario_name_en="Resting feels wrong",
        response_en="You have kept running so long that resting itself feels wrong.\nFor now, it does not have to be 'resting'. Just pausing for a moment is enough. I am here.",
    ),
    "silent_loneliness": DemoScenario(
        scenario_id="silent_loneliness",
        scenario_name="なんとなく寂しい",
        response="はっきりした理由がない時ほど、その孤独感は重く感じられますよね。\n言葉にならなくても構いません。ただ、あなたが一人ではないことだけ伝えておきますね。",
        state=HumanState(stress=0.40, loneliness=0.90, sleepiness=0.15, energy=0.25, need_listening=0.95, need_advice=0.05),
        mode=Mode.SILENT_COMPANION,
        pressure_level="VERY_LOW",
        facs_hint=["AU41", "AU6", "AU12"],
        scenario_name_en="Somehow lonely",
        response_en="The loneliness can feel heavier when there is no clear reason.\nYou do not have to put it into words. I just want you to know you are not alone.",
    ),
    "anxiety_insomnia": DemoScenario(
        scenario_id="anxiety_insomnia",
        scenario_name="不安が強く、眠れていない",
        response="今は、かなり張りつめている状態かもしれません。\n無理に答えを出そうとしなくて大丈夫です。まずは少し休むことを優先してもよさそうです。\n必要なら、今の状態を誰かに伝えるメモにまとめます。",
        state=HumanState(stress=0.88, loneliness=0.30, sleepiness=0.75, energy=0.10, need_listening=0.92, need_advice=0.35),
        mode=Mode.LISTENING_FIRST,
        pressure_level="VERY_LOW",
        facs_hint=["AU1", "AU15", "AU41"],
        scenario_name_en="Anxiety and insomnia",
        response_en="You may be feeling very tense right now.\nYou do not have to force an answer. It may be okay to prioritize a little rest first.\nIf needed, I can help turn your current state into a note for someone else.",
    ),
    "state_support_memo": DemoScenario(
        scenario_id="state_support_memo",
        scenario_name="誰かに伝えるメモがほしい",
        response="誰かに伝えるために、今の状態を少し整えたいのですね。\n医療判断ではなく、あなたが困っていることを伝えやすくするためのメモとして、短くまとめていけます。",
        state=HumanState(stress=0.65, loneliness=0.30, sleepiness=0.25, energy=0.25, need_listening=0.75, need_advice=0.65),
        mode=Mode.LISTENING_FIRST,
        pressure_level="LOW",
        facs_hint=["AU41", "AU15"],
        scenario_name_en="Need a shareable note",
        response_en="You want to gently organize your current state so you can share it with someone.\nThis is not a medical judgment, but we can make a short note that helps communicate what is difficult.",
    ),
    "health_symptoms": DemoScenario(
        scenario_id="health_symptoms",
        scenario_name="健康状態を伝えたい",
        response="体調のことを、伝えやすく整理したいのですね。\n今わかっている症状、いつ頃からか、生活への影響を短く並べるだけでも、相談先に伝えやすくなります。",
        state=HumanState(stress=0.70, loneliness=0.10, sleepiness=0.35, energy=0.15, need_listening=0.70, need_advice=0.55, physical_distress=0.85),
        mode=Mode.LISTENING_FIRST,
        pressure_level="LOW",
        facs_hint=["AU41", "AU15"],
        scenario_name_en="Share health symptoms",
        response_en="You want to organize your physical condition so it is easier to explain.\nEven listing symptoms, when they started, and their impact on daily life can make it easier to share with a consultant.",
    ),
}


# ── 状態に近い入力を検出するキーワード ──

_SCENARIO_KEYWORDS = {
    "tired": ["最近ちょっと疲れ", "ちょっと疲れ", "すごく疲れ"],
    "anxiety": ["明日のこと", "不安で落ち着かない", "考えると不安"],
    "lonely": ["一人でいる感じ", "一人でいる", "寂しい"],
    "exhausted_advice": ["教えてほしいけど", "どうしたらいいか", "疲れてる"],
    "overthinking_sleep": ["明日も早いのに", "考えごとが止まらなくて", "眠れない"],
    "always_tense": ["休んでるはずなのに", "気を張っている"],
    "decision_fatigue": ["小さいことを決めるのも", "何から考えればいいか"],
    "cannot_rest": ["休んでいい気がしない"],
    "silent_loneliness": ["別に大きな問題があるわけじゃない", "一人で抱えてる感じ"],
    "anxiety_insomnia": ["不安が強い", "眠れていない", "眠れてない"],
    "state_support_memo": ["誰かに伝えるメモ", "メモがほしい", "支援者に伝えたい"],
    "health_symptoms": ["熱っぽい", "喉が痛い", "吐き気", "下痢", "めまい", "動悸", "息苦しい", "医師へ伝えたい"],
}

# 長いキーワードを先にチェックするためにソートする
_SORTED_SCENARIOS = sorted(
    _SCENARIO_KEYWORDS.items(),
    key=lambda item: max(len(kw) for kw in item[1]),
    reverse=True,
)


def detect_demo_scenario(user_text: str) -> Optional[str]:
    """
    ユーザー入力テキストが固定応答パターンに該当するか判定する。
    該当すれば scenario_id を返し、該当しなければ None を返す。
    """
    for scenario_id, keywords in _SORTED_SCENARIOS:
        for kw in keywords:
            if kw in user_text:
                return scenario_id
    return None


def get_demo_response(scenario_id: str) -> Optional[DemoScenario]:
    """
    scenario_id から固定応答パターンの完全な応答データを返す。
    """
    return DEMO_SCENARIOS.get(scenario_id)
