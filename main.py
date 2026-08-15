#!/usr/bin/env python3
import json, logging, random, re, signal, subprocess, sys, threading, time, urllib.error, urllib.request
from collections import Counter
from pathlib import Path

from input_controller import InputController
from twitch_irc import TwitchIRCClient
from token_validator import TokenValidator
from trainer_db import TrainerDB
from sound_engine import SoundEngine
from event_engine import EventEngine
from game_state import read_state, update_state
from auto_game_state import AutoGameStateServer

BASE=Path(__file__).resolve().parent
CFG=json.loads((BASE/"config.json").read_text(encoding="utf-8"))
for runtime_dir in ("data", "logs", "saves"):
    (BASE / runtime_dir).mkdir(exist_ok=True)
STOP=threading.Event()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler(),
              logging.FileHandler(BASE/"logs"/"twitchplays.log",encoding="utf-8")]
)
log=logging.getLogger("tpp")

def load_token():
    p=BASE/"secrets.env"
    if not p.exists(): raise SystemExit("Missing secrets.env")
    for line in p.read_text().splitlines():
        if line.startswith("TWITCH_ACCESS_TOKEN="):
            token=line.split("=",1)[1].strip()
            if token.startswith("oauth:"): token=token[6:]
            if token and "PASTE_NEW" not in token: return token
    raise SystemExit("TWITCH_ACCESS_TOKEN not configured")

def is_sub(tags):
    if tags.get("subscriber")=="1": return True
    return any(x.startswith(("subscriber/","founder/")) for x in tags.get("badges","").split(","))

def is_admin(user, tags):
    channel = CFG["twitch"]["channel"].lower()
    badges = tags.get("badges", "")
    return (
        user.lower() == channel
        or tags.get("mod") == "1"
        or "broadcaster/" in badges
    )

def parse_twitch_emotes(message, raw):
    emotes = []
    if not raw:
        return emotes
    for part in raw.split("/"):
        if ":" not in part:
            continue
        emote_id, ranges = part.split(":", 1)
        for span in ranges.split(","):
            if "-" not in span:
                continue
            try:
                start, end = (int(value) for value in span.split("-", 1))
            except ValueError:
                continue
            text = message[start:end + 1]
            if text:
                emotes.append({"provider": "twitch", "id": emote_id, "start": start, "end": end, "text": text})
    return sorted(emotes, key=lambda item: item["start"])

def fetch_json(url, timeout=5):
    req = urllib.request.Request(url, headers={"User-Agent": "PokemonTwitchChat/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))

def add_emote(out, code, provider, emote_id, url):
    code = str(code or "").strip()
    if not code or not url:
        return
    out[code] = {"provider": provider, "id": str(emote_id), "url": url}

def ffz_url(urls):
    if not isinstance(urls, dict):
        return ""
    url = urls.get("2") or urls.get("1") or urls.get("4")
    if not url:
        return ""
    return "https:" + url if url.startswith("//") else url

def parse_ffz_sets(data):
    out = {}
    for emote_set in data.get("sets", {}).values():
        for emote in emote_set.get("emoticons", []):
            add_emote(out, emote.get("name"), "ffz", emote.get("id"), ffz_url(emote.get("urls")))
    return out

def seven_tv_url(emote):
    data = emote.get("data") or emote
    host = data.get("host", {})
    base = host.get("url", "")
    if base.startswith("//"):
        base = "https:" + base
    if not base:
        return ""
    files = host.get("files", [])
    preferred = ("2x_static.gif", "1x_static.gif", "2x_static.webp", "1x_static.webp", "2x.gif", "1x.gif")
    by_name = {item.get("name"): item for item in files}
    by_static = {item.get("static_name"): item for item in files if item.get("static_name")}
    for name in preferred:
        if name in by_static:
            return f"{base}/{by_static[name]['static_name']}"
        if name in by_name:
            return f"{base}/{by_name[name]['name']}"
    if files and files[0].get("name"):
        return f"{base}/{files[0]['name']}"
    return ""

def parse_seven_tv_set(data):
    out = {}
    emote_set = data.get("emote_set") if isinstance(data.get("emote_set"), dict) else data
    for emote in emote_set.get("emotes", []):
        add_emote(out, emote.get("name"), "7tv", emote.get("id"), seven_tv_url(emote))
    return out

class App:
    def __init__(self, token):
        self.token=token
        self.lock=threading.RLock()
        self.controls=CFG["controls"]
        self.controller=InputController(CFG["input"])
        ss=CFG["stream_system"]

        self.sound=SoundEngine(BASE/"assets"/"sounds",ss["sound_enabled"],ss["sound_volume"])
        self.events=EventEngine(BASE,CFG,self.sound)
        self.db=TrainerDB(BASE/"data"/"trainers.sqlite3", ss["trainer_level_xp"])
        self.auto_game_state=AutoGameStateServer(CFG, STOP)

        self.base_window=float(CFG["mode"]["vote_window_seconds"])
        self.vote_window=self.base_window
        self.round_end=time.monotonic()+self.vote_window
        self.votes=Counter(); self.raw=Counter(); self.user_votes={}; self.order={}; self.seq=0
        self.recent=[]; self.chat_log=[]; self.last_winner=None; self.total_votes=0; self.total_weighted=0
        self.players=set(); self.rounds=0; self.effects={}
        self.third_party_emotes={}
        self.third_party_emote_loads=set()

        self.state_path=BASE/CFG["overlay"]["state_file"]
        self.game_state_path=BASE/CFG["overlay"].get("game_state_file","game_state.json")
        if not self.game_state_path.exists():
            update_state({})
        self.overlay_proc=None

        self.gym=None
        self.next_gym_at=time.monotonic()+ss["gym_challenge_interval_minutes"]*60

        tw=CFG["twitch"]
        self.chat=TwitchIRCClient(
            tw["bot_username"],token,tw["channel"],
            self.on_message,self.on_notice,STOP
        )
        self.start_third_party_emote_load()

    def boot_sequence(self):
        if not CFG["stream_system"].get("show_boot_sequence",True):
            return
        delay=float(CFG["stream_system"].get("boot_step_seconds",.7))
        steps=[
            ("CONNECTING TO TWITCH","Opening trainer network…"),
            ("LOADING SAVE","Checking adventure state…"),
            ("CHECKING EMULATOR","mGBA input controller ready."),
            ("LOADING OVERLAY","FireRed interface online."),
            ("READY!","Chat controls the adventure.")
        ]
        self.sound.play("boot.wav")
        for i,(s,d) in enumerate(steps):
            self.events.boot(s,d,i==len(steps)-1)
            time.sleep(delay)

    def effect_active(self,name):
        d=self.effects.get(name)
        if not d:return False
        if time.monotonic()>=d["end"]:
            self.effects.pop(name,None)
            return False
        return True

    def king_mode_owner(self):
        d=self.effects.get("king_mode")
        if not d:
            return None
        if time.monotonic()>=d["end"]:
            self.effects.pop("king_mode",None)
            return None
        owner=(d.get("source") or "").strip().lower()
        return owner or None

    def clear_round_votes(self):
        self.votes=Counter(); self.raw=Counter(); self.user_votes={}; self.order={}; self.seq=0

    def activate_effect(self,effect,duration,user="",amount=0):
        self.effects[effect]={"end":time.monotonic()+duration,"source":user,"amount":amount}
        labels={"speed_round":"SPEED ROUND","chaos":"CHAOS MODE",
                "reverse_controls":"REVERSE CONTROLS",
                "king_mode":"KING MODE"}
        sound={"speed_round":"speed_round.wav",
               "chaos":"chaos.wav",
               "reverse_controls":"reverse_controls.wav",
               "king_mode":"gym_win.wav"}.get(effect)
        subtitle=f"Active for {int(duration)} seconds"
        if effect=="king_mode" and user:
            subtitle=f"{user} is king for {int(duration)} seconds"
        self.events.alert("world_event",labels.get(effect,effect.upper()),
                           subtitle,
                           {"effect":effect,"user":user,"source":user,"amount":amount,"bits":amount,"duration":duration},3.2,sound)
        if user:
            self.db.record_event(user, amount)
        if effect=="king_mode":
            with self.lock:
                self.clear_round_votes()
                self.round_end=time.monotonic()+self.base_window
        dialogue={
            "speed_round":("Bike Shop","Hold on tight! Voting just got a whole lot faster!"),
            "chaos":("Team Rocket","Prepare for trouble! Every command goes through right now!"),
            "reverse_controls":("Psychic Trainer","Your sense of direction feels... backwards."),
            "king_mode":("Elite Trainer",f"{user} is king now. Hold on tight!")
        }.get(effect)
        if dialogue:
            threading.Timer(1.0, lambda: self.events.dialogue(*dialogue)).start()

    def weight(self,tags):
        return CFG["voting"]["subscriber_weight"] if is_sub(tags) else CFG["voting"]["regular_weight"]

    def on_notice(self,tags):
        msgid=tags.get("msg-id","")
        name=tags.get("display-name") or "Trainer"
        if msgid=="sub":
            months=tags.get("msg-param-cumulative-months","1")
            self.events.alert("subscriber","NEW TRAINER JOINED!",
                              f"{name} subscribed - {months} month(s) - votes count x2",
                              {"user":name,"months":months},4.0,"subscriber.wav")
            self.db.record_event(name)
        elif msgid=="resub":
            months=tags.get("msg-param-cumulative-months","1")
            self.events.alert("resub","WELCOME BACK!",
                              f"{name} resubscribed for {months} month(s)",
                              {"user":name,"months":months},4.0,"subscriber.wav")
            self.db.record_event(name)
        elif msgid in ("subgift","anonsubgift"):
            rec=tags.get("msg-param-recipient-display-name","a trainer")
            self.events.alert("gift_sub","A POKé BALL WAS GIFTED!",
                              f"{name} gifted a sub to {rec}",
                              {"user":name,"recipient":rec},4.5,"gift_sub.wav")
            self.db.record_event(name)
        elif msgid in ("submysterygift","anonsubmysterygift"):
            count=tags.get("msg-param-mass-gift-count","?")
            self.events.alert("gift_sub","TRAINER PARTY EXPANDED!",
                              f"{name} gifted {count} subscriptions!",
                              {"user":name,"count":count},4.5,"gift_sub.wav")
            self.db.record_event(name)

    def handle_cheer(self,user,bits):
        rule=None
        for r in CFG["events"]["cheer_effects"]:
            if bits>=r["minimum_bits"]: rule=r
        if rule:
            self.activate_effect(rule["effect"],rule["duration_seconds"],user,bits)
        else:
            self.events.alert("cheer","TRAINER USED AN ITEM!",
                              f"{user} used {bits:,} Bits",{"bits":bits},4.0)
            self.db.record_event(user,bits)

    def mapped_key(self,cmd):
        if self.effect_active("reverse_controls"):
            cmd={"!up":"!down","!down":"!up","!left":"!right","!right":"!left"}.get(cmd,cmd)
        return self.controls[cmd]

    def start_third_party_emote_load(self, room_id=None):
        key = str(room_id or "global")
        with self.lock:
            if key in self.third_party_emote_loads:
                return
            self.third_party_emote_loads.add(key)
        threading.Thread(target=self.load_third_party_emotes, args=(room_id,), daemon=True).start()

    def load_third_party_emotes(self, room_id=None):
        loaded = {}
        jobs = []
        if room_id:
            jobs.extend([
                ("bttv-channel", f"https://api.betterttv.net/3/cached/users/twitch/{room_id}"),
                ("7tv-channel", f"https://7tv.io/v3/users/twitch/{room_id}"),
                ("ffz-room", f"https://api.frankerfacez.com/v1/room/{CFG['twitch']['channel']}"),
            ])
        else:
            jobs.extend([
                ("bttv-global", "https://api.betterttv.net/3/cached/emotes/global"),
                ("7tv-global", "https://7tv.io/v3/emote-sets/global"),
                ("ffz-global", "https://api.frankerfacez.com/v1/set/global"),
            ])

        for kind, url in jobs:
            try:
                data = fetch_json(url)
            except urllib.error.HTTPError as e:
                if e.code != 404:
                    log.info("Could not load %s emotes: HTTP %s", kind, e.code)
                continue
            except Exception as e:
                log.info("Could not load %s emotes: %s", kind, e)
                continue

            if kind.startswith("bttv"):
                if isinstance(data, list):
                    emotes = data
                else:
                    emotes = data.get("channelEmotes", []) + data.get("sharedEmotes", [])
                for emote in emotes:
                    add_emote(loaded, emote.get("code"), "bttv", emote.get("id"), f"https://cdn.betterttv.net/emote/{emote.get('id')}/2x")
            elif kind.startswith("ffz"):
                loaded.update(parse_ffz_sets(data))
            elif kind.startswith("7tv"):
                loaded.update(parse_seven_tv_set(data))

        if loaded:
            with self.lock:
                self.third_party_emotes.update(loaded)
            log.info("Loaded %s third-party emotes%s", len(loaded), f" for room {room_id}" if room_id else "")

    def parse_third_party_emotes(self, message, taken):
        with self.lock:
            emote_map = dict(self.third_party_emotes)
        if not emote_map:
            return []

        out = []
        for match in re.finditer(r"\S+", message):
            code = match.group(0)
            meta = emote_map.get(code)
            if not meta:
                continue
            start, end = match.start(), match.end() - 1
            if any(not (end < used_start or start > used_end) for used_start, used_end in taken):
                continue
            out.append({
                "provider": meta["provider"],
                "id": meta["id"],
                "url": meta["url"],
                "start": start,
                "end": end,
                "text": code,
            })
            taken.append((start, end))
        return out

    def on_message(self,user,msg,tags):
        if tags.get("bits"):
            try:self.handle_cheer(user,int(tags["bits"]))
            except ValueError:pass

        room_id = tags.get("room-id")
        if room_id:
            self.start_third_party_emote_load(room_id)
        twitch_emotes = parse_twitch_emotes(msg, tags.get("emotes", ""))
        taken = [(emote["start"], emote["end"]) for emote in twitch_emotes]
        all_emotes = sorted(twitch_emotes + self.parse_third_party_emotes(msg, taken), key=lambda item: item["start"])
        display_name = tags.get("display-name") or user
        with self.lock:
            self.chat_log.append({
                "username": display_name,
                "message": msg,
                "subscriber": is_sub(tags),
                "emotes": all_emotes,
            })
            self.chat_log=self.chat_log[-80:]

        # lightweight built-in commands
        low=msg.strip().lower()
        if self.handle_game_state_command(user,msg,tags):
            return
        if low=="!trainer":
            card=self.db.card(user)
            if card:
                self.events.alert("trainer_card",
                    f"TRAINER Lv. {card['level']}",
                    f"{user} - {card['votes_cast']:,} votes - {card['events_triggered']} events",
                    card,6.0,None)
            return
        if low=="!toptrainers":
            top=self.db.top(3)
            if top:
                subtitle=" - ".join(f"{i+1}. {t['username']} Lv{t['level']}" for i,t in enumerate(top))
                self.events.alert("leaderboard","TOP TRAINERS",subtitle,{"trainers":top},6.0,None)
            return

        cmd=low
        if cmd not in self.controls:return

        king_owner=self.king_mode_owner()
        if king_owner:
            if user.lower()==king_owner:
                w=self.weight(tags)
                self.db.record_vote(user,w,CFG["stream_system"]["trainer_xp_per_vote"])
                self.controller.press(self.mapped_key(cmd))
                with self.lock:
                    self.recent.append({"username":user,"command":cmd,"subscriber":is_sub(tags),"weight":w})
                    self.recent=self.recent[-30:]
            return

        w=self.weight(tags)
        self.db.record_vote(user,w,CFG["stream_system"]["trainer_xp_per_vote"])

        if self.effect_active("chaos"):
            self.controller.press(self.mapped_key(cmd))
            with self.lock:
                self.recent.append({"username":user,"command":cmd,"subscriber":is_sub(tags),"weight":w})
                self.recent=self.recent[-30:]
            return

        u=user.lower()
        with self.lock:
            if u in self.user_votes:
                old=self.user_votes[u]
                if old["command"]==cmd:return
                self.votes[old["command"]]-=old["weight"]; self.raw[old["command"]]-=1
                if self.votes[old["command"]]<=0:self.votes.pop(old["command"],None)
                if self.raw[old["command"]]<=0:self.raw.pop(old["command"],None)

            self.user_votes[u]={"command":cmd,"weight":w}
            self.votes[cmd]+=w; self.raw[cmd]+=1
            self.seq+=1; self.order.setdefault(cmd,self.seq)
            self.total_votes+=1; self.total_weighted+=w; self.players.add(u)
            self.recent.append({"username":user,"command":cmd,"subscriber":is_sub(tags),"weight":w})
            self.recent=self.recent[-30:]

            if self.gym and self.gym["metric"]=="weighted_votes":
                self.gym["progress"] += w
            if self.gym and self.gym["metric"]=="unique_voters":
                self.gym["voters"].add(u)
                self.gym["progress"] = len(self.gym["voters"])

    def handle_game_state_command(self, user, msg, tags):
        if not is_admin(user, tags):
            return False
        text = msg.strip()
        low = text.lower()
        commands = {
            "!location": "location",
            "!setlocation": "location",
            "!badges": "badges",
            "!setbadges": "badges",
            "!party": "party_size",
            "!setparty": "party_size",
            "!deaths": "deaths",
            "!setdeaths": "deaths",
            "!objective": "objective",
            "!setobjective": "objective",
        }
        if low == "!death":
            current = read_state(CFG)
            update_state({"deaths": int(current.get("deaths", 0)) + 1}, CFG)
            return True
        for prefix, field in commands.items():
            if low == prefix or low.startswith(prefix + " "):
                value = text[len(prefix):].strip()
                if not value:
                    return True
                if field in ("badges", "party_size", "deaths"):
                    try:
                        value = int(value)
                    except ValueError:
                        return True
                update_state({field: value}, CFG)
                return True
        return False

    def choose(self):
        if not self.votes:return None
        m=max(self.votes.values())
        tied=[c for c,v in self.votes.items() if v==m]
        return min(tied,key=lambda c:self.order.get(c,999999))

    def round_worker(self):
        while not STOP.is_set():
            if self.king_mode_owner():
                with self.lock:
                    self.clear_round_votes()
                    self.round_end=time.monotonic()+self.base_window
                STOP.wait(.05)
                continue
            desired=1.0 if self.effect_active("speed_round") else self.base_window
            if desired!=self.vote_window:
                self.vote_window=desired; self.round_end=time.monotonic()+desired
            if time.monotonic()<self.round_end:
                STOP.wait(.05); continue
            with self.lock:
                winner=self.choose()
                if winner:
                    self.last_winner={"command":winner,"votes":self.votes[winner],
                                      "raw_votes":self.raw.get(winner,0),"timestamp":time.time()}
                    self.rounds+=1
                self.votes=Counter(); self.raw=Counter(); self.user_votes={}; self.order={}; self.seq=0
                self.round_end=time.monotonic()+self.vote_window
            if winner:
                self.controller.press(self.mapped_key(winner))

    def gym_worker(self):
        ss=CFG["stream_system"]
        while not STOP.is_set():
            now=time.monotonic()
            if not self.gym and now>=self.next_gym_at:
                template=random.choice(CFG["gym_challenges"])
                self.gym=dict(template)
                self.gym["progress"]=0
                self.gym["voters"]=set()
                self.gym["ends_at"]=now+ss["gym_challenge_duration_seconds"]
                self.events.alert("gym_start","GYM CHALLENGE!",self.gym["description"],
                                  {"challenge":self.gym["name"]},5.0,"gym_start.wav")
                self.events.dialogue("Gym Guide",f"{self.gym['name']} has begun! Work together, trainers!")
            elif self.gym:
                if self.gym["progress"]>=self.gym["target"]:
                    completed=self.gym
                    self.gym=None
                    self.events.alert("gym_win","CHALLENGE CLEARED!",
                                      f"{completed['name']} - Reward: {completed['reward']}",
                                      {"challenge":completed["name"]},5.0,"gym_win.wav")
                    self.activate_effect(completed["reward_effect"],completed["reward_seconds"])
                    self.next_gym_at=now+ss["gym_challenge_interval_minutes"]*60
                elif now>=self.gym["ends_at"]:
                    name=self.gym["name"]
                    self.gym=None
                    self.events.dialogue("Gym Guide",f"{name} ended. You'll get another shot later!")
                    self.next_gym_at=now+ss["gym_challenge_interval_minutes"]*60
            STOP.wait(.2)

    def active_effects(self):
        out=[]
        for k,d in list(self.effects.items()):
            rem=d["end"]-time.monotonic()
            if rem<=0:self.effects.pop(k,None)
            else:out.append({"effect":k,"remaining":rem,"source":d.get("source",""),"amount":d.get("amount",0)})
        return out

    def gym_state(self):
        if not self.gym:return None
        return {
            "name":self.gym["name"],"description":self.gym["description"],
            "progress":self.gym["progress"],"target":self.gym["target"],
            "remaining":max(0,self.gym["ends_at"]-time.monotonic()),
            "reward":self.gym["reward"]
        }

    def state(self):
        with self.lock:
            game = read_state(CFG)
            total=sum(self.votes.values())
            ranked=sorted(self.votes.items(),key=lambda x:(-x[1],self.order.get(x[0],999999)))[:5]
            rows=[{"command":c,"weighted_votes":v,"raw_votes":self.raw.get(c,0),
                   "percent":(100*v/total if total else 0)} for c,v in ranked]
            rem=max(0,self.round_end-time.monotonic())
            return {
                "connected":self.chat.connected,
                "mode":"KING MODE" if self.king_mode_owner() else "CHAOS" if self.effect_active("chaos") else "DEMOCRACY",
                "time_remaining":rem,
                "round_progress":1-rem/self.vote_window if self.vote_window else 1,
                "votes":rows,
                "round_weighted_vote_count":total,
                "round_player_count":len(self.user_votes),
                "recent_commands":self.recent[-7:],
                "recent_chat":self.chat_log[-14:],
                "last_winner":self.last_winner,
                "unique_players":len(self.players),
                "total_votes":self.total_votes,
                "total_weighted_votes":self.total_weighted,
                "total_rounds":self.rounds,
                "active_effects":self.active_effects(),
                "subscriber_multiplier":CFG["voting"]["subscriber_weight"],
                "top_trainers":self.db.top(3),
                "gym_challenge":self.gym_state(),
                "location":game["location"],
                "badges":game["badges"],
                "party_size":game["party_size"],
                "party_fainted":game.get("party_fainted", []),
                "party_species":game.get("party_species", []),
                "deaths":game["deaths"],
                "objective":game["objective"]
            }

    def state_writer(self):
        while not STOP.is_set():
            tmp=self.state_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.state()),encoding="utf-8")
            tmp.replace(self.state_path)
            STOP.wait(1/max(2,CFG["overlay"]["refresh_hz"]))

    def run(self):
        ok,data=TokenValidator(self.token,CFG["twitch"]["bot_username"]).validate()
        if not ok:raise SystemExit(f"Token validation failed: {data}")
        tmp=self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state()),encoding="utf-8")
        tmp.replace(self.state_path)
        if CFG["overlay"].get("enabled", True):
            self.overlay_proc=subprocess.Popen([sys.executable,str(BASE/"overlay_app.py")],cwd=BASE)
        self.auto_game_state.start_thread()
        threading.Thread(target=self.state_writer,daemon=True).start()
        threading.Thread(target=self.round_worker,daemon=True).start()
        threading.Thread(target=self.gym_worker,daemon=True).start()
        self.boot_sequence()
        self.chat.run_forever()

    def stop(self):
        STOP.set(); self.chat.close()
        if self.overlay_proc and self.overlay_proc.poll() is None:
            self.overlay_proc.terminate()

def main():
    app=App(load_token())
    signal.signal(signal.SIGINT,lambda *_:app.stop())
    signal.signal(signal.SIGTERM,lambda *_:app.stop())
    try: app.run()
    finally: app.stop()


if __name__ == "__main__":
    main()
