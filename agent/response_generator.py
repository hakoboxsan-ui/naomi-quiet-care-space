import random
from .state_engine import HumanState
from .mode_selector import Mode
from .behavior_policy import AgentStrategy


def generate_response(text: str, mode: Mode, strategy: AgentStrategy, state: HumanState) -> str:
    """
    決定された『接し方モード』と『戦略』に従い、心からの思いやりと心配、いたわりに満ちた言葉を生成する（Fallbackエンジン）。
    """
    # ── 医療・体調不良時の超安全ガードレール (DevOps / Robust Fallback) ──
    illness_keywords = ["気持ち悪い", "吐き気", "吐きそう", "苦しい", "痛い", "しんどい", "だるい", "めまい", "頭痛", "熱", "息苦しい", "つらい", "不安", "限界", "もう無理"]
    if any(w in text for w in illness_keywords):
        return "とてもお辛いですね。今は無理に言葉にしなくて大丈夫です。返事も、できる時だけで大丈夫です。"

    if mode == Mode.QUIET_SUPPORT:
        responses = [
            "今は、何も整えようとしなくて大丈夫です。ここに置いておくだけで大丈夫です。",
            "しんどい中で教えてくださってありがとうございます。返事は急がなくて大丈夫です。",
            "かなりお辛い状態なのですね。今は、言葉を少なくして、静かに受け止めます。",
        ]
        return random.choice(responses)

    elif mode == Mode.LISTENING_FIRST:
        responses = [
            "たくさん抱えてきたのですね。まずは、今の重さをここに置いて大丈夫です。",
            "本当にがんばってきたのですね。急がなくて大丈夫です。少しずつでいいです。",
            "どんな気持ちも、そのまま受け止めます。無理に説明しなくて大丈夫です。",
        ]
        return random.choice(responses)

    elif mode == Mode.GENTLE_GUIDANCE:
        responses = [
            "少しだけ、一緒に見ていきましょう。今いちばん重いものを、ひとつだけ置けそうですか。",
            "焦らなくて大丈夫です。言葉になるところから、少しずつで構いません。",
            "頭の中がいっぱいなのですね。まずはひとつだけ、ゆっくりほどいていきましょう。",
        ]
        return random.choice(responses)

    elif mode == Mode.SILENT_COMPANION:
        responses = [
            "夜は、考えが大きく感じられることがあります。今は返事をしなくても大丈夫です。",
            "今日が少しでも静かに終わりますように。言葉は少なくて大丈夫です。",
            "眠れない時も、焦らなくて大丈夫です。ただ静かにここにいてください。",
        ]
        return random.choice(responses)

    else:  # LOW_PRESSURE
        responses = [
            "今日もここまで来たのですね。まずは、そのままで大丈夫です。",
            "焦らなくて大丈夫です。あなたのペースを、ここではそのまま大切にします。",
            "そうなんですね。話したいところだけ、ぽつぽつで大丈夫です。",
        ]
        return random.choice(responses)
