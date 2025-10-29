import reflex as rx
import logging
import httpx


class Message(rx.Base):
    role: str
    content: str


class ChatState(rx.State):
    messages: list[Message] = []
    is_processing: bool = False
    current_page: str = "Chat"
    mcp_url: str = "https://mcp.lemonado.io/mcp"
    mcp_token: str = ""
    ollama_base_url: str = "http://localhost:11434"
    model_name: str = "phi4-mini"

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
        prompt = f"Context from data source: {mcp_context}\n\nUser query: {user_input}\n\nBased ONLY on the context provided, answer the user's query. If the context is insufficient, say so."
        ai_response = ""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.ollama_base_url}/api/generate",
                    json={"model": self.model_name, "prompt": prompt, "stream": False},
                )
                response.raise_for_status()
                result = response.json()
                ai_response = result.get(
                    "response", "Sorry, I couldn't generate a response."
                )
        except httpx.HTTPStatusError as e:
            logging.exception(f"Error connecting to Ollama: {e}")
            ai_response = f"Error: Could not get a response from the AI model (Status: {e.response.status_code}). Please ensure Ollama is running and the model '{self.model_name}' is available."
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

    @rx.event
    def set_mcp_token(self, token: str):
        self.mcp_token = token

    @rx.event
    async def query_mcp_data(self, query: str):
        """Query MCP server for data context"""
        if not self.mcp_token:
            return "Please set your MCP token first."
        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {self.mcp_token}"}
                response = await client.post(
                    self.mcp_url, json={"query": query}, headers=headers
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    return f"MCP Error: {response.status_code}"
        except Exception as e:
            logging.exception(f"Error querying MCP server: {e}")
            return "Error connecting to MCP server"