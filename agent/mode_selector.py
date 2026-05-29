from enum import Enum
from .state_engine import HumanState


class Mode(Enum):
    QUIET_SUPPORT = "Quiet Support (静かな見守り)"
    LISTENING_FIRST = "Listening First (傾聴最優先)"
    LISTENING = "Listening First (傾聴最優先)"
    LOW_PRESSURE = "Low Pressure (低圧応対)"
    SILENT_COMPANION = "Silent Companion (静かな伴走)"
    GENTLE_GUIDANCE = "Gentle Guidance (穏やかな整理)"
    ADVICE = "Gentle Guidance (穏やかな整理)"


def select_mode(state: HumanState) -> Mode:
    """
    HumanStateから『AIがどう接するか』の接し方モードを決定する。
    """
    # 0. 身体的不調（Physical Distress）➔ 最優先で静かな見守り
    if getattr(state, "physical_distress", 0.0) >= 0.5:
        return Mode.QUIET_SUPPORT

    # 1. 極度の不調・ストレス高・エネルギー低 ➔ 静かな見守り
    if state.stress >= 0.7 or state.energy <= 0.2:
        return Mode.QUIET_SUPPORT
        
    # 2. 安心欲求が極めて高い、または傾聴が必要 ➔ 傾聴最優先
    if state.reassurance_need >= 0.6 or state.need_listening >= 0.7:
        return Mode.LISTENING_FIRST
        
    # 3. アドバイスや整理を求めている ➔ 穏やかな整理
    if state.need_advice >= 0.6:
        return Mode.GENTLE_GUIDANCE
        
    # 4. 眠気や夜間・疲労時 ➔ 静かな伴走
    if state.sleepiness >= 0.5 or state.energy <= 0.4:
        return Mode.SILENT_COMPANION
        
    # 5. 通常時 ➔ 低圧応対
    return Mode.LOW_PRESSURE
