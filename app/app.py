import reflex as rx
from app.states.state import ChatState
from app.components.chat_settings import chat_settings


def message_bubble(message: rx.Var[dict]) -> rx.Component:
    is_user = message["role"] == "user"
    return rx.el.div(
        rx.el.div(
            rx.el.p(message["content"], class_name="text-sm leading-relaxed"),
            class_name=rx.cond(
                is_user, "bg-blue-500 text-white", "bg-gray-100 text-gray-800"
            )
            + " p-3 rounded-lg max-w-md",
        ),
        class_name=rx.cond(is_user, "flex justify-end mb-4", "flex justify-start mb-4"),
    )


def chat_interface() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.h1(
                "Lemonado MCP Chat", class_name="text-2xl font-bold text-gray-800 mb-2"
            ),
            rx.el.p(
                "Chat with your Google Ads and GA4 data using natural language",
                class_name="text-gray-600 mb-6",
            ),
            class_name="text-center",
        ),
        chat_settings(),
        rx.el.div(
            rx.el.div(
                rx.cond(
                    ChatState.messages.length() > 0,
                    rx.foreach(ChatState.messages, message_bubble),
                    rx.el.div(
                        rx.el.p(
                            "👋 Hi! I'm ready to help you analyze your Google Ads and GA4 data.",
                            class_name="text-gray-600 text-center",
                        ),
                        rx.el.p(
                            "Try asking something like: 'Show me my top performing campaigns this month'",
                            class_name="text-sm text-gray-500 text-center mt-2",
                        ),
                        class_name="flex flex-col items-center justify-center h-40 border-2 border-dashed border-gray-300 rounded-lg",
                    ),
                ),
                class_name="flex-1 overflow-y-auto p-4 bg-white rounded-lg border min-h-[400px] max-h-[500px]",
            ),
            rx.el.form(
                rx.el.div(
                    rx.el.input(
                        placeholder="Ask about your Google Ads or GA4 data...",
                        name="user_input",
                        disabled=ChatState.is_processing,
                        class_name="flex-1 p-3 border border-gray-300 rounded-l-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
                    ),
                    rx.el.button(
                        rx.cond(ChatState.is_processing, "Thinking...", "Send"),
                        type="submit",
                        disabled=ChatState.is_processing,
                        class_name=rx.cond(
                            ChatState.is_processing,
                            "px-6 py-3 bg-gray-400 text-white rounded-r-lg cursor-not-allowed",
                            "px-6 py-3 bg-blue-500 text-white rounded-r-lg hover:bg-blue-600 transition-colors",
                        ),
                    ),
                    class_name="flex",
                ),
                on_submit=ChatState.on_submit,
                reset_on_submit=True,
                class_name="mt-4",
            ),
            class_name="flex flex-col",
        ),
        class_name="max-w-4xl mx-auto p-6 min-h-screen bg-gray-50 font-['Inter']",
    )


@rx.page(route="/")
def index() -> rx.Component:
    return chat_interface()


app = rx.App(
    theme=rx.theme(appearance="light"),
    head_components=[
        rx.el.link(rel="preconnect", href="https://fonts.googleapis.com"),
        rx.el.link(rel="preconnect", href="https://fonts.gstatic.com", cross_origin=""),
        rx.el.link(
            href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap",
            rel="stylesheet",
        ),
    ],
)