import json, urllib.request, urllib.error

class TokenValidator:
    URL="https://id.twitch.tv/oauth2/validate"
    def __init__(self, access_token, expected_username):
        self.access_token=access_token
        self.expected_username=expected_username.lower()

    def validate(self):
        req=urllib.request.Request(
            self.URL, headers={"Authorization":f"OAuth {self.access_token}"}
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                data=json.loads(r.read().decode())
        except Exception as e:
            return False, str(e)
        login=str(data.get("login","")).lower()
        if login and login != self.expected_username:
            return False, f"Token belongs to {login}, expected {self.expected_username}"
        return True, data
