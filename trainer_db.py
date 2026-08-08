import sqlite3
from pathlib import Path

class TrainerDB:
    def __init__(self, path, level_xp=100):
        self.path = Path(path)
        self.level_xp = max(1, int(level_xp))
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS trainers(
            username TEXT PRIMARY KEY,
            votes_cast INTEGER NOT NULL DEFAULT 0,
            weighted_votes INTEGER NOT NULL DEFAULT 0,
            events_triggered INTEGER NOT NULL DEFAULT 0,
            bits_used INTEGER NOT NULL DEFAULT 0,
            xp INTEGER NOT NULL DEFAULT 0
        )
        """)
        self.conn.commit()

    def record_vote(self, username, weight, xp=1):
        self.conn.execute("""
        INSERT INTO trainers(username,votes_cast,weighted_votes,xp)
        VALUES(?,?,?,?)
        ON CONFLICT(username) DO UPDATE SET
          votes_cast=votes_cast+1,
          weighted_votes=weighted_votes+excluded.weighted_votes,
          xp=xp+excluded.xp
        """, (username.lower(), 1, int(weight), int(xp)))
        self.conn.commit()

    def record_event(self, username, bits=0):
        if not username:
            return
        self.conn.execute("""
        INSERT INTO trainers(username,events_triggered,bits_used)
        VALUES(?,?,?)
        ON CONFLICT(username) DO UPDATE SET
          events_triggered=events_triggered+1,
          bits_used=bits_used+excluded.bits_used
        """, (username.lower(), 1, int(bits)))
        self.conn.commit()

    def card(self, username):
        cur=self.conn.execute("""
        SELECT username,votes_cast,weighted_votes,events_triggered,bits_used,xp
        FROM trainers WHERE username=?
        """,(username.lower(),))
        r=cur.fetchone()
        if not r:
            return None
        level = 1 + r[5] // self.level_xp
        return {
            "username":r[0],"votes_cast":r[1],"weighted_votes":r[2],
            "events_triggered":r[3],"bits_used":r[4],"xp":r[5],
            "level":level,"xp_into_level":r[5]%self.level_xp,
            "xp_per_level":self.level_xp
        }

    def top(self, limit=3):
        rows=self.conn.execute("""
        SELECT username,votes_cast,weighted_votes,events_triggered,bits_used,xp
        FROM trainers ORDER BY xp DESC, weighted_votes DESC LIMIT ?
        """,(int(limit),)).fetchall()
        return [{
            "username":r[0],"votes_cast":r[1],"weighted_votes":r[2],
            "events_triggered":r[3],"bits_used":r[4],"xp":r[5],
            "level":1+r[5]//self.level_xp
        } for r in rows]
