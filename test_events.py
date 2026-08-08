#!/usr/bin/env python3
import json,time
from pathlib import Path
BASE=Path(__file__).resolve().parent
CFG=json.loads((BASE/"config.json").read_text())
P=BASE/CFG["overlay"]["event_file"]

def send(kind,title,subtitle,extra=None,duration=5):
    P.write_text(json.dumps({"id":time.time_ns(),"kind":kind,"title":title,"subtitle":subtitle,
                             "extra":extra or {},"duration":duration,"created_at":time.time()}))
    print("Sent:",title)

menu={
"1":("subscriber","NEW TRAINER JOINED!","TestTrainer subscribed • votes count ×2",{},5),
"2":("gift_sub","A POKé BALL WAS GIFTED!","TestTrainer gifted a sub to LuckyViewer",{"recipient":"LuckyViewer"},6),
"3":("cheer","TRAINER USED AN ITEM!","TestTrainer used 100 Bits • DOUBLE VOTES for 30s",{"bits":100,"effect":"double_votes"},5),
"4":("cheer","TRAINER USED AN ITEM!","TestTrainer used 500 Bits • SPEED ROUND for 60s",{"bits":500,"effect":"speed_round"},5),
"5":("cheer","TRAINER USED AN ITEM!","TestTrainer used 1,000 Bits • CHAOS MODE for 60s",{"bits":1000,"effect":"chaos"},5),
"6":("cheer","TRAINER USED AN ITEM!","TestTrainer used 1,500 Bits • ANARCHY MODE for 60s",{"bits":1500,"effect":"anarchy"},5),
"7":("cheer","TRAINER USED AN ITEM!","TestTrainer used 2,000 Bits • REVERSE CONTROLS for 60s",{"bits":2000,"effect":"reverse_controls"},5),
}
while True:
    print("\n1 Sub  2 Gift Sub  3 100 Bits  4 500 Bits  5 1000 Bits  6 1500 Bits  7 2000 Bits  q Quit")
    c=input("> ").strip().lower()
    if c=="q":break
    if c in menu:send(*menu[c])
