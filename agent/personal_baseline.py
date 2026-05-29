import json
import os
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional

# プロジェクトルートからのデータ保存パス
DATA_DIR = "data"
PROFILES_FILE = os.path.join(DATA_DIR, "personal_profiles.json")

@dataclass
class PersonalBaseline:
    """利用者の『普段の状態』や好みを保持するデータクラス"""
    user_id: str
    display_name: str
    usual_energy: float = 0.5  # 普段の元気度 (0.0 - 1.0)
    usual_talk_length: str = "medium"  # short / medium / long
    sleep_tendency: str = "good"  # good / irregular / bad
    preferred_interaction_style: str = "gentle"  # gentle / direct / companion
    sensitive_topics: List[str] = field(default_factory=list)
    favorite_topics: List[str] = field(default_factory=list)
    care_notes: str = ""

def load_profiles() -> Dict[str, dict]:
    """JSONファイルからプロフィール全データを読み込む"""
    if not os.path.exists(PROFILES_FILE):
        # デフォルトデータの作成
        default_profiles = {
            "default": asdict(PersonalBaseline(user_id="default", display_name="デフォルト利用者")),
            "user_a": asdict(PersonalBaseline(
                user_id="user_a", 
                display_name="田中さん (普段元気)", 
                usual_energy=0.8,
                usual_talk_length="long",
                favorite_topics=["散歩", "孫"]
            )),
            "user_b": asdict(PersonalBaseline(
                user_id="user_b", 
                display_name="佐藤さん (物静か)", 
                usual_energy=0.3,
                usual_talk_length="short",
                sleep_tendency="irregular"
            ))
        }
        save_profiles(default_profiles)
        return default_profiles
    
    try:
        with open(PROFILES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_profiles(profiles: Dict[str, dict]):
    """プロフィールデータをJSONファイルに保存する"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    
    with open(PROFILES_FILE, 'w', encoding='utf-8') as f:
        json.dump(profiles, f, ensure_ascii=False, indent=4)

def get_profile(user_id: str) -> dict:
    """指定されたIDのプロフィールを取得する"""
    profiles = load_profiles()
    return profiles.get(user_id, profiles.get("default"))

def update_profile(user_id: str, updates: dict) -> dict:
    """プロフィールを更新して保存する"""
    profiles = load_profiles()
    if user_id not in profiles:
        profiles[user_id] = asdict(PersonalBaseline(user_id=user_id, display_name=user_id))
    
    profiles[user_id].update(updates)
    save_profiles(profiles)
    return profiles[user_id]

def compare_with_baseline(user_text: str, current_state: dict, profile: dict) -> List[str]:
    """
    現在の状態とベースラインを比較し、『普段との違い』を抽出する。
    
    Returns:
        List[str]: 違いを示す短いメッセージのリスト
    """
    diff_notes = []
    
    # 元気度の比較
    usual_energy = profile.get("usual_energy", 0.5)
    curr_energy = current_state.get("energy", 0.0)
    
    if usual_energy - curr_energy > 0.4:
        diff_notes.append("いつもより少し活気が低下している様子が見受けられます")
    elif curr_energy - usual_energy > 0.4:
        diff_notes.append("いつもより少し活動的、あるいは気が張っている様子があります")

    # 会話量の簡易比較 (普段 short の人が長文、など)
    text_len = len(user_text)
    usual_len = profile.get("usual_talk_length", "medium")
    
    if usual_len == "long" and text_len < 5:
        diff_notes.append("いつもに比べて、言葉少なめでいらっしゃるようです")
    elif usual_len == "short" and text_len > 30:
        diff_notes.append("いつもよりご自身のお気持ちを多く話されている様子があります")

    # 睡眠影響
    if current_state.get("sleepiness", 0.0) > 0.6:
        if profile.get("sleep_tendency") == "good":
            diff_notes.append("普段はよく休まれているようですが、本日は少しお疲れ・眠気がある様子です")
        else:
            diff_notes.append("継続して睡眠不足や眠気の傾向が見受けられます")

    # ストレス・不安
    if current_state.get("stress", 0.0) > 0.6:
        diff_notes.append("少しご負担や気疲れが重なっている様子がうかがえます")

    return diff_notes
