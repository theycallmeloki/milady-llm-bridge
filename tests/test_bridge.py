# tests/test_bridge.py
import pytest
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch
from mcp import StdioServerParameters
from mcp_llm_bridge.config import BridgeConfig, LLMConfig
from mcp_llm_bridge.bridge import MCPLLMBridge, BridgeManager

@pytest.fixture
def mock_config():
    return BridgeConfig(
        mcp_server_params=StdioServerParameters(
            command="uvx",
            args=["mcp-server"],
            env=None
        ),
        llm_config=LLMConfig(
            api_key="test-key",
            model="gpt-4",
            base_url=None
        ),
        system_prompt="Test system prompt"
    )

# Fixtures for the MiladyOS SSE tools
@pytest.fixture
def mock_hello_world_tool():
    mock = MagicMock()
    mock.name = "hello_world"
    mock.description = "Say hello from MiladyOS!"
    mock.inputSchema = {
        "type": "object",
        "properties": {}
    }
    return mock

@pytest.fixture
def mock_view_template_tool():
    mock = MagicMock()
    mock.name = "view_template"
    mock.description = "View content of a template with line numbers"
    mock.inputSchema = {
        "type": "object",
        "properties": {
            "template_name": {"type": "string"}
        },
        "required": ["template_name"]
    }
    return mock

@pytest.fixture
def mock_edit_template_tool():
    mock = MagicMock()
    mock.name = "edit_template"
    mock.description = "Edit an existing template in the templates directory"
    mock.inputSchema = {
        "type": "object",
        "properties": {
            "template_name": {"type": "string"},
            "content": {"type": "string"}
        },
        "required": ["template_name", "content"]
    }
    return mock

@pytest.fixture
def mock_execute_command_tool():
    mock = MagicMock()
    mock.name = "execute_command"
    mock.description = "Execute a CLI command"
    mock.inputSchema = {
        "type": "object",
        "properties": {
            "command": {"type": "string"}
        },
        "required": ["command"]
    }
    return mock

@pytest.fixture
def mock_create_template_tool():
    mock = MagicMock()
    mock.name = "create_template"
    mock.description = "Create or modify a template in the templates directory"
    mock.inputSchema = {
        "type": "object",
        "properties": {
            "template_name": {"type": "string"},
            "content": {"type": "string"}
        },
        "required": ["template_name", "content"]
    }
    return mock

@pytest.fixture
def mock_list_templates_tool():
    mock = MagicMock()
    mock.name = "list_templates"
    mock.description = "List all available pipeline templates"
    mock.inputSchema = {
        "type": "object",
        "properties": {}
    }
    return mock

@pytest.fixture
def mock_deploy_pipeline_tool():
    mock = MagicMock()
    mock.name = "deploy_pipeline"
    mock.description = "Register a template with Jenkins (with version control)"
    mock.inputSchema = {
        "type": "object",
        "properties": {
            "template_name": {"type": "string"},
            "version": {"type": "string"}
        },
        "required": ["template_name", "version"]
    }
    return mock

@pytest.fixture
def mock_run_pipeline_tool():
    mock = MagicMock()
    mock.name = "run_pipeline"
    mock.description = "Execute a pipeline and record in metadata layer"
    mock.inputSchema = {
        "type": "object",
        "properties": {
            "pipeline_id": {"type": "string"},
            "parameters": {
                "type": "object",
                "additionalProperties": True
            }
        },
        "required": ["pipeline_id"]
    }
    return mock

@pytest.fixture
def mock_get_pipeline_status_tool():
    mock = MagicMock()
    mock.name = "get_pipeline_status"
    mock.description = "Get status from metadata layer (not directly from Jenkins)"
    mock.inputSchema = {
        "type": "object",
        "properties": {
            "run_id": {"type": "string"}
        },
        "required": ["run_id"]
    }
    return mock

@pytest.fixture
def mock_list_pipeline_runs_tool():
    mock = MagicMock()
    mock.name = "list_pipeline_runs"
    mock.description = "Show execution history from metadata"
    mock.inputSchema = {
        "type": "object",
        "properties": {
            "pipeline_id": {"type": "string"},
            "limit": {"type": "integer"}
        },
        "required": ["pipeline_id"]
    }
    return mock

@pytest.fixture
def mock_read_query_tool():
    mock = MagicMock()
    mock.name = "read_query"
    mock.description = "Execute a SELECT query on MiladyOS's internal SQLite database (read-only)"
    mock.inputSchema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"}
        },
        "required": ["query"]
    }
    return mock

@pytest.fixture
def mock_list_db_tables_tool():
    mock = MagicMock()
    mock.name = "list_db_tables"
    mock.description = "List all tables in MiladyOS's internal SQLite database"
    mock.inputSchema = {
        "type": "object",
        "properties": {}
    }
    return mock

@pytest.fixture
def mock_describe_db_table_tool():
    mock = MagicMock()
    mock.name = "describe_db_table"
    mock.description = "Get the schema information for a specific table in MiladyOS's internal database"
    mock.inputSchema = {
        "type": "object",
        "properties": {
            "table_name": {"type": "string"}
        },
        "required": ["table_name"]
    }
    return mock

@pytest.fixture
def all_mock_tools(
    mock_hello_world_tool, mock_view_template_tool, mock_edit_template_tool,
    mock_execute_command_tool, mock_create_template_tool, mock_list_templates_tool,
    mock_deploy_pipeline_tool, mock_run_pipeline_tool, mock_get_pipeline_status_tool,
    mock_list_pipeline_runs_tool, mock_read_query_tool, mock_list_db_tables_tool,
    mock_describe_db_table_tool
):
    return [
        mock_hello_world_tool, mock_view_template_tool, mock_edit_template_tool,
        mock_execute_command_tool, mock_create_template_tool, mock_list_templates_tool,
        mock_deploy_pipeline_tool, mock_run_pipeline_tool, mock_get_pipeline_status_tool,
        mock_list_pipeline_runs_tool, mock_read_query_tool, mock_list_db_tables_tool,
        mock_describe_db_table_tool
    ]

@pytest.fixture
def mock_llm_response():
    tool_call = MagicMock()
    tool_call.id = "call_1"
    tool_call.function = MagicMock()
    tool_call.function.name = "test_tool"
    tool_call.function.arguments = '{"arg1": "test"}'
    
    response = MagicMock()
    response.tool_calls = [tool_call]
    return response

@pytest.mark.asyncio
async def test_bridge_initialization(mock_config, all_mock_tools):
    with patch('mcp_llm_bridge.bridge.MCPClient') as MockMCPClient:
        # Setup mocks
        mock_mcp_instance = AsyncMock()
        mock_mcp_instance.get_available_tools.return_value = all_mock_tools
        MockMCPClient.return_value = mock_mcp_instance

        # Create bridge
        bridge = MCPLLMBridge(mock_config)
        
        # Test initialization
        success = await bridge.initialize()
        assert success == True
        
        # Verify MCP client was initialized
        MockMCPClient.assert_called_once()
        mock_mcp_instance.connect.assert_called_once()
        mock_mcp_instance.get_available_tools.assert_called_once()

@pytest.mark.asyncio
async def test_tool_conversion(mock_config, all_mock_tools):
    bridge = MCPLLMBridge(mock_config)
    converted_tools = bridge._convert_mcp_tools_to_openai_format(all_mock_tools)
    
    assert len(converted_tools) == 13
    
    # Verify each tool was correctly converted
    for i, tool in enumerate(all_mock_tools):
        assert converted_tools[i]["type"] == "function"
        assert converted_tools[i]["function"]["name"] == tool.name.replace("-", "_").replace(" ", "_").lower()
        assert converted_tools[i]["function"]["description"] == tool.description
        assert "parameters" in converted_tools[i]["function"]

@pytest.mark.asyncio
async def test_message_processing(mock_config, mock_llm_response):
    with patch('mcp_llm_bridge.bridge.MCPClient') as MockMCPClient, \
         patch('mcp_llm_bridge.bridge.LLMClient') as MockLLMClient, \
         patch('mcp_llm_bridge.logging_config.notify_stream_token') as mock_stream_handler:
        
        # Setup mocks
        mock_mcp_instance = AsyncMock()
        mock_llm_instance = AsyncMock()
        
        # Create a mock response without tool calls
        mock_response = MagicMock()
        mock_response.content = "Final response"
        mock_response.tool_calls = None
        mock_response.is_tool_call = False
        
        mock_llm_instance.invoke_with_prompt.return_value = mock_response
        
        MockMCPClient.return_value = mock_mcp_instance
        MockLLMClient.return_value = mock_llm_instance

        # Create and initialize bridge
        bridge = MCPLLMBridge(mock_config)
        await bridge.initialize()

        # Test message processing
        response = await bridge.process_message("Test message")
        
        # Verify interactions
        mock_llm_instance.invoke_with_prompt.assert_called_once()
        args, kwargs = mock_llm_instance.invoke_with_prompt.call_args
        assert args[0] == "Test message"  # First argument should be the message
        assert args[1] is True  # Second argument should be stream=True
        # Don't check the stream_handler directly as it may vary
        
        assert response == "Final response"

@pytest.mark.asyncio
async def test_tool_call_handling(mock_config, mock_llm_response):
    with patch('mcp_llm_bridge.bridge.MCPClient') as MockMCPClient, \
         patch('mcp_llm_bridge.bridge.LLMClient') as MockLLMClient:
        
        # Setup mocks
        mock_mcp_instance = AsyncMock()
        mock_mcp_instance.call_tool.return_value = {"result": "tool_result"}
        
        mock_llm_instance = AsyncMock()
        mock_llm_instance.invoke_with_prompt.return_value = mock_llm_response
        mock_llm_instance.invoke.return_value = MagicMock(content="Final response")
        
        MockMCPClient.return_value = mock_mcp_instance
        MockLLMClient.return_value = mock_llm_instance

        # Create and initialize bridge
        bridge = MCPLLMBridge(mock_config)
        bridge.tool_name_mapping = {"test_tool": "test_tool"}
        await bridge.initialize()

        # Test tool call handling
        tool_responses = await bridge._handle_tool_calls(mock_llm_response.tool_calls)
        
        # Verify tool execution
        assert len(tool_responses) == 1
        assert tool_responses[0]["tool_call_id"] == "call_1"
        mock_mcp_instance.call_tool.assert_called_once_with(
            "test_tool", 
            {"arg1": "test"}
        )

@pytest.mark.asyncio
async def test_bridge_manager(mock_config):
    with patch('mcp_llm_bridge.bridge.MCPLLMBridge') as MockBridge:
        # Setup mock
        mock_bridge_instance = AsyncMock()
        mock_bridge_instance.initialize.return_value = True
        MockBridge.return_value = mock_bridge_instance

        # Test context manager
        async with BridgeManager(mock_config) as bridge:
            assert bridge is mock_bridge_instance
            mock_bridge_instance.initialize.assert_called_once()

@pytest.mark.asyncio
async def test_error_handling(mock_config):
    with patch('mcp_llm_bridge.bridge.MCPClient') as MockMCPClient:
        # Setup mock to raise an error
        mock_mcp_instance = AsyncMock()
        mock_mcp_instance.connect.side_effect = Exception("Connection error")
        MockMCPClient.return_value = mock_mcp_instance

        # Create bridge
        bridge = MCPLLMBridge(mock_config)
        
        # Test initialization failure
        success = await bridge.initialize()
        assert success == False

@pytest.mark.asyncio
async def test_tool_name_sanitization(mock_config):
    bridge = MCPLLMBridge(mock_config)
    
    test_cases = [
        ("test-tool", "test_tool"),
        ("test tool", "test_tool"),
        ("Test-Tool", "test_tool"),
        ("test_tool", "test_tool"),
        ("test-tool-123", "test_tool_123"),
    ]
    
    for input_name, expected_output in test_cases:
        assert bridge._sanitize_tool_name(input_name) == expected_output

@pytest.mark.asyncio
async def test_bridge_cleanup(mock_config):
    with patch('mcp_llm_bridge.bridge.MCPClient') as MockMCPClient:
        # Setup mock
        mock_mcp_instance = AsyncMock()
        MockMCPClient.return_value = mock_mcp_instance

        # Create bridge
        bridge = MCPLLMBridge(mock_config)
        
        # Test cleanup
        await bridge.close()
        mock_mcp_instance.__aexit__.assert_called_once()

# New tests for specific tool edge cases
@pytest.mark.asyncio
async def test_hello_world_tool(mock_config, mock_hello_world_tool):
    with patch('mcp_llm_bridge.bridge.MCPClient') as MockMCPClient, \
         patch('mcp_llm_bridge.bridge.LLMClient') as MockLLMClient:
        
        # Setup mocks
        mock_mcp_instance = AsyncMock()
        mock_mcp_instance.get_available_tools.return_value = [mock_hello_world_tool]
        mock_mcp_instance.call_tool.return_value = "Hello from MiladyOS!"
        
        MockMCPClient.return_value = mock_mcp_instance
        
        # Create tool call
        tool_call = MagicMock()
        tool_call.id = "call_hello"
        tool_call.function = MagicMock()
        tool_call.function.name = "hello_world"
        tool_call.function.arguments = '{}'
        
        # Create bridge
        bridge = MCPLLMBridge(mock_config)
        bridge.tool_name_mapping = {"hello_world": "hello_world"}
        await bridge.initialize()
        
        # Test tool call
        tool_responses = await bridge._handle_tool_calls([tool_call])
        
        # Verify
        assert len(tool_responses) == 1
        assert tool_responses[0]["tool_call_id"] == "call_hello"
        assert tool_responses[0]["output"] == "Hello from MiladyOS!"
        mock_mcp_instance.call_tool.assert_called_once_with("hello_world", {})

@pytest.mark.asyncio
async def test_view_template_tool(mock_config, mock_view_template_tool):
    with patch('mcp_llm_bridge.bridge.MCPClient') as MockMCPClient, \
         patch('mcp_llm_bridge.bridge.LLMClient') as MockLLMClient:
        
        # Setup mocks
        mock_mcp_instance = AsyncMock()
        mock_mcp_instance.get_available_tools.return_value = [mock_view_template_tool]
        mock_mcp_instance.call_tool.return_value = "Template content with line numbers"
        
        MockMCPClient.return_value = mock_mcp_instance
        
        # Create tool call
        tool_call = MagicMock()
        tool_call.id = "call_view"
        tool_call.function = MagicMock()
        tool_call.function.name = "view_template"
        tool_call.function.arguments = '{"template_name": "example.yaml"}'
        
        # Create bridge
        bridge = MCPLLMBridge(mock_config)
        bridge.tool_name_mapping = {"view_template": "view_template"}
        await bridge.initialize()
        
        # Test tool call
        tool_responses = await bridge._handle_tool_calls([tool_call])
        
        # Verify
        assert len(tool_responses) == 1
        assert tool_responses[0]["tool_call_id"] == "call_view"
        assert tool_responses[0]["output"] == "Template content with line numbers"
        mock_mcp_instance.call_tool.assert_called_once_with(
            "view_template", 
            {"template_name": "example.yaml"}
        )

@pytest.mark.asyncio
async def test_view_template_tool_missing_required_parameter(mock_config, mock_view_template_tool):
    with patch('mcp_llm_bridge.bridge.MCPClient') as MockMCPClient, \
         patch('mcp_llm_bridge.bridge.LLMClient') as MockLLMClient:
        
        # Setup mocks
        mock_mcp_instance = AsyncMock()
        mock_mcp_instance.get_available_tools.return_value = [mock_view_template_tool]
        mock_mcp_instance.call_tool.side_effect = Exception("Missing required parameter: template_name")
        
        MockMCPClient.return_value = mock_mcp_instance
        
        # Create tool call with missing required parameter
        tool_call = MagicMock()
        tool_call.id = "call_view"
        tool_call.function = MagicMock()
        tool_call.function.name = "view_template"
        tool_call.function.arguments = '{}'
        
        # Create bridge
        bridge = MCPLLMBridge(mock_config)
        bridge.tool_name_mapping = {"view_template": "view_template"}
        await bridge.initialize()
        
        # Test tool call
        tool_responses = await bridge._handle_tool_calls([tool_call])
        
        # Verify error handling
        assert len(tool_responses) == 1
        assert tool_responses[0]["tool_call_id"] == "call_view"
        assert "Error: Missing required parameter" in tool_responses[0]["output"]

@pytest.mark.asyncio
async def test_edit_template_tool(mock_config, mock_edit_template_tool):
    with patch('mcp_llm_bridge.bridge.MCPClient') as MockMCPClient, \
         patch('mcp_llm_bridge.bridge.LLMClient') as MockLLMClient:
        
        # Setup mocks
        mock_mcp_instance = AsyncMock()
        mock_mcp_instance.get_available_tools.return_value = [mock_edit_template_tool]
        mock_mcp_instance.call_tool.return_value = "Template edited successfully"
        
        MockMCPClient.return_value = mock_mcp_instance
        
        # Create tool call
        tool_call = MagicMock()
        tool_call.id = "call_edit"
        tool_call.function = MagicMock()
        tool_call.function.name = "edit_template"
        tool_call.function.arguments = '{"template_name": "example.yaml", "content": "updated content"}'
        
        # Create bridge
        bridge = MCPLLMBridge(mock_config)
        bridge.tool_name_mapping = {"edit_template": "edit_template"}
        await bridge.initialize()
        
        # Test tool call
        tool_responses = await bridge._handle_tool_calls([tool_call])
        
        # Verify
        assert len(tool_responses) == 1
        assert tool_responses[0]["tool_call_id"] == "call_edit"
        assert tool_responses[0]["output"] == "Template edited successfully"
        mock_mcp_instance.call_tool.assert_called_once_with(
            "edit_template", 
            {"template_name": "example.yaml", "content": "updated content"}
        )

@pytest.mark.asyncio
async def test_execute_command_tool(mock_config, mock_execute_command_tool):
    with patch('mcp_llm_bridge.bridge.MCPClient') as MockMCPClient, \
         patch('mcp_llm_bridge.bridge.LLMClient') as MockLLMClient:
        
        # Setup mocks
        mock_mcp_instance = AsyncMock()
        mock_mcp_instance.get_available_tools.return_value = [mock_execute_command_tool]
        mock_mcp_instance.call_tool.return_value = "Command executed: ls -la"
        
        MockMCPClient.return_value = mock_mcp_instance
        
        # Create tool call
        tool_call = MagicMock()
        tool_call.id = "call_exec"
        tool_call.function = MagicMock()
        tool_call.function.name = "execute_command"
        tool_call.function.arguments = '{"command": "ls -la"}'
        
        # Create bridge
        bridge = MCPLLMBridge(mock_config)
        bridge.tool_name_mapping = {"execute_command": "execute_command"}
        await bridge.initialize()
        
        # Test tool call
        tool_responses = await bridge._handle_tool_calls([tool_call])
        
        # Verify
        assert len(tool_responses) == 1
        assert tool_responses[0]["tool_call_id"] == "call_exec"
        assert tool_responses[0]["output"] == "Command executed: ls -la"
        mock_mcp_instance.call_tool.assert_called_once_with(
            "execute_command", 
            {"command": "ls -la"}
        )

@pytest.mark.asyncio
async def test_multiple_tool_calls_in_sequence(mock_config, all_mock_tools):
    with patch('mcp_llm_bridge.bridge.MCPClient') as MockMCPClient, \
         patch('mcp_llm_bridge.bridge.LLMClient') as MockLLMClient:
        
        # Setup mocks
        mock_mcp_instance = AsyncMock()
        mock_mcp_instance.get_available_tools.return_value = all_mock_tools
        mock_mcp_instance.call_tool.side_effect = [
            "Hello from MiladyOS!",
            "Template content",
            "Query results"
        ]
        
        mock_llm_instance = AsyncMock()
        
        # Create a sequence of responses with tool calls
        hello_tool_call = MagicMock()
        hello_tool_call.id = "call_hello"
        hello_tool_call.function = MagicMock()
        hello_tool_call.function.name = "hello_world"
        hello_tool_call.function.arguments = '{}'
        
        first_response = MagicMock()
        first_response.is_tool_call = True
        first_response.tool_calls = [hello_tool_call]
        
        view_tool_call = MagicMock()
        view_tool_call.id = "call_view"
        view_tool_call.function = MagicMock()
        view_tool_call.function.name = "view_template"
        view_tool_call.function.arguments = '{"template_name": "example.yaml"}'
        
        second_response = MagicMock()
        second_response.is_tool_call = True
        second_response.tool_calls = [view_tool_call]
        
        query_tool_call = MagicMock()
        query_tool_call.id = "call_query"
        query_tool_call.function = MagicMock()
        query_tool_call.function.name = "read_query"
        query_tool_call.function.arguments = '{"query": "SELECT * FROM pipelines"}'
        
        third_response = MagicMock()
        third_response.is_tool_call = True
        third_response.tool_calls = [query_tool_call]
        
        final_response = MagicMock()
        final_response.is_tool_call = False
        final_response.content = "Final response after all tool calls"
        
        # Setup response sequence
        mock_llm_instance.invoke_with_prompt.return_value = first_response
        mock_llm_instance.invoke.side_effect = [second_response, third_response, final_response]
        
        MockMCPClient.return_value = mock_mcp_instance
        MockLLMClient.return_value = mock_llm_instance
        
        # Create bridge
        bridge = MCPLLMBridge(mock_config)
        bridge.tool_name_mapping = {
            "hello_world": "hello_world",
            "view_template": "view_template",
            "read_query": "read_query"
        }
        await bridge.initialize()
        
        # Test multiple tool calls
        response = await bridge.process_message("Use multiple tools")
        
        # Verify
        assert response == "Final response after all tool calls"
        assert mock_mcp_instance.call_tool.call_count == 3
        assert mock_llm_instance.invoke.call_count == 3

@pytest.mark.asyncio
async def test_complex_input_schema_handling(mock_config, mock_run_pipeline_tool):
    with patch('mcp_llm_bridge.bridge.MCPClient') as MockMCPClient, \
         patch('mcp_llm_bridge.bridge.LLMClient') as MockLLMClient:
        
        # Setup mocks
        mock_mcp_instance = AsyncMock()
        mock_mcp_instance.get_available_tools.return_value = [mock_run_pipeline_tool]
        mock_mcp_instance.call_tool.return_value = "Pipeline started, run ID: abc123"
        
        MockMCPClient.return_value = mock_mcp_instance
        
        # Create tool call with complex nested parameters
        tool_call = MagicMock()
        tool_call.id = "call_run"
        tool_call.function = MagicMock()
        tool_call.function.name = "run_pipeline"
        tool_call.function.arguments = json.dumps({
            "pipeline_id": "data-etl",
            "parameters": {
                "source": "mysql",
                "target": "snowflake",
                "options": {
                    "batch_size": 1000,
                    "timeout": 3600
                },
                "tables": ["users", "orders", "products"]
            }
        })
        
        # Create bridge
        bridge = MCPLLMBridge(mock_config)
        bridge.tool_name_mapping = {"run_pipeline": "run_pipeline"}
        await bridge.initialize()
        
        # Test tool call
        tool_responses = await bridge._handle_tool_calls([tool_call])
        
        # Verify complex parameter handling
        assert len(tool_responses) == 1
        assert tool_responses[0]["tool_call_id"] == "call_run"
        assert tool_responses[0]["output"] == "Pipeline started, run ID: abc123"
        
        # Check that complex parameters were passed correctly
        call_args = mock_mcp_instance.call_tool.call_args[0]
        assert call_args[0] == "run_pipeline"
        assert call_args[1]["pipeline_id"] == "data-etl"
        assert call_args[1]["parameters"]["source"] == "mysql"
        assert call_args[1]["parameters"]["target"] == "snowflake"
        assert call_args[1]["parameters"]["options"]["batch_size"] == 1000
        assert "tables" in call_args[1]["parameters"]

@pytest.mark.asyncio
async def test_tool_result_handling_for_different_response_types(mock_config, mock_hello_world_tool):
    with patch('mcp_llm_bridge.bridge.MCPClient') as MockMCPClient, \
         patch('mcp_llm_bridge.bridge.LLMClient') as MockLLMClient:
        
        # Setup mocks
        mock_mcp_instance = AsyncMock()
        mock_mcp_instance.get_available_tools.return_value = [mock_hello_world_tool]
        
        # Setup different response types to test
        string_response = "Simple string response"
        dict_response = {"status": "success", "message": "Operation completed"}
        object_with_content_list = type('ObjWithContentList', (), {
            'content': [
                type('Content1', (), {'text': 'First part.'}),
                type('Content2', (), {'text': 'Second part.'})
            ]
        })()
        
        # Configure call_tool to return different response types in sequence
        mock_mcp_instance.call_tool.side_effect = [
            string_response,
            dict_response,
            object_with_content_list
        ]
        
        MockMCPClient.return_value = mock_mcp_instance
        
        # Create tool call
        tool_call = MagicMock()
        tool_call.id = "call_test"
        tool_call.function = MagicMock()
        tool_call.function.name = "hello_world"
        tool_call.function.arguments = '{}'
        
        # Create bridge
        bridge = MCPLLMBridge(mock_config)
        bridge.tool_name_mapping = {"hello_world": "hello_world"}
        await bridge.initialize()
        
        # Test different response types
        for i, expected_output in enumerate([
            string_response,
            str(dict_response),
            "First part. Second part."
        ]):
            tool_responses = await bridge._handle_tool_calls([tool_call])
            assert tool_responses[0]["output"] == expected_output
            assert mock_mcp_instance.call_tool.call_count == i + 1

@pytest.mark.asyncio
async def test_error_reporting_for_failed_tool_calls(mock_config, mock_hello_world_tool):
    with patch('mcp_llm_bridge.bridge.MCPClient') as MockMCPClient, \
         patch('mcp_llm_bridge.bridge.LLMClient') as MockLLMClient:
        
        # Setup mocks
        mock_mcp_instance = AsyncMock()
        mock_mcp_instance.get_available_tools.return_value = [mock_hello_world_tool]
        
        # Setup various errors
        mock_mcp_instance.call_tool.side_effect = [
            Exception("Network error"),
            ValueError("Invalid parameter"),
            RuntimeError("Internal server error")
        ]
        
        MockMCPClient.return_value = mock_mcp_instance
        
        # Create tool call
        tool_call = MagicMock()
        tool_call.id = "call_test"
        tool_call.function = MagicMock()
        tool_call.function.name = "hello_world"
        tool_call.function.arguments = '{}'
        
        # Create bridge
        bridge = MCPLLMBridge(mock_config)
        bridge.tool_name_mapping = {"hello_world": "hello_world"}
        await bridge.initialize()
        
        # Test error handling for different exception types
        for i, expected_error in enumerate(["Network error", "Invalid parameter", "Internal server error"]):
            tool_responses = await bridge._handle_tool_calls([tool_call])
            assert f"Error: {expected_error}" in tool_responses[0]["output"]
            assert mock_mcp_instance.call_tool.call_count == i + 1

@pytest.mark.asyncio
async def test_malformed_tool_call_handling(mock_config, mock_hello_world_tool):
    with patch('mcp_llm_bridge.bridge.MCPClient') as MockMCPClient, \
         patch('mcp_llm_bridge.bridge.LLMClient') as MockLLMClient:
        
        # Setup mocks
        mock_mcp_instance = AsyncMock()
        mock_mcp_instance.get_available_tools.return_value = [mock_hello_world_tool]
        mock_mcp_instance.call_tool.return_value = "Success"
        
        MockMCPClient.return_value = mock_mcp_instance
        
        # Create malformed tool calls
        missing_function = type('MissingFunction', (), {'id': 'call_1'})
        missing_id = type('MissingId', (), {'function': None})
        malformed_arguments = MagicMock()
        malformed_arguments.id = "call_2"
        malformed_arguments.function = MagicMock()
        malformed_arguments.function.name = "hello_world"
        malformed_arguments.function.arguments = '{invalid json'
        
        # Dictionary style tool call with missing fields
        dict_style_call = {
            'id': 'call_3',
            # Missing 'function' field
        }
        
        # Create bridge
        bridge = MCPLLMBridge(mock_config)
        bridge.tool_name_mapping = {"hello_world": "hello_world"}
        await bridge.initialize()
        
        # Test handling of malformed tool calls
        tool_responses = await bridge._handle_tool_calls([
            missing_function, 
            missing_id, 
            malformed_arguments,
            dict_style_call
        ])
        
        # Verify that no valid tool calls were processed
        assert len(tool_responses) == 2  # Only the ones with valid IDs should have responses
        assert any("Error: " in response["output"] for response in tool_responses)
        assert mock_mcp_instance.call_tool.call_count == 0

@pytest.mark.asyncio
async def test_nonexistent_tool_handling(mock_config, mock_hello_world_tool):
    with patch('mcp_llm_bridge.bridge.MCPClient') as MockMCPClient, \
         patch('mcp_llm_bridge.bridge.LLMClient') as MockLLMClient:
        
        # Setup mocks
        mock_mcp_instance = AsyncMock()
        mock_mcp_instance.get_available_tools.return_value = [mock_hello_world_tool]
        
        MockMCPClient.return_value = mock_mcp_instance
        
        # Create tool call for nonexistent tool
        tool_call = MagicMock()
        tool_call.id = "call_nonexistent"
        tool_call.function = MagicMock()
        tool_call.function.name = "nonexistent_tool"
        tool_call.function.arguments = '{}'
        
        # Create bridge
        bridge = MCPLLMBridge(mock_config)
        bridge.tool_name_mapping = {"hello_world": "hello_world"}  # Only hello_world is mapped
        await bridge.initialize()
        
        # Test handling of nonexistent tool
        tool_responses = await bridge._handle_tool_calls([tool_call])
        
        # Verify that the tool call was skipped
        assert len(tool_responses) == 0
        mock_mcp_instance.call_tool.assert_not_called()

@pytest.mark.asyncio
async def test_streaming_mode(mock_config, all_mock_tools):
    with patch('mcp_llm_bridge.bridge.MCPClient') as MockMCPClient, \
         patch('mcp_llm_bridge.bridge.LLMClient') as MockLLMClient, \
         patch('mcp_llm_bridge.logging_config.notify_stream_token') as mock_stream_handler:
        
        # Setup mocks
        mock_mcp_instance = AsyncMock()
        mock_mcp_instance.get_available_tools.return_value = all_mock_tools
        
        mock_llm_instance = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "Streaming response"
        mock_response.tool_calls = None
        
        mock_llm_instance.invoke_with_prompt.return_value = mock_response
        
        MockMCPClient.return_value = mock_mcp_instance
        MockLLMClient.return_value = mock_llm_instance
        
        # Create bridge
        bridge = MCPLLMBridge(mock_config)
        await bridge.initialize()
        
        # Test streaming mode
        response = await bridge.process_message("Test message", stream=True)
        
        # Verify stream handler was passed
        mock_llm_instance.invoke_with_prompt.assert_called_once()
        assert mock_llm_instance.invoke_with_prompt.call_args[0][1] is True  # stream=True
        assert mock_llm_instance.invoke_with_prompt.call_args[0][2] is not None  # stream_handler is not None