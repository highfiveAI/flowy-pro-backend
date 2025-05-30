# MCP(Model Context Protocol) 관련 유틸/연동 함수 예시

class MCPContextManager:
    def __init__(self):
        self.contexts = {}

    def create_context(self, user_id, initial_data=None):
        self.contexts[user_id] = initial_data or {}
        return self.contexts[user_id]

    def update_context(self, user_id, data):
        if user_id in self.contexts:
            self.contexts[user_id].update(data)
        else:
            self.create_context(user_id, data)
        return self.contexts[user_id]

    def get_context(self, user_id):
        return self.contexts.get(user_id, {})