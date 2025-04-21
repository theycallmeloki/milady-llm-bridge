# src/mcp_llm_bridge/llm_client.py
import openai
import json

class LLMResponse:
    def __init__(self, completion):
        self.choice = completion.choices[0]
        self.message = self.choice.message
        self.stop_reason = self.choice.finish_reason
        self.is_tool_call = self.stop_reason == "tool_calls"
        self.content = self.message.content if self.message.content is not None else ""
        self.tool_calls = self.message.tool_calls if hasattr(self.message, "tool_calls") else None
        
    def get_message(self):
        # Ensure we properly format the tool_calls
        msg = {"role": "assistant", "content": self.content}
        if self.tool_calls:
            msg["tool_calls"] = []
            for tc in self.tool_calls:
                if hasattr(tc, 'id') and hasattr(tc, 'function'):
                    # Object style
                    msg["tool_calls"].append({
                        "id": tc.id,
                        "type": "function", 
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    })
                elif isinstance(tc, dict) and 'id' in tc and 'function' in tc:
                    # Dictionary style
                    msg["tool_calls"].append(tc)
        return msg

class LLMClient:
    def __init__(self, config):
        self.config = config
        self.client = openai.OpenAI(api_key=config.api_key, base_url=config.base_url)
        self.tools = []
        self.messages = []
        self.system_prompt = None
    
    async def invoke_with_prompt(self, prompt, stream=False, stream_handler=None):
        self.messages.append({"role": "user", "content": prompt})
        return await self.invoke([], stream, stream_handler)
    
    async def invoke(self, tool_results=None, stream=False, stream_handler=None):
        # Add tool results to conversation
        if tool_results:
            for result in tool_results:
                tool_message = {
                    "role": "tool", 
                    "content": str(result.get("output", "")),
                    "tool_call_id": result["tool_call_id"]
                }
                self.messages.append(tool_message)
        
        # Prepare messages
        msgs = []
        if self.system_prompt: msgs.append({"role": "system", "content": self.system_prompt})
        msgs.extend(self.messages)
        
        if stream and stream_handler:
            # Stream mode
            streaming_completion = self.client.chat.completions.create(
                model=self.config.model,
                messages=msgs,
                tools=self.tools if self.tools else None,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                stream=True
            )
            
            collected_content = ""
            tool_calls = []
            stop_reason = None
            
            for chunk in streaming_completion:
                delta = chunk.choices[0].delta
                
                # Handle content
                if delta.content:
                    collected_content += delta.content
                    stream_handler(delta.content)
                
                # Handle tool calls
                if hasattr(delta, "tool_calls") and delta.tool_calls:
                    for tool_call in delta.tool_calls:
                        if len(tool_calls) <= tool_call.index:
                            tool_calls.append({
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": tool_call.function.name,
                                    "arguments": tool_call.function.arguments
                                }
                            })
                        elif tool_call.function.arguments:
                            tool_calls[tool_call.index]["function"]["arguments"] += tool_call.function.arguments
                
                if chunk.choices[0].finish_reason:
                    stop_reason = chunk.choices[0].finish_reason
            
            # Create synthetic completion
            completion = type('SyntheticCompletion', (), {
                'choices': [type('Choice', (), {
                    'message': type('Message', (), {
                        'content': collected_content,
                        'tool_calls': tool_calls
                    }),
                    'finish_reason': stop_reason
                })]
            })()
        else:
            # Non-streaming mode
            try:
                completion = self.client.chat.completions.create(
                    model=self.config.model,
                    messages=msgs,
                    tools=self.tools if self.tools else None,
                    temperature=self.config.temperature,
                    max_tokens=self.config.max_tokens
                )
            
                response = LLMResponse(completion)
                self.messages.append(response.get_message())
                return response
            except Exception as e:
                print(f"LLM API error: {str(e)}")
                raise
            
        # For streaming mode
        response = LLMResponse(completion)
        self.messages.append(response.get_message())
        return response