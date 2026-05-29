from typing import Dict, List, Optional
from .state_engine import HumanState
from .mode_selector import Mode

def generate_checkin_question(context_type: str, profile: Optional[dict] = None) -> str:
    """
    指定されたコンテクストに基づき、NAOMIからの能動的な問いかけを生成する。
    """
    language = profile.get("language", "JP") if profile else "JP"
    name = profile.get("display_name", "user" if language == "EN" else "利用者") if profile else ("user" if language == "EN" else "利用者")
    
    if language == "EN":
        questions = {
            "morning_checkin": f"Good morning, {name}. How does your body feel today compared with yesterday?",
            "sleep_check": "Were you able to sleep well last night? Did you wake up during the night?",
            "loneliness_check": "Did you have a chance to talk with anyone today? If you would like, we can talk a little here.",
            "fatigue_check": "You seem a little tired. Does your body feel heavy? You do not have to force yourself to speak.",
            "care_facility_daily": "Is there anything about today's mood or condition that you would like staff to know?",
            "hospital_checkin": "Would you like to organize your physical discomfort or anxiety so it is easier to tell a doctor or nurse?",
        }
        return questions.get(context_type, "How are you feeling?")
    
    questions = {
        "morning_checkin": f"おはようございます、{name}さん。今日は体の調子、昨日と比べてどうですか？",
        "sleep_check": "昨夜はぐっすり眠れましたか？途中で目が覚めたりしませんでしたか？",
        "loneliness_check": "今日は誰かとお話しする機会はありましたか？もしよければ、少しお話ししませんか。",
        "fatigue_check": "少しお疲れのように見えますが、お体だるかったりしませんか？無理に話さなくても大丈夫ですよ。",
        "care_facility_daily": "今日の気分や体調で、職員さんに伝えておきたいことなどはありますか？",
        "hospital_checkin": "今の体のつらさや不安を、先生や看護師さんに伝えやすいように、一緒に整理してみましょうか？"
    }
    
    return questions.get(context_type, "調子はいかがですか？")

def generate_care_proposal(human_state: HumanState, mode: Mode, pressure: str, profile: Optional[dict] = None, baseline_diff: Optional[List[str]] = None, language: str = "JP") -> str:
    """
    現在の状態とベースライン差分に基づき、小さなケア提案を生成する。
    """
    if language == "EN":
        proposals = []
        if human_state.sleepiness > 0.6:
            proposals.append("It is suggested to avoid strenuous activity, stay hydrated, and take more rest.")
        if human_state.stress > 0.6:
            proposals.append("Take deep breaths and organize your burdens one by one. No need to rush.")
        if human_state.loneliness > 0.6:
            proposals.append("If you'd like, I'm always here to listen to any pleasant memories or thoughts you want to share.")
        if not proposals:
            proposals.append("Your state seems stable. Please continue to pace yourself gently.")
        return " ".join(proposals)

    proposals = []
    
    # 状態に基づいた柔らかい提案
    if human_state.sleepiness > 0.6:
        proposals.append("今日は無理に活動せず、水分を摂って少し横になる時間を増やしてみてはいかがでしょうか。")
    
    if human_state.stress > 0.6:
        proposals.append("深呼吸をして、まずは今の負担を一つずつ整理していきましょう。急がなくても大丈夫です。")
        
    if human_state.loneliness > 0.6:
        proposals.append("もしよければ、昔の楽しかった思い出など、何かお話ししたいことがあればいつでも聞きますよ。")

    if not proposals:
        proposals.append("今のところ安定しているようです。この調子で、ご自分のペースを大切にお過ごしください。")
        
    return " ".join(proposals)

def generate_staff_note(user_text: str, human_state: HumanState, proposal: str, pressure: str, baseline_diff: Optional[List[str]] = None, language: str = "JP") -> str:
    """
    支援者（職員・家族）向けの客観的な共有メモを生成する。
    医療断定を避け、客観的な事実とNAOMIの気づきに留める。
    """
    if language == "EN":
        notes = ["■ Care handoff note (Staff Note)"]
        notes.append(f"・Current concern: \"{user_text}\"")
        if baseline_diff:
            notes.append(f"・Changes from baseline: {', '.join(baseline_diff)}")
        
        trend_str = "Seems calm and stable"
        if human_state.stress > 0.6 or human_state.energy < 0.4:
            trend_str = "May be experiencing fatigue or emotional distress"
        notes.append(f"・Estimated state (Anxiety/Fatigue): {trend_str}")
        
        sleep_str = "No specific sleep issues detected"
        if human_state.sleepiness > 0.6:
            sleep_str = "Potential lack of sleep or high fatigue"
        notes.append(f"・Sleep condition: {sleep_str}")
        
        pressure_map = {"VERY_LOW": "Very Gentle (Very Low)", "LOW": "Gentle (Low)", "MEDIUM": "Standard (Medium)", "HIGH": "Active (High)"}
        notes.append(f"・Conversation pressure: {pressure_map.get(pressure, pressure)}")
        notes.append(f"・Suggested approach / Care proposal: {proposal}")
        notes.append("\n*This is not a medical diagnosis or clinical assessment.")
        return "\n".join(notes)

    notes = ["■ 状態整理メモ (Staff Note)"]
    
    # 状態の要約
    notes.append(f"・現在の主訴: 「{user_text}」")
    
    if baseline_diff:
        notes.append(f"・普段との違い: {', '.join(baseline_diff)}")
    
    # 不安/疲労傾向
    trend_str = "落ち着いている様子"
    if human_state.stress > 0.6 or human_state.energy < 0.4:
        trend_str = "少しお疲れ、あるいはご負担を感じている可能性"
    notes.append(f"・不安/疲労の傾向: {trend_str}")
    
    # 睡眠状態
    sleep_str = "特筆事項なし"
    if human_state.sleepiness > 0.6:
        sleep_str = "睡眠不足や眠気の影響がある可能性"
    notes.append(f"・睡眠状態: {sleep_str}")
    
    # 会話圧
    pressure_map = {"VERY_LOW": "極めて低い", "LOW": "低い", "MEDIUM": "標準", "HIGH": "高い"}
    notes.append(f"・会話圧: {pressure_map.get(pressure, pressure)} (推奨)")
    
    notes.append(f"・本人が気にしている点 / 補足: {proposal}")
    notes.append("\n※このメモはAIとの対話からの推定であり、医療的な診断や断定を行うものではありません。")
    
    return "\n".join(notes)
