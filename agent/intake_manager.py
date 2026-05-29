from typing import List, Dict, Optional, Any

class IntakeManager:
    """問診モード（Intake Mode）の進行管理と情報整理を担当する。"""

    INTAKE_TYPES = {
        "internal_medicine": [
            "発症時期（いつからつらいか）",
            "主症状（一番つらいところ）",
            "発熱の有無",
            "咳・喉の痛み",
            "鼻水・鼻詰まり",
            "頭痛",
            "倦怠感（だるさ）",
            "息苦しさ（呼吸のしにくさ）",
            "胸の痛み",
            "水分の摂取状況",
            "食事の摂取状況",
            "持病（基礎疾患）",
            "現在服用中の薬",
            "周囲の流行状況（家族や身近な人の感染症）",
            "受診の希望"
        ]
    }

    def __init__(self):
        self.active = False
        self.intake_type = None
        self.current_step = 0
        self.history = []  # List of {"question": str, "answer": str}
        self.red_flags = []

    def start_intake(self, intake_type: str = "internal_medicine"):
        """問診を開始する。"""
        if intake_type in self.INTAKE_TYPES:
            self.active = True
            self.intake_type = intake_type
            self.current_step = 0
            self.history = []
            self.red_flags = []
            return True
        return False

    def stop_intake(self):
        """問診を終了する。"""
        self.active = False

    def get_next_question_topic(self) -> Optional[str]:
        """次に聞くべきトピックを返す。"""
        topics = self.INTAKE_TYPES.get(self.intake_type, [])
        if self.current_step < len(topics):
            return topics[self.current_step]
        return None

    def record_answer(self, question: str, answer: str):
        """ユーザーの回答を記録し、レッドフラグをチェックする。"""
        self.history.append({"question": question, "answer": answer})
        
        # レッドフラグの段階的チェック
        critical_keywords = {
            "息苦しい": ("呼吸困難の様子", "high"),
            "苦しい": ("呼吸困難の様子", "high"),
            "胸が痛い": ("胸痛の訴え", "high"),
            "激痛": ("強い痛みの訴え", "high"),
            "意識": ("意識レベル低下の可能性", "high"),
            "飲めない": ("脱水傾向の可能性", "medium"),
            "水分がとれない": ("脱水傾向の可能性", "medium"),
            "熱": ("発熱の様子", "low"),
            "だるい": ("倦怠感の訴え", "low")
        }
        
        for kw, (label, level) in critical_keywords.items():
            if kw in answer:
                if not any(f["label"] == label for f in self.red_flags):
                    self.red_flags.append({"label": label, "level": level})
        
        self.current_step += 1

    def generate_handoff_note(self) -> str:
        """医療者向けの申し送りノートを生成する。"""
        lines = [f"【NAOMI問診レポート: {self.intake_type}】"]
        
        if self.red_flags:
            lines.append("⚠️ 確認事項（要注意の可能性）:")
            for flag in self.red_flags:
                lines.append(f"  - [{flag['level'].upper()}] {flag['label']}")
            lines.append("")

        lines.append("■ 問診内容:")
        for entry in self.history:
            lines.append(f"Q: {entry['question']}")
            lines.append(f"A: {entry['answer']}")
        
        lines.append("\n※このレポートはAIとの対話記録です。診察の補助としてお使いください。")
        return "\n".join(lines)

    def is_finished(self) -> bool:
        """すべての質問が完了したか判定する。"""
        topics = self.INTAKE_TYPES.get(self.intake_type, [])
        return self.current_step >= len(topics)
