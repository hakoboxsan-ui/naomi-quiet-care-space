import re

class PersonaGuard:
    """
    不適切な口調（診断、命令、説教）や特定の抑制キーワードを優しく安全な表現に変換するガードレール。
    """
    def __init__(self):
        # 抑制表現と柔らかい代替表現のマッピング（正規表現または単純文字列）
        self.replacements = [
            # 診断・断定の抑制
            (r"必ず", "なるべく"),
            (r"治療", "ケア"),
            (r"判定", "ご様子"),
            (r"診断", "整理"),
            (r"病気", "体調の変化"),
            (r"うつ病", "お疲れがたまった状態"),
            (r"認知症", "もの忘れなどのご様子"),
            
            # 命令・説教の抑制
            (r"すべき", "するのもよいかもしれません"),
            (r"しなさい", "してみてくださいね"),
            (r"教えなさい", "教えていただけますか"),
            (r"解決しなさい", "少しずつ整理してみましょう"),
            
            # 不自然な硬い表現・SaaS接客感の緩和
            (r"実行してください", "試してみてくださいね"),
            (r"義務です", "ご無理のない範囲で大丈夫です"),
            (r"〜になります", "〜のご様子です"),
            (r"確認してください", "見てみてくださいね"),
        ]

    def sanitize(self, text: str, input_text: str = "") -> str:
        """
        出力テキストを走査し、安全な表現へ置換する。不調文脈での高テンション誤爆も完全遮断。
        さらに、NAOMIの『低圧・Cognitive Relief』の人格に反する空気感（Vibe）を検知して遮断。
        """
        sanitized = text
        
        # ── 感情極性バグ防御安全遮断器 (Failsafe Guardrail) ──
        illness_keywords = ["気持ち悪い", "吐き気", "吐きそう", "苦しい", "痛い", "しんどい", "だるい", "めまい", "頭痛", "熱", "息苦しい", "つらい", "不安", "限界", "もう無理"]
        is_illness = any(w in input_text for w in illness_keywords) or any(w in text for w in illness_keywords)

        # 空気感（Vibe）検知と安全遮断
        inappropriate_vibes = [
            "楽しそう", "嬉しい", "うれしい", "あはは", "いいね", "ワクワク", "わくわく", 
            "嬉しく", "楽しい", "最高", "やった", "おぉ", "すごいね", "おめでとう",
            "詳しく教えて", "もっと話して", "どうしてですか？"
        ]
        
        if is_illness:
            # 不調時：高テンション、情報要求圧、元気づけすぎを完全に遮断 ➔ 心身を心配する静かな見守りへ強制置換
            if any(f in sanitized for f in inappropriate_vibes) or "？" in sanitized or "?" in sanitized:
                return "とてもお辛いですね……、本当に心配です。今はどうぞ無理に言葉にされようとせず、このまま静かに休んでくださいね。お返事も不要ですよ。"
        else:
            # 通常時でも、過剰なテンション高や雑談ノリを上品に緩和し、親身に心身を思いやる姿勢へ
            if any(f in sanitized for f in ["あはは", "いいね", "最高", "やった", "おぉ"]):
                sanitized = "そうだったのですね。お疲れなどはありませんか？いつもあなたの心身を見守り、心配していますからね。どうぞご無理のない範囲でゆっくりお過ごしくださいね。"

        for pattern, replacement in self.replacements:
            sanitized = re.sub(pattern, replacement, sanitized)
            
        # 診断・解決策の押しつけの追加緩和（末尾にやわらかい余白を付与）
        if "解決策" in sanitized or "対策" in sanitized:
            sanitized = sanitized.replace("解決策は", "ご提案としては").replace("対策は", "できることとしては")
            
        return sanitized
