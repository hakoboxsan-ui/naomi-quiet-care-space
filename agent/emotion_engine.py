from .state_engine import HumanState

class EmotionEngine:
    """
    ユーザーの感情状態（HumanState）に応じて、AIの返答スタイル（長さ、順序、要求度合い）を動的に調節する。
    """
    def adjust_response(self, text: str, state: HumanState) -> str:
        # 1. 身体的不調（Physical Distress）：1〜2文制限
        if getattr(state, "physical_distress", 0.0) >= 0.5:
            # カウンセラー的な心理前置きを一切スキップし、最短のいたわりと休息促しのみで構成
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            base = lines[0] if lines else "お体がかなりしんどい状態ですね……。本当に心配です。"
            # カウンセリング用フレーズが紛れ込んでいたら自動排除し、ストレートな思いやりへ
            if any(p in base for p in ["受け止め", "お気持ち", "大丈夫", "整理し"]):
                base = "それはかなりしんどいですね……。本当に心配しております。"
            
            if not base.endswith("。") and not base.endswith("ね。") and not base.endswith("よ。"):
                base += "。"
            return base + "\n今は無理に整理しようとせず、暖かくして静かに休んでくださいね。お返事も大丈夫ですよ。"

        # 2. 不安・安心欲求高（reassurance_need >= 0.6）：2〜3文制限
        if hasattr(state, 'reassurance_need') and state.reassurance_need >= 0.6:
            reassurance_phrases = "まずはそのお気持ち、しっかりと受け止めますね。焦らなくて大丈夫ですよ。"
            lines = [line.strip() for line in text.split("\n") if line.strip() and not any(p in line for p in ["大丈夫", "わかります", "安心", "受け止め"])]
            second_line = lines[0] if lines else "いつでもあなたの隣に寄り添っていますからね。"
            if not second_line.endswith("ね。") and not second_line.endswith("よ。") and not second_line.endswith("。"):
                second_line += "。"
            return reassurance_phrases + "\n" + second_line

        # 3. ストレス高（stress >= 0.6）または 相談希望（need_advice >= 0.6）：3〜5文制限
        if state.stress >= 0.6 or state.need_advice >= 0.6:
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            adjusted = "\n".join(lines[:3]) # 3行（約3〜4文）に制限
            if not adjusted.endswith("ね。") and not adjusted.endswith("よ。") and not adjusted.endswith("。"):
                adjusted += "。"
            # 返事を強要しない
            if state.energy <= 0.3:
                adjusted += "\n\n※無理に答えようとせず、このまま静かに休んでくださいね。"
            return adjusted

        # 4. 眠気高（sleepiness >= 0.6）
        if state.sleepiness >= 0.6:
            return "頭の考えごとはここに置いて、どうぞゆっくり目を閉じてお休みください。お返事も不要ですよ。"

        # 5. 通常時：最大5文程度に収める
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        return "\n".join(lines[:5])
