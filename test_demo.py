# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.')

from agent.core import NaomiAgentCore

core = NaomiAgentCore()

tests = [
    ("最近ちょっと疲れてて…", "tired"),
    ("明日のことを考えると不安で落ち着かない", "anxiety"),
    ("なんか一人でいる感じがして寂しい", "lonely"),
    ("どうしたらいいか教えてほしいけど、正直もう疲れてる", "exhausted_advice"),
    ("楽しかった！", None),
    ("今日はいい天気だね", None),
]

all_pass = True
for text, expected_scenario in tests:
    r = core.process_input(text)
    ok = r.scenario_id == expected_scenario
    if not ok:
        all_pass = False
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] scenario={r.scenario_id} | mode={r.mode.value} | pressure={r.pressure_level} | facs={r.facs_hint}")
    print(f"       Input: {text}")
    print(f"       Response: {r.text[:40]}...")
    print()

if all_pass:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
