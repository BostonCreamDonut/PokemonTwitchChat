import socket, ssl, time

def parse_tags(raw):
    tags={}
    for part in raw.split(";") if raw else []:
        if "=" in part:
            k,v=part.split("=",1)
            tags[k]=v.replace(r"\s"," ").replace(r"\:",";")
    return tags

class TwitchIRCClient:
    HOST="irc.chat.twitch.tv"; PORT=6697
    def __init__(self,username,access_token,channel,on_message,on_event,stop_event):
        self.username=username.lower()
        self.access_token=access_token
        self.channel=channel.lower().lstrip("#")
        self.on_message=on_message
        self.on_event=on_event
        self.stop_event=stop_event
        self.sock=None
        self.connected=False

    def _send(self,line):
        self.sock.sendall((line+"\r\n").encode())

    def connect(self):
        raw=socket.create_connection((self.HOST,self.PORT),timeout=15)
        self.sock=ssl.create_default_context().wrap_socket(raw,server_hostname=self.HOST)
        self.sock.settimeout(1)
        self._send(f"PASS oauth:{self.access_token}")
        self._send(f"NICK {self.username}")
        self._send("CAP REQ :twitch.tv/tags twitch.tv/commands twitch.tv/membership")
        self._send(f"JOIN #{self.channel}")
        self.connected=True

    @staticmethod
    def _split(line):
        tags={}
        if line.startswith("@"):
            raw,line=line[1:].split(" ",1)
            tags=parse_tags(raw)
        return tags,line

    def listen(self):
        buf=""
        while not self.stop_event.is_set():
            try:
                data=self.sock.recv(4096)
                if not data: raise ConnectionError("Twitch closed connection")
                buf+=data.decode(errors="replace")
            except socket.timeout:
                continue
            while "\r\n" in buf:
                line,buf=buf.split("\r\n",1)
                if line.startswith("PING"):
                    self._send("PONG :tmi.twitch.tv"); continue
                if "Login authentication failed" in line:
                    raise RuntimeError("Twitch login failed")
                tags,payload=self._split(line)
                if " USERNOTICE " in payload:
                    self.on_event(tags)
                    continue
                if " PRIVMSG " in payload:
                    try:
                        prefix,rest=payload.split(" PRIVMSG ",1)
                        user=prefix.lstrip(":").split("!",1)[0]
                        _,msg=rest.split(" :",1)
                        self.on_message(user,msg,tags)
                    except ValueError:
                        pass

    def run_forever(self):
        backoff=2
        while not self.stop_event.is_set():
            try:
                self.connect(); backoff=2; self.listen()
            except Exception as e:
                self.connected=False
                self.close()
                if self.stop_event.is_set(): break
                print(f"Twitch disconnected: {e}; retrying in {backoff}s")
                self.stop_event.wait(backoff)
                backoff=min(backoff*2,60)

    def close(self):
        self.connected=False
        if self.sock:
            try:self.sock.close()
            except:pass
            self.sock=None
