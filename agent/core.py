from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict
from .state_engine import estimate_state, HumanState
from .mode_selector import select_mode, Mode
from .behavior_policy import determine_strategy, AgentStrategy
from .response_generator import generate_response
from .demo_scenarios import detect_demo_scenario, get_demo_response
from .personal_baseline import compare_with_baseline
from .proactive_care import generate_care_proposal, generate_staff_note
from .gemini_brain import GeminiBrain
from .intake_manager import IntakeManager

@dataclass
class AgentResponse:
    """Agent Coreの出力。UIレイヤーはこれだけ受け取ればよい。"""
    text: str
    state: HumanState
    mode: Mode
    strategy: AgentStrategy
    scenario_id: Optional[str] = None       # デモシナリオ該当時のみ設定
    pressure_level: str = "MEDIUM"          # VERY_LOW / LOW / MEDIUM / HIGH
    facs_hint: List[str] = field(default_factory=list)  # 将来拡張用
    
    # Phase 3 追加フィールド
    baseline_diff: List[str] = field(default_factory=list)
    care_proposal: str = ""
    staff_note: str = ""
    handoff_note: str = ""
    intake_summary: str = ""
    intake_active: bool = False
    red_flags: List[Dict[str, str]] = field(default_factory=list)

class NaomiAgentCore:
    """
    NAOMIの意思決定・状態遷移・返答生成パイプラインを統合するコアクラス。
    """
    def __init__(self):
        self.gemini = GeminiBrain()
        self.intake = IntakeManager()

    def process_input(self, text_input: str, profile: Optional[Dict] = None) -> AgentResponse:
        """
        ユーザー入力を処理し、NAOMIの返答と内部状態を返す。
        """
        # --- 0. 問診モード（Intake Mode）中の処理 ---
        if self.intake.active:
            q_topic = self.intake.get_next_question_topic()
            self.intake.record_answer(q_topic, text_input)
            state = estimate_state(text_input)
            
            if self.intake.is_finished():
                handoff = self.intake.generate_handoff_note()
                
                # サマリーの生成
                summary_lines = [
                    "・疲労感: " + ("強め" if state.energy < 0.4 else "普通"),
                    "・睡眠: " + ("不調の可能性" if state.sleepiness > 0.5 else "良好"),
                    "・不安感: " + ("高め" if state.stress > 0.5 else "落ち着いている様子"),
                    "・会話圧: 低圧応対推奨"
                ]
                summary = "\n".join(summary_lines)
                
                self.intake.stop_intake()
                return self._post_process_response(AgentResponse(
                    text="ここまで話してくださって、ありがとうございます。今の内容を、あとで見返しやすい形にそっとまとめました。",
                    state=state,
                    mode=Mode.QUIET_SUPPORT,
                    strategy=AgentStrategy(
                        advice_mode="OFF",
                        listening_mode=True,
                        speech_density="LOW",
                        pause_length="LONG",
                        emotional_tone="Gentle",
                        goal="Finish intake"
                    ),
                    handoff_note=handoff,
                    intake_summary=summary,
                    intake_active=False,
                    red_flags=self.intake.red_flags
                ), text_input)
            
            # 次の質問を生成（Gemini優先）
            next_topic = self.intake.get_next_question_topic()
            if self.gemini.is_available:
                next_q = self.gemini.generate_next_intake_question(self.intake.history)
            else:
                next_q = f"続けられそうなら、{next_topic}について少しだけ教えてください。無理のない範囲で大丈夫です。"
                
            return self._post_process_response(AgentResponse(
                text=next_q,
                state=HumanState(energy=0.4),
                mode=Mode.LISTENING_FIRST,
                strategy=AgentStrategy(
                    advice_mode="OFF",
                    listening_mode=True,
                    speech_density="MEDIUM",
                    pause_length="MEDIUM",
                    emotional_tone="Gentle",
                    goal="Continue intake"
                ),
                intake_active=True,
                red_flags=self.intake.red_flags
            ), text_input)

        # --- 1. 固定デモシナリオの検出 ---
        scenario_id = detect_demo_scenario(text_input)
        if scenario_id:
            scenario = get_demo_response(scenario_id)
            if scenario:
                strategy = determine_strategy(scenario.mode, scenario.state)
                strategy.pressure_level = scenario.pressure_level
                strategy.facs_hint = scenario.facs_hint
                
                is_english = (profile.get("language") == "EN") if profile else False
                lang_code = "EN" if is_english else "JP"
                
                # デモ用にも Staff Note 等を生成（ルールベース）
                diff = compare_with_baseline(text_input, asdict(scenario.state), profile or {})
                proposal = generate_care_proposal(scenario.state, scenario.mode, scenario.pressure_level, language=lang_code)
                note = generate_staff_note(text_input, scenario.state, proposal, scenario.pressure_level, diff, language=lang_code)
                
                response_text = scenario.response_en if (is_english and scenario.response_en) else scenario.response
                
                return self._post_process_response(AgentResponse(
                    text=response_text,
                    state=scenario.state,
                    mode=scenario.mode,
                    strategy=strategy,
                    scenario_id=scenario.scenario_id,
                    pressure_level=scenario.pressure_level,
                    facs_hint=scenario.facs_hint,
                    baseline_diff=diff,
                    care_proposal=proposal,
                    staff_note=note
                ), text_input)

        # --- 2. 状態推定 (Gemini優先) ---
        state_dict = None
        if self.gemini.is_available:
            state_dict = self.gemini.analyze_human_state(text_input, profile)
        
        if state_dict:
            state = HumanState(**state_dict)
        else:
            state = estimate_state(text_input)

        # --- 3. 問診モードへの自動移行判定 ---
        if self.gemini.is_available and self.gemini.detect_need_for_intake_mode(text_input, asdict(state)):
            # 問診を自動的に開始するかどうかはUIで制御する場合が多いが、ここではフラグだけ立てることも可能
            # ただし、今回は「自分から問いかける」デモを優先するため、UI側でボタン起動する形にする。
            pass

        # --- 4. モード・戦略決定 ---
        mode = select_mode(state)
        strategy = determine_strategy(mode, state)

        # --- 5. 応答生成 (Gemini優先) ---
        response_text = None
        if self.gemini.is_available:
            response_text = self.gemini.generate_low_pressure_response(text_input, asdict(state), profile)
        
        if not response_text:
            response_text = generate_response(text_input, mode, strategy, state)

        # --- 6. Care Loop 解析 ---
        diff = compare_with_baseline(text_input, asdict(state), profile or {})
        
        is_english = (profile.get("language") == "EN") if profile else False
        lang_code = "EN" if is_english else "JP"
        
        if self.gemini.is_available:
            # LLMによる高度な提案とノート生成
            proposal = self.gemini._call_gemini(f"現在の状態 {asdict(state)} に基づき、ユーザーへの小さなケア提案を生成してください。1文で。") or generate_care_proposal(state, mode, strategy.pressure_level, language=lang_code)
            staff_note = self.gemini.generate_staff_note(text_input, asdict(state), diff) or generate_staff_note(text_input, state, proposal, strategy.pressure_level, diff, language=lang_code)
        else:
            proposal = generate_care_proposal(state, mode, strategy.pressure_level, language=lang_code)
            staff_note = generate_staff_note(text_input, state, proposal, strategy.pressure_level, diff, language=lang_code)

        return self._post_process_response(AgentResponse(
            text=response_text,
            state=state,
            mode=mode,
            strategy=strategy,
            pressure_level=strategy.pressure_level,
            baseline_diff=diff,
            care_proposal=proposal,
            staff_note=staff_note
        ), text_input)

    def process_accessibility_input(self, button_key: str, language: str = "JP") -> AgentResponse:
        """
        アクセシビリティタブからの簡易入力ボタンを処理し、仮のHumanStateとAgentResponseを返す。
        """
        from .state_engine import HumanState
        from .mode_selector import Mode
        from .behavior_policy import AgentStrategy
        from .proactive_care import generate_care_proposal, generate_staff_note
        
        # デフォルト値
        state = HumanState()
        listening_mode = getattr(Mode, "LISTENING_FIRST", getattr(Mode, "LISTENING", Mode.LOW_PRESSURE))
        guidance_mode = getattr(Mode, "GENTLE_GUIDANCE", getattr(Mode, "ADVICE", Mode.LOW_PRESSURE))
        mode = listening_mode
        pressure_level = "LOW"
        text = ""
        red_flags = []
        
        # 英語キーから日本語ラベルへのマッピング（Staff Note等で使用）
        label_map = {
            "tsurai": "つらい",
            "fuan": "不安",
            "tsukarete": "疲れた",
            "nemurenai": "眠れない",
            "itai": "痛い",
            "ikigurushii": "息苦しい",
            "kiite_hoshii": "ただ聞いてほしい",
            "seiri_shitai": "言葉にしたい",
            "kazoku_memo": "家族に伝えるメモを作りたい",
            "moji": "文字で答える",
            "button_only": "ボタンだけで答える",
            "short": "返事は短くしてほしい",
            "no_talk": "今は話したくない",
            "later": "あとで続けたい"
        }
        if language == "EN":
            label_map = {
                "tsurai": "Painful",
                "fuan": "Anxious",
                "tsukarete": "Tired",
                "nemurenai": "Can't sleep",
                "itai": "Physical pain",
                "ikigurushii": "Short of breath",
                "kiite_hoshii": "Just want a listener",
                "seiri_shitai": "Want to organize thoughts",
                "kazoku_memo": "Create a note for family",
                "moji": "Respond with text",
                "button_only": "Respond with buttons",
                "short": "Short responses preferred",
                "no_talk": "Don't want to talk now",
                "later": "Continue later"
            }
        button_label = label_map.get(button_key, button_key)
        
        # 状態ボタン
        if button_key == "tsurai":
            if language == "EN":
                text = "I hear you, and thank you for pressing this button to let me know. You can leave your painful feelings right here."
            else:
                text = "つらいお気持ちのなか、ボタンを押して教えてくださりありがとうございます。少しでもそのお気持ちをここに置いていってくださいね。"
            state = HumanState(stress=0.8, energy=0.2, need_listening=0.9, need_advice=0.2, loneliness=0.5, sleepiness=0.3)
            pressure_level = "VERY_LOW"
        elif button_key == "fuan":
            if language == "EN":
                text = "It feels like your mind is racing. You don't have to put everything into words right now. Let's just take a deep breath together."
            else:
                text = "何だか心が落ち着かないのですね。不安なときは、無理に言葉にされなくても大丈夫です。少し深呼吸をしてみましょうか。"
            state = HumanState(stress=0.7, energy=0.3, need_listening=0.8, need_advice=0.3, loneliness=0.6, sleepiness=0.2)
            pressure_level = "VERY_LOW"
        elif button_key == "tsukarete":
            if language == "EN":
                text = "Thank you for working so hard. Your mind and body must be exhausted. Please relax and lie down."
            else:
                text = "本当にお疲れ様です。今日は心も体もたくさん動かされたのですね。どうぞ肩の力を抜いて、少し横になってくださいね。"
            state = HumanState(stress=0.6, energy=0.1, need_listening=0.7, need_advice=0.1, loneliness=0.4, sleepiness=0.6)
            pressure_level = "VERY_LOW"
        elif button_key == "nemurenai":
            if language == "EN":
                text = "It is tough when you can't sleep. No need to rush into sleeping. Just closing your eyes and being here is enough."
            else:
                text = "夜が更けても眠れないのは辛いですね。眠ろうと焦る必要はありません。ただ目を閉じて、静かな時間を過ごすだけでも体は休まりますよ。"
            state = HumanState(stress=0.5, energy=0.1, need_listening=0.6, need_advice=0.4, loneliness=0.5, sleepiness=0.8)
            pressure_level = "VERY_LOW"
        elif button_key == "itai":
            if language == "EN":
                text = "I am very sorry to hear you are in pain. If the pain is severe, please do not hesitate to contact a medical professional."
            else:
                text = "お体のどこかに痛みがあるのですね。それはとてもお辛い状態です。もし痛みが強い場合や続く場合は、無理をせず医療機関へのご相談をご検討くださいね。"
            state = HumanState(stress=0.8, energy=0.2, need_listening=0.5, need_advice=0.6)
            pressure_level = "LOW"
        elif button_key == "ikigurushii":
            if language == "EN":
                text = "You are experiencing shortness of breath. That must feel very scary. Please try focusing on breathing out slowly. If it is severe, please contact emergency services immediately."
            else:
                text = "息苦しさを感じていらっしゃるのですね。とても不安な状態だと思います。まずはゆっくりと息を吐くことを意識してみてください。※もし呼吸困難が激しい場合は、速やかに専門機関や救急車を呼ぶなど、安全確保を最優先してください。"
            state = HumanState(stress=0.9, energy=0.1, need_listening=0.7, need_advice=0.6)
            pressure_level = "MEDIUM"
            red_flag_label = "Shortness of breath detected" if language == "EN" else "呼吸困難・息苦しさの兆候"
            red_flags = [{"label": red_flag_label, "level": "high"}]
        elif button_key == "kiite_hoshii":
            if language == "EN":
                text = "I understand completely that you just want a listener right now without solutions. Please share whatever you want at your own pace."
            else:
                text = "解決策はいらず、ただ誰かに聞いてほしいということですね。よく分かります。どうぞ、あなたのペースで、話したいことを何でも話してください。"
            state = HumanState(stress=0.4, energy=0.4, need_listening=1.0, need_advice=0.0)
            pressure_level = "VERY_LOW"
        elif button_key == "seiri_shitai":
            if language == "EN":
                text = "You'd like to put your thoughts into words. Feel free to just drop the most prominent thought here. It doesn't have to be long."
            else:
                text = "頭の中にあるものを、少し言葉にしたい感じなのですね。今いちばん気になっていることを、短く置くだけで大丈夫です。"
            state = HumanState(stress=0.5, energy=0.5, need_listening=0.6, need_advice=0.7)
            mode = guidance_mode
            pressure_level = "LOW"
        elif button_key == "kazoku_memo":
            if language == "EN":
                text = "Creating a note for your family or caregivers. Let's start with the one most important thing you wish to share."
            else:
                text = "ご家族に伝えるためのメモですね。まずは、一番伝えたいことをひとつだけ置いてみましょう。"
            state = HumanState(stress=0.6, energy=0.3, need_listening=0.5, need_advice=0.8)
            mode = guidance_mode
            pressure_level = "LOW"
            
        # 返答負荷ボタン
        elif button_key == "moji":
            if language == "EN":
                text = "Responding with text input. Please type whatever you can write easily."
            else:
                text = "文字での入力ですね。どうぞ、ご自身のキーボードやフリック入力で、書きやすい言葉から入力してください。"
            state = HumanState(need_listening=0.7, energy=0.4)
        elif button_key == "button_only":
            if language == "EN":
                text = "Understood. I will offer buttons so you can continue just by clicking."
            else:
                text = "かしこまりました。画面上のボタンを押すだけでやり取りを進められるよう、こちらから選択肢を提示しますね。"
            state = HumanState(need_listening=0.5, energy=0.3)
        elif button_key == "short":
            if language == "EN":
                text = "Understood. I will make my responses as short and simple as possible to ease your load."
            else:
                text = "分かりました。私の返答はできるだけ短くシンプルにしますね。ご負担を減らしましょう。"
            state = HumanState(need_listening=0.5, energy=0.3)
        elif button_key == "no_talk":
            if language == "EN":
                text = "You don't want to talk right now. That is perfectly fine. You don't have to say anything. Just relax and be comfortable."
            else:
                text = "今は話したくない気分なのですね。当然のことです。無理に話す必要はありません。ただここに居るだけで大丈夫ですので、ゆっくり休んでください。"
            state = HumanState(stress=0.7, energy=0.1, need_listening=0.1)
            pressure_level = "VERY_LOW"
        elif button_key == "later":
            if language == "EN":
                text = "Understood. Please feel free to come back and talk whenever you are ready and feeling better. I'll be here."
            else:
                text = "かしこまりました。お気持ちや体調が良いときに、またいつでも続きをお話ししに来てくださいね。お待ちしております。"
            state = HumanState(energy=0.3)
            
        strategy = AgentStrategy(
            advice_mode="ON" if mode == guidance_mode else "OFF",
            listening_mode=True if mode == listening_mode else False,
            speech_density="LOW" if pressure_level in ["VERY_LOW", "LOW"] else "MEDIUM",
            pause_length="LONG" if pressure_level in ["VERY_LOW", "LOW"] else "MEDIUM",
            emotional_tone="Gentle",
            goal=f"Accessibility helper: {button_key}"
        )
        
        diff = []
        proposal = generate_care_proposal(state, mode, pressure_level, language=language)
        note = generate_staff_note(f"Accessibility helper: {button_label}" if language == "EN" else f"アクセシビリティ簡易入力: {button_label}", state, proposal, pressure_level, diff, language=language)
        
        # 「整理のサマリー」の作成
        if language == "EN":
            summary_lines = [
                f"・Concern (Accessibility): {button_label}",
                f"・Fatigue/Stress state: " + ("High" if state.stress > 0.6 or state.energy < 0.3 else "Normal"),
                f"・Rest recommendations: " + ("Rest/Sleep management suggested" if state.sleepiness > 0.6 or state.energy < 0.2 else "Stable observation"),
                f"・Conversation pressure: {pressure_level} recommended"
            ]
        else:
            summary_lines = [
                f"・主訴（やさしい入力）: {button_label}",
                f"・疲労/ストレス状態: " + ("強め" if state.stress > 0.6 or state.energy < 0.3 else "普通"),
                f"・睡眠/安静状態: " + ("安静・睡眠調整推奨" if state.sleepiness > 0.6 or state.energy < 0.2 else "落ち着きを見守り中"),
                f"・会話圧: {pressure_level} 応対推奨"
            ]
        intake_summary = "\n".join(summary_lines)

        return self._post_process_response(AgentResponse(
            text=text,
            state=state,
            mode=mode,
            strategy=strategy,
            pressure_level=pressure_level,
            baseline_diff=diff,
            care_proposal=proposal,
            staff_note=note,
            intake_summary=intake_summary,
            red_flags=red_flags
        ), button_label)

    def _post_process_response(self, response: AgentResponse, text_input: str = "") -> AgentResponse:
        from .emotion_engine import EmotionEngine
        from .persona_guard import PersonaGuard
        
        ee = EmotionEngine()
        pg = PersonaGuard()

        response = self._apply_naomi_core_layer(response)

        def has_japanese(text: str) -> bool:
            return any(
                "\u3040" <= ch <= "\u30ff" or "\u4e00" <= ch <= "\u9fff"
                for ch in text
            )

        is_english_response = not has_japanese(text_input) and not has_japanese(response.text)
        
        # 1. 感情適応（EmotionEngine）
        adapted_text = response.text if is_english_response else ee.adjust_response(response.text, response.state)
        
        # 2. 安全フィルタ（PersonaGuard）
        sanitized_text = pg.sanitize(adapted_text, text_input)
        
        response.text = sanitized_text
        
        if response.staff_note:
            response.staff_note = pg.sanitize(response.staff_note, text_input)
        if response.care_proposal:
            response.care_proposal = pg.sanitize(response.care_proposal, text_input)
        if response.intake_summary:
            response.intake_summary = pg.sanitize(response.intake_summary, text_input)
            
        return response

    def _apply_naomi_core_layer(self, response: AgentResponse) -> AgentResponse:
        """
        NAOMI Core Layer.
        状態推定、Listening First、Pressure Control、認知負荷軽減を全モードに薄く適用する。
        UIでは機能名として見せず、「接し方」そのものに反映する。
        """
        state = response.state
        strategy = response.strategy
        high_red_flag = any(flag.get("level") == "high" for flag in response.red_flags)
        needs_quiet_layer = (
            state.need_listening >= 0.6
            or state.stress >= 0.6
            or state.energy <= 0.3
            or state.reassurance_need >= 0.6
            or state.physical_distress >= 0.5
        )

        if needs_quiet_layer:
            strategy.listening_mode = True
            strategy.speech_density = "LOW"
            strategy.pause_length = "LONG"
            if strategy.advice_mode == "ON" and state.need_advice < 0.75:
                strategy.advice_mode = "WAIT"

            pressure_order = {"VERY_LOW": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
            target_pressure = "LOW"
            if state.energy <= 0.2 or state.stress >= 0.8 or state.reassurance_need >= 0.8:
                target_pressure = "VERY_LOW"
            if high_red_flag:
                target_pressure = "MEDIUM"

            current = response.pressure_level or strategy.pressure_level
            if pressure_order.get(target_pressure, 1) < pressure_order.get(current, 2):
                response.pressure_level = target_pressure
                strategy.pressure_level = target_pressure

        response.strategy = strategy
        return response
