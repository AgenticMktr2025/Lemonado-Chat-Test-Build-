import reflex as rx
from app.states.state import ChatState


def chat_settings() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.h3(
                "Chat Settings", class_name="text-lg font-semibold text-gray-800 mb-4"
            ),
            rx.el.div(
                rx.el.label(
                    "Model:", class_name="block text-sm font-medium text-gray-700 mb-2"
                ),
                rx.el.select(
                    rx.foreach(
                        ChatState.model_options,
                        lambda option: rx.el.option(option, value=option),
                    ),
                    value=ChatState.model_name,
                    on_change=ChatState.set_model_name,
                    class_name="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500",
                ),
                class_name="mb-4",
            ),
            rx.el.button(
                "Clear Chat",
                on_click=ChatState.clear_chat,
                class_name="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors",
            ),
            class_name="bg-white p-4 rounded-lg shadow border-l-4 border-blue-500",
        ),
        class_name="mb-6",
    )