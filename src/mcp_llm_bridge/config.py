# src/mcp_llm_bridge/config.py
from dataclasses import dataclass
from typing import Dict, Optional
from mcp import StdioServerParameters

@dataclass
class SSEServerParameters:
    url: str
    env: Optional[Dict[str, str]] = None

@dataclass
class LLMConfig:
    api_key: str
    model: str
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2000

@dataclass
class BridgeConfig:
    mcp_server_params: object  # Either StdioServerParameters or SSEServerParameters
    llm_config: LLMConfig
    system_prompt: Optional[str] = None