# src/mcp_llm_bridge/mcp_client.py
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from mcp_llm_bridge.config import SSEServerParameters

class MCPClient:
    def __init__(self, server_params):
        self.server_params = server_params
        self.session = None
        self._client = None
        self._notification_handlers = {}
        
    async def __aenter__(self):
        await self.connect()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session: await self.session.__aexit__(exc_type, exc_val, exc_tb)
        if self._client: await self._client.__aexit__(exc_type, exc_val, exc_tb)
    
    def register_notification_handler(self, method, handler):
        self._notification_handlers[method] = handler
    
    async def _notification_callback(self, message):
        if not isinstance(message, dict) or "method" not in message or "jsonrpc" not in message: return
            
        method = message.get("method")
        params = message.get("params", {})
        
        # Call registered handler
        if method in self._notification_handlers:
            try: await self._notification_handlers[method](params)
            except: pass
            
        # Handle progress notifications
        if method == "notifications/progress":
            from mcp_llm_bridge.logging_config import notify_mcp_notification
            await notify_mcp_notification(method, params)

    async def connect(self):
        # Initialize client based on server parameters type
        if isinstance(self.server_params, StdioServerParameters):
            self._client = stdio_client(self.server_params)
            self.read, self.write = await self._client.__aenter__()
        elif isinstance(self.server_params, SSEServerParameters):
            self._client = sse_client(self.server_params.url, self.server_params.env)
            self.read, self.write = await self._client.__aenter__()
        else: raise ValueError("Unsupported server parameters")
        
        # Create notification-aware session
        class StreamingClientSession(ClientSession):
            def __init__(self, read, write, notification_callback):
                super().__init__(read, write)
                self._notification_callback = notification_callback
            
            async def _handle_message(self, message):
                if "method" in message and "params" in message:
                    await self._notification_callback(message)
                return await super()._handle_message(message)
        
        # Initialize session
        session = StreamingClientSession(self.read, self.write, self._notification_callback)
        self.session = await session.__aenter__()
        await self.session.initialize()

    async def get_available_tools(self):
        if not self.session: raise RuntimeError("Not connected to MCP server")
        return await self.session.list_tools()

    async def call_tool(self, tool_name, arguments):
        if not self.session: raise RuntimeError("Not connected to MCP server")
        return await self.session.call_tool(tool_name, arguments=arguments)