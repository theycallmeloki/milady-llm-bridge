# src/mcp_llm_bridge/main.py
import os, sys, asyncio, argparse
from dotenv import load_dotenv
from mcp_llm_bridge.config import BridgeConfig, LLMConfig, SSEServerParameters
from mcp_llm_bridge.bridge import BridgeManager
from mcp_llm_bridge.logging_config import (
    setup_logging, register_tool_call_callback, register_stream_token_callback,
    register_mcp_notification_callback, MinimalProgressLogger
)

def parse_args():
    parser = argparse.ArgumentParser(description="MCP LLM Bridge")
    parser.add_argument("prompt", nargs='?', type=str, help="The prompt to send to the LLM")
    parser.add_argument("--prompt", dest="prompt_flag", type=str, help="The prompt to send to the LLM (alternative flag format)")
    parser.add_argument("--template", type=str, help="Template name to update when using piped input")
    return parser.parse_args()

async def main():
    os.environ['PYTHONUNBUFFERED'] = '1'
    setup_logging()
    load_dotenv()
    
    args = parse_args()
    
    config = BridgeConfig(
        mcp_server_params=SSEServerParameters(
            url="http://mcp.miladyos.net/sse",
            env={}
        ),
        llm_config=LLMConfig(
            api_key="ollama",
            model="deepseek-r1:1.5b",
            base_url="https://lmm.miladyos.net/v1"
        ),
        system_prompt="You are a helpful assistant that can use tools to help answer questions."
    )
    
    logger = MinimalProgressLogger()
    register_tool_call_callback(logger.on_tool_call)
    register_stream_token_callback(logger.on_stream_token)
    register_mcp_notification_callback("notifications/progress", logger.on_mcp_notification)
    
    # Check if stdin has data (piped input)
    stdin_data = ""
    if not sys.stdin.isatty():
        stdin_data = sys.stdin.read().strip()
    
    # Create the bridge manager
    bridge_manager = BridgeManager(config)
    
    async with bridge_manager as bridge:
        try:
            logger.on_init_complete()
            
            # Handle template update from stdin if template flag is provided
            if args.template and stdin_data:
                await bridge_manager.update_template(args.template, stdin_data)
                print(f"\nTemplate '{args.template}' updated successfully.", flush=True)
                return
            
            # Use prompt_flag if provided, otherwise use positional prompt, or stdin data, or fallback to input
            user_input = args.prompt_flag if args.prompt_flag else args.prompt if args.prompt else stdin_data if stdin_data else input("\nEnter your prompt: ")
            
            if user_input.strip():
                response = await bridge.process_message(user_input)
                print(f"\n{response}", flush=True)
            else:
                print("\nNo input provided. Exiting...", flush=True)
        except KeyboardInterrupt:
            print("\nExiting...", flush=True)
        except Exception as e:
            print(f"\nError: {str(e)}", flush=True)

def cli_entry_point():
    asyncio.run(main())

if __name__ == "__main__":
    cli_entry_point()