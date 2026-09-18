class StateStore:
    def __init__(self):
        self._sessions = {}
        
    def get_session(self, user_id: str) -> dict:
        return self._sessions.get(user_id, {})
        
    def update_session(self, user_id: str, data: dict):
        if user_id not in self._sessions:
            self._sessions[user_id] = {}
        self._sessions[user_id].update(data)
        
    def clear_session(self, user_id: str):
        if user_id in self._sessions:
            del self._sessions[user_id]
            
    def get_context(self, user_id: str, domain: str) -> dict:
        session = self.get_session(user_id)
        return session.get("contexts", {}).get(domain, {})
        
    def set_context(self, user_id: str, domain: str, context: dict):
        if user_id not in self._sessions:
            self._sessions[user_id] = {}
        if "contexts" not in self._sessions[user_id]:
            self._sessions[user_id]["contexts"] = {}
        self._sessions[user_id]["contexts"][domain] = context
