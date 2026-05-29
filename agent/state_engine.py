from dataclasses import dataclass


@dataclass
class HumanState:
    """ユーザーの内部状態を定量化するデータクラス"""
    stress: float = 0.0
    loneliness: float = 0.0
    sleepiness: float = 0.0
    energy: float = 0.0
    need_listening: float = 0.0
    need_advice: float = 0.0
    reassurance_need: float = 0.0
    physical_distress: float = 0.0  # 身体的不調（頭痛、腹痛、寒気など）の強さ


def estimate_state(text: str) -> HumanState:
    """
    ユーザー入力テキストからルールベースで状態を簡易推定する。
    """
    state = HumanState()

    # --- 身体的不調（Physical Distress）の判定 ──
    physical_keywords = ["頭痛", "腹痛", "お腹痛い", "お腹が痛い", "寒気", "吐き気", "気持ち悪い", "熱", "だるい", "しんどい", "苦しい", "息苦しい", "めまい", "咳", "鼻水", "痛い", "吐きそう", "頭が重い"]
    if any(w in text for w in physical_keywords):
        state.physical_distress = 1.0
        state.stress = 0.9
        state.energy = 0.0
        state.need_listening = 0.9
        state.reassurance_need = 0.9

    # --- ストレス・精神的負荷系 ---
    if any(w in text for w in ["疲れ", "しんど", "不安", "辛い", "つらい", "いや", "だるい", "きつい", "もう無理", "限界"]):
        state.stress = min(1.0, state.stress + 0.8)
        state.energy = max(0.0, state.energy - 0.4)
        state.need_listening = min(1.0, state.need_listening + 0.9)

    # --- 眠気系 ---
    if any(w in text for w in ["眠", "寝た", "ふぁ", "夜", "おやすみ", "ねむ"]):
        state.sleepiness = min(1.0, state.sleepiness + 0.8)
        state.need_listening = min(1.0, state.need_listening + 0.5)

    # --- 孤独感系 ---
    if any(w in text for w in ["寂し", "さみし", "一人", "ひとり", "悲し", "誰か", "話したい"]):
        state.loneliness = min(1.0, state.loneliness + 0.7)
        state.need_listening = min(1.0, state.need_listening + 0.7)

    # --- ポジティブ / エネルギー系 ---
    if any(w in text for w in ["元気", "楽し", "最高", "わーい", "うれし", "良か", "やった"]):
        state.energy = min(1.0, state.energy + 0.7)

    # --- アドバイス要求系 ---
    if any(w in text for w in ["相談", "どうすれば", "どうしたら", "教え", "アドバイス", "方法"]):
        state.need_advice = min(1.0, state.need_advice + 0.8)

    # --- 安心欲求系（不調時を含む） ---
    if any(w in text for w in ["助け", "不安", "どうしよう", "怖い", "苦しい", "つらい", "心配", "しんど"]):
        state.reassurance_need = min(1.0, state.reassurance_need + 0.9)
        state.need_listening = min(1.0, state.need_listening + 0.9)

    # --- デフォルト: 何もマッチしなければ軽い会話モード ---
    total = state.stress + state.loneliness + state.sleepiness + state.energy + state.need_listening + state.need_advice + state.reassurance_need + state.physical_distress
    if total == 0.0:
        state.energy = 0.3

    return state
