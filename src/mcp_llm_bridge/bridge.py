# src/mcp_llm_bridge/bridge.py
import json
from mcp_llm_bridge.mcp_client import MCPClient
from mcp_llm_bridge.llm_client import LLMClient
from mcp_llm_bridge.logging_config import notify_tool_call
from mcp_llm_bridge.config import SSEServerParameters

class MCPLLMBridge:
    def __init__(self, config):
        self.config = config
        self.mcp_client = MCPClient(config.mcp_server_params)
        self.llm_client = LLMClient(config.llm_config)
        if config.system_prompt: self.llm_client.system_prompt = config.system_prompt
        self.available_tools = []
        self.tool_name_mapping = {}
        
    async def update_template(self, template_name, content):
        """Update a template directly from piped input without using MCP or LLMs.
        Specifically designed to handle Jenkinsfile templates."""
        try:
            # Call edit_template or create_template tool directly
            result = await self.mcp_client.call_tool(
                "edit_template", 
                {"template_name": template_name, "content": content}
            )
            return result
        except Exception as e:
            # If edit_template failed (template doesn't exist yet), try create_template
            try:
                return await self.mcp_client.call_tool(
                    "create_template", 
                    {"template_name": template_name, "content": content}
                )
            except Exception as inner_e:
                raise RuntimeError(f"Failed to update template: {str(inner_e) or str(e)}")

    async def initialize(self):
        try:
            # Super kawaii Milady boot sequence
            import time, random, requests
            
            small_milady_logo = """
             ,.. ,.,
        ......,,.,,,,,,,
     ..,,..,,,,***,,.,,,,,.,
    ,,,,*,,*,,,*%&&&&&(**,,,,
    ,*,*,.,*,*&&&&&&&&&.*&,#/
   ,**,,,*,,/#&&&&&&&&%
   */,/(  %/        ,
  ,*%%&&&&&&    .  &&%.
  ,,,,.%%%%%&&#%&&&&&&&%%%,,
   ,,,,......%&&&&&%&%%%,,,,,
       ,,,...             ,,
    """
            print(small_milady_logo)
            print("\n⋆ ˚｡⋆୨♡୧⋆ ˚｡⋆  cute/acc  ⋆ ˚｡⋆୨♡୧⋆ ˚｡⋆\n")
            
            boot_messages = [
                "˚₊‧꒰ა ☆ ໒꒱ Agent Milady...",
                "˚✧₊⁎( ˘ω˘ )⁎⁺˳✧༚ Upgrading to Milady Context Protocol...",
            ]
            
            # Print boot messages with cute typing effect
            for msg in boot_messages:
                for char in msg:
                    print(char, end="", flush=True)
                    time.sleep(random.uniform(0.01, 0.03))
                time.sleep(0.3)
                print(" ✓")
                
            # Note: removed health check since we try to connect anyway
            
            # Connect to MCP silently
            print("\n", end="")  # Add a newline for spacing
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
                
                # Properly invoke the LLM with the tool responses
                try:
                    response = await self.llm_client.invoke(tool_responses, stream, stream_handler)
                except Exception as e:
                    # If the LLM has trouble with the tool response, just show it once
                    if len(tool_responses) == 1:
                        # Don't print it here as it will be returned and printed later
                        return tool_responses[0]['output']
                    else:
                        output = "\n".join(t['output'] for t in tool_responses)
                        return output
            
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
                # Handle empty string arguments
                # Handle arguments properly - empty string, properly formatted JSON, or dict
                if isinstance(function_args, str):
                    if not function_args.strip():
                        arguments = {}  # Empty arguments
                    else:
                        try:
                            arguments = json.loads(function_args)
                        except json.JSONDecodeError:
                            arguments = {"text": function_args}  # Fallback for invalid JSON
                else:
                    arguments = function_args if function_args else {}
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
        
    async def update_template(self, template_name, content):
        """Proxy to bridge's update_template method"""
        if not self.bridge:
            raise RuntimeError("Bridge not initialized")
        return await self.bridge.update_template(template_name, content)