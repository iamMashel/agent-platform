from langchain_google_genai import ChatGoogleGenerativeAI
from apps.api.config import settings
import os

if settings.google_api_key:
    os.environ["GOOGLE_API_KEY"] = settings.google_api_key

llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")


def synth_node(state):
    prompt = f"""
    You are an assistant.

    User input: {state['input']}
    Tool result: {state.get('tool_result')}

    Produce a final helpful answer.
    """

    response = llm.invoke(prompt).content

    return {"final_output": response}