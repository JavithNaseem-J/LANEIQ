import json
import logging
from groq import Groq
from config.agents import PLANNER_SYSTEM_PROMPT, PLANNER_TOOL_SCHEMA
from config.settings import settings
from src.agents.state import AgentState

logger = logging.getLogger(__name__)

MODEL = "llama-3.3-70b-versatile"


def planner_node(state: AgentState) -> AgentState:
    """
    Planner Agent node.
    Reads state["shipment_brief"] and writes state["decomposed_tasks"].
    """
    brief = state.get("shipment_brief", "")
    if not brief:
        logger.warning("[planner_node] shipment_brief is empty — skipping.")
        return {**state, "error": "shipment_brief is empty", "decomposed_tasks": []}

    if state.get("error"):
        logger.warning("[planner_node] upstream error detected — skipping.")
        return state

    logger.info("[planner_node] decomposing brief: %s", brief[:80])

    try:
        client = Groq(api_key=settings.GROQ_API_KEY)

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                {"role": "user", "content": brief},
            ],
            tools=[PLANNER_TOOL_SCHEMA],
            tool_choice={"type": "function", "function": {"name": "extract_shipment"}},
            temperature=0.0,
        )

        message = response.choices[0].message

        if not message.tool_calls:
            raise ValueError("Model did not return a tool call.")

        tool_call = message.tool_calls[0]
        extracted = json.loads(tool_call.function.arguments)

        logger.info("[planner_node] extracted fields: %s", extracted)

        return {**state, "decomposed_tasks": [extracted], "error": None}

    except Exception as exc:
        logger.error("[planner_node] error: %s", exc)
        return {**state, "decomposed_tasks": [], "error": str(exc)}
