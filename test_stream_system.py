#!/usr/bin/env python3
import json,time
from pathlib import Path
BASE=Path(__file__).resolve().parent
CFG=json.loads((BASE/"config.json").read_text())
EP=BASE/CFG["overlay"]["event_file"]; DP=BASE/CFG["overlay"]["dialogue_file"]; BP=BASE/CFG["overlay"]["boot_file"]

def write(p,data):
    data["id"]=time.time_ns(); data["created_at"]=time.time(); p.write_text(json.dumps(data))

while True:
    print("""
1 Sub alert
2 Gift sub
3 World event: Double Votes
4 Trainer Card
5 Gym Challenge start
6 Gym Challenge cleared
7 NPC: Professor Oak
8 NPC: Team Rocket
9 Boot screen step
q Quit
""")
    c=input("> ").strip().lower()
    if c=="q":break
    if c=="1":write(EP,{"kind":"subscriber","title":"NEW TRAINER JOINED!","subtitle":"TestTrainer subscribed • votes count ×2","extra":{},"duration":4})
    elif c=="2":write(EP,{"kind":"gift_sub","title":"A POKé BALL WAS GIFTED!","subtitle":"TestTrainer gifted 5 subs!","extra":{},"duration":4.5})
    elif c=="3":write(EP,{"kind":"world_event","title":"DOUBLE VOTES","subtitle":"Active for 30 seconds","extra":{"effect":"double_votes"},"duration":3.2})
    elif c=="4":write(EP,{"kind":"trainer_card","title":"TRAINER Lv. 12","subtitle":"TestTrainer • 1,240 votes • 3 events","extra":{"xp_into_level":42,"xp_per_level":100,"weighted_votes":1750},"duration":6})
    elif c=="5":write(EP,{"kind":"gym_start","title":"GYM CHALLENGE!","subtitle":"Cast 75 weighted votes before time runs out!","extra":{},"duration":5})
    elif c=="6":write(EP,{"kind":"gym_win","title":"CHALLENGE CLEARED!","subtitle":"Reward: DOUBLE VOTES","extra":{},"duration":5})
    elif c=="7":write(DP,{"speaker":"Professor Oak","text":"The trainers are fired up! Everyone's vote power has doubled!","duration":4.5})
    elif c=="8":write(DP,{"speaker":"Team Rocket","text":"Prepare for trouble! Every winning move gets an extra A press!","duration":4.5})
    elif c=="9":write(BP,{"step":"CONNECTING TO TWITCH","detail":"Opening trainer network…","done":False})
