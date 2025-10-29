import reflex as rx
import logging
import httpx
import os
import uuid
from typing import Any


class Message(rx.Base):
    role: str
    content: str


class ChatState(rx.State):
    messages: list[Message] = []
    is_processing: bool = False
    current_page: str = "Chat"
    mcp_url: str = "https://mcp.lemonado.io/mcp"
    mcp_token: str = ""
    model_options: list[str] = [
        "google/gemma-2-9b-it:free",
        "meta-llama/llama-3-8b-instruct:free",
        "microsoft/phi-3-medium-4k-instruct:free",
    ]
    model_name: str = "google/gemma-2-9b-it:free"
    mcp_session_id: str = ""
    available_tools: list[dict] = []

    async def _make_jsonrpc_request(
        self, method: str, params: dict | None = None
    ) -> dict:
        if not self.mcp_token:
            return {"error": {"message": "MCP token is not set."}}
        request_id = str(uuid.uuid4())
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }
        headers = {
            "Authorization": f"Bearer {self.mcp_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.mcp_session_id:
            headers["Mcp-Session-Id"] = self.mcp_session_id
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.mcp_url, json=payload, headers=headers
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logging.exception(f"MCP request failed for method {method}: {e}")
            error_detail = e.response.text
            try:
                error_json = e.response.json()
                if "error" in error_json and "message" in error_json["error"]:
                    error_detail = error_json["error"]["message"]
            except Exception as e_json:
                logging.exception(f"Error parsing error response JSON: {e_json}")
            return {
                "error": {"message": f"HTTP {e.response.status_code}: {error_detail}"}
            }
        except Exception as e:
            logging.exception(f"An unexpected error occurred during MCP request: {e}")
            return {"error": {"message": str(e)}}

    @rx.event
    async def initialize_mcp_session(self) -> str:
        """Initializes a session with the MCP server."""
        result = await self._make_jsonrpc_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "reflex-chat-app", "version": "0.1"},
            },
        )
        if "result" in result and "sessionId" in result["result"]:
            self.mcp_session_id = result["result"]["sessionId"]
            await self._make_jsonrpc_request("initialized", {})
            return "MCP session initialized."
        else:
            error_msg = result.get("error", {}).get(
                "message", "Failed to initialize session."
            )
            return f"Error: {error_msg}"

    @rx.event
    async def list_mcp_tools(self) -> str:
        """Lists available tools from the MCP server."""
        if not self.mcp_session_id:
            init_msg = await self.initialize_mcp_session()
            if "Error:" in init_msg:
                return init_msg
        result = await self._make_jsonrpc_request("tools/list")
        if "result" in result and "tools" in result["result"]:
            self.available_tools = result["result"]["tools"]
            return f"Found tools: {[tool['name'] for tool in self.available_tools]}"
        else:
            error_msg = result.get("error", {}).get("message", "Failed to list tools.")
            return f"Error: {error_msg}"

    @rx.event
    async def query_mcp_data(self, query: str) -> str:
        """Queries the MCP server for data context using the best available tool."""
        if not self.mcp_token:
            return "Error: MCP token is not set."
        if not self.mcp_session_id:
            init_msg = await self.initialize_mcp_session()
            if "Error:" in init_msg:
                return init_msg
        if not self.available_tools:
            list_msg = await self.list_mcp_tools()
            if "Error:" in list_msg:
                return list_msg
        tool_name = None
        for tool in self.available_tools:
            if "data_query" in tool.get("name", "") or "query" in tool.get("name", ""):
                tool_name = tool["name"]
                break
        if not tool_name:
            return "Error: No suitable data query tool found on MCP server."
        result = await self._make_jsonrpc_request(
            "tools/call", {"name": tool_name, "arguments": {"query": query}}
        )
        if "result" in result:
            return str(result["result"])
        else:
            error_msg = result.get("error", {}).get("message", "Tool call failed.")
            return f"MCP Error: {error_msg}"

    @rx.event
    async def on_submit(self, form_data: dict):
        user_input = form_data.get("user_input", "").strip()
        if not user_input or self.is_processing:
            return
        self.is_processing = True
        self.messages.append(Message(role="user", content=user_input))
        yield
        mcp_context = "No external context provided."
        if self.mcp_token:
            mcp_context = await self.query_mcp_data(user_input)
        prompt = f"Context from data source: {mcp_context}\n\nUser query: {user_input}\n\nBased ONLY on the context provided, answer the user's query. If the context is insufficient or contains an error, explain the problem to the user based on the error message."
        ai_response = ""
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_api_key:
            ai_response = "Error: OPENROUTER_API_KEY environment variable is not set."
            self.messages.append(Message(role="assistant", content=ai_response))
            self.is_processing = False
            return
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {openrouter_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model_name,
                        "messages": [
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": user_input},
                        ],
                    },
                )
                response.raise_for_status()
                result = response.json()
                ai_response = result["choices"][0]["message"]["content"]
        except httpx.ConnectError as e:
            logging.exception(f"Connection to OpenRouter failed: {e}")
            ai_response = "Error: Could not connect to OpenRouter. Please check your network connection."
        except httpx.HTTPStatusError as e:
            logging.exception(f"Error connecting to OpenRouter: {e}")
            ai_response = f"Error: API request failed (Status: {e.response.status_code}). Please check your API key and model name."
        except Exception as e:
            logging.exception(f"An unexpected error occurred: {e}")
            ai_response = (
                "An unexpected error occurred while communicating with the AI model."
            )
        self.messages.append(Message(role="assistant", content=ai_response))
        self.is_processing = False
        yield

    @rx.event
    def clear_chat(self):
        self.messages = []
        self.mcp_session_id = ""
        self.available_tools = []

    @rx.event
    def set_mcp_token(self, token: str):
        self.mcp_token = token
        self.mcp_session_id = ""
        self.available_tools = []