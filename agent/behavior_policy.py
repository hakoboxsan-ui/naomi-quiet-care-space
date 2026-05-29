from dataclasses import dataclass, field
from typing import List
from .state_engine import HumanState
from .mode_selector import Mode


@dataclass
class AgentStrategy:
    """AIの会話戦略を可視化するためのデータ構造"""
    advice_mode: str       # ON / OFF / WAIT
    listening_mode: bool
    speech_density: str    # LOW / MEDIUM / HIGH
    pause_length: str      # LONG / MEDIUM / SHORT
    emotional_tone: str
    goal: str
    pressure_level: str = "MEDIUM"          # VERY_LOW / LOW / MEDIUM / HIGH
    facs_hint: List[str] = field(default_factory=list)  # 将来拡張用 (Companion表情)


def determine_strategy(mode: Mode, state: HumanState) -> AgentStrategy:
    """
    ModeとHumanStateから、AIが『どう接するか』のConversation Strategyを決定する。
    """
    if mode == Mode.QUIET_SUPPORT:
        return AgentStrategy(
            advice_mode="OFF",
            listening_mode=True,
            speech_density="LOW",
            pause_length="LONG",
            emotional_tone="Calm",
            goal="Ensure warm silence & safety",
            pressure_level="VERY_LOW",
        )

    elif mode == Mode.LISTENING_FIRST:
        return AgentStrategy(
            advice_mode="WAIT",
            listening_mode=True,
            speech_density="LOW",
            pause_length="LONG",
            emotional_tone="Gentle",
            goal="Relieve cognitive load",
            pressure_level="LOW",
        )

    elif mode == Mode.GENTLE_GUIDANCE:
        return AgentStrategy(
            advice_mode="ON",
            listening_mode=False,
            speech_density="MEDIUM",
            pause_length="MEDIUM",
            emotional_tone="Supportive",
            goal="Help organize user thoughts gently",
            pressure_level="MEDIUM",
        )

    elif mode == Mode.SILENT_COMPANION:
        return AgentStrategy(
            advice_mode="OFF",
            listening_mode=True,
            speech_density="LOW",
            pause_length="LONG",
            emotional_tone="Quiet",
            goal="Warm low-pressure company",
            pressure_level="VERY_LOW",
        )

    else:  # LOW_PRESSURE
        return AgentStrategy(
            advice_mode="OFF",
            listening_mode=True,
            speech_density="LOW",
            pause_length="LONG",
            emotional_tone="Gentle",
            goal="Maintain peaceful state",
            pressure_level="LOW",
        )
