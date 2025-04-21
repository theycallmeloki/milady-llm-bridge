# src/mcp_llm_bridge/bridge.py
import json
from mcp_llm_bridge.mcp_client import MCPClient
from mcp_llm_bridge.llm_client import LLMClient
from mcp_llm_bridge.logging_config import notify_tool_call

class MCPLLMBridge:
    def __init__(self, config):
        self.config = config
        self.mcp_client = MCPClient(config.mcp_server_params)
        self.llm_client = LLMClient(config.llm_config)
        if config.system_prompt: self.llm_client.system_prompt = config.system_prompt
        self.available_tools = []
        self.tool_name_mapping = {}

    async def initialize(self):
        try:
            await self.mcp_client.connect()
            
            # Register notification handler
            from mcp_llm_bridge.logging_config import notify_mcp_notification
            self.mcp_client.register_notification_handler(
                "notifications/progress", 
                lambda params: notify_mcp_notification("notifications/progress", params)
            )
            
            # Get and convert tools
            mcp_tools = await self.mcp_client.get_available_tools()
            self.available_tools = getattr(mcp_tools, 'tools', mcp_tools)
            self.llm_client.tools = self._convert_mcp_tools_to_openai_format(self.available_tools)
            return True
        except Exception: return False

    def _sanitize_tool_name(self, name):
        """
        Sanitize tool names to be compatible with OpenAI function naming conventions:
        - Replace hyphens and spaces with underscores
        - Convert to lowercase
        """
        return name.replace("-", "_").replace(" ", "_").lower()
        
    def _convert_mcp_tools_to_openai_format(self, mcp_tools):
        openai_tools = []
        tools_list = mcp_tools
        if hasattr(mcp_tools, 'tools'): tools_list = mcp_tools.tools
        elif isinstance(mcp_tools, dict): tools_list = mcp_tools.get('tools', [])
        
        for tool in tools_list if isinstance(tools_list, list) else []:
            if hasattr(tool, 'name') and hasattr(tool, 'description'):
                openai_name = self._sanitize_tool_name(tool.name)
                self.tool_name_mapping[openai_name] = tool.name
                tool_schema = getattr(tool, 'inputSchema', {"type": "object", "properties": {}, "required": []})
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": openai_name,
                        "description": tool.description,
                        "parameters": tool_schema
                    }
                })
        return openai_tools

    async def process_message(self, message, stream=True):
        try:
            # Set up streaming handler if enabled
            stream_handler = None
            if stream:
                from mcp_llm_bridge.logging_config import notify_stream_token
                stream_handler = notify_stream_token
            
            # Send message to LLM
            response = await self.llm_client.invoke_with_prompt(message, stream, stream_handler)
            
            # Process tool calls until we get a final response
            while response.is_tool_call and response.tool_calls:
                tool_responses = await self._handle_tool_calls(response.tool_calls)
                response = await self.llm_client.invoke(tool_responses, stream, stream_handler)
            
            return response.content
        except Exception as e: return f"Error: {str(e)}"

    async def _handle_tool_calls(self, tool_calls):
        tool_responses = []
        
        for tool_call in tool_calls:
            try:
                # Extract tool information
                if hasattr(tool_call, 'function'):
                    openai_name = tool_call.function.name
                    tool_id = tool_call.id
                    function_args = tool_call.function.arguments
                elif isinstance(tool_call, dict):
                    openai_name = tool_call['function']['name']
                    tool_id = tool_call['id']
                    function_args = tool_call['function']['arguments']
                else: continue
                
                mcp_name = self.tool_name_mapping.get(openai_name)
                if not mcp_name: continue
                
                # Notify and execute
                notify_tool_call(mcp_name)
                arguments = json.loads(function_args) if isinstance(function_args, str) else function_args
                result = await self.mcp_client.call_tool(mcp_name, arguments)
                
                # Format response
                if isinstance(result, str): output = result
                elif hasattr(result, 'content') and isinstance(result.content, list):
                    output = " ".join(content.text for content in result.content if hasattr(content, 'text'))
                else: output = str(result)
                
                tool_responses.append({"tool_call_id": tool_id, "output": output})
            except Exception as e:
                try:
                    if isinstance(tool_call, dict) and 'id' in tool_call: tool_id = tool_call['id']
                    elif hasattr(tool_call, 'id'): tool_id = tool_call.id
                    else: continue
                    tool_responses.append({"tool_call_id": tool_id, "output": f"Error: {str(e)}"})
                except: continue
        
        return tool_responses

    async def close(self): await self.mcp_client.__aexit__(None, None, None)

class BridgeManager:
    def __init__(self, config):
        self.config = config
        self.bridge = None

    async def __aenter__(self):
        self.bridge = MCPLLMBridge(self.config)
        await self.bridge.initialize()
        return self.bridge
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.bridge: await self.bridge.close()