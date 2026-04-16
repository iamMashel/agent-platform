from langchain_google_genai import ChatGoogleGenerativeAI
from apps.api.config import settings
import os

if settings.google_api_key:
    os.environ["GOOGLE_API_KEY"] = settings.google_api_key

llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")


def planner_node(state):
    prompt = f"""
    You are a planner agent.

    Decide if the user needs a tool or direct answer.

    User input: {state['input']}

    Respond with:
    - "tool:search" OR
    - "final"
    """

    response = llm.invoke(prompt).content.strip().lower()

    return {"next_step": response}