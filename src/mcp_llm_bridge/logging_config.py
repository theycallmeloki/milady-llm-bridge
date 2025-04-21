# src/mcp_llm_bridge/logging_config.py
import sys
import logging

tool_call_callbacks = []
stream_token_callbacks = []
mcp_notification_callbacks = {}

def setup_logging(): logging.getLogger().setLevel(logging.ERROR)

def register_tool_call_callback(callback): tool_call_callbacks.append(callback)
def register_stream_token_callback(callback): stream_token_callbacks.append(callback)

def register_mcp_notification_callback(method, callback):
    if method not in mcp_notification_callbacks: mcp_notification_callbacks[method] = []
    mcp_notification_callbacks[method].append(callback)

def notify_tool_call(tool_name):
    for callback in tool_call_callbacks:
        try: callback(tool_name); sys.stdout.flush()
        except: pass

def notify_stream_token(token):
    for callback in stream_token_callbacks:
        try: callback(token); sys.stdout.flush()
        except: pass

async def notify_mcp_notification(method, params):
    if method not in mcp_notification_callbacks: return
    for callback in mcp_notification_callbacks[method]:
        try:
            result = callback(params)
            if hasattr(result, "__await__"): await result
            sys.stdout.flush()
        except: pass

class MinimalProgressLogger:
    def __init__(self): self.in_cot_mode = False
    
    def on_init_complete(self, tools=None): pass  # Silent initialization
    
    def on_tool_call(self, tool_name):
        if self.in_cot_mode: print("\n", end="", flush=True); self.in_cot_mode = False
        print(f"▶ {tool_name}", flush=True)
    
    def on_stream_token(self, token):
        print(token, end="", flush=True)
        self.in_cot_mode = True
    
    async def on_mcp_notification(self, params):
        if params.get("contentType") == "thinking":
            print(params.get("content", ""), end="", flush=True)
            self.in_cot_mode = True