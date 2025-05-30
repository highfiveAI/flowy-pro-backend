from app.api.mcp_utils import MCPContextManager

mcp_manager = MCPContextManager()

def create_user_context(user_id, initial_data=None):
    return mcp_manager.create_context(user_id, initial_data)

def update_user_context(user_id, data):
    return mcp_manager.update_context(user_id, data)

def get_user_context(user_id):
    return mcp_manager.get_context(user_id)