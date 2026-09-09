import operator
from typing import Annotated, Literal, TypedDict

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from palimpsest.agent.prompts import SYSTEM_PROMPT
from palimpsest.agent.tools import Toolbox, build_registry
from palimpsest.agent.validation import check_citations


class MessagesState(TypedDict):
    messages: Annotated[list[dict], operator.add]
    iterations: int
    citation_problems: list[str]


def build_graph(pool, embedder, model, iter_cap: int = 8):
    tools = build_registry(Toolbox(pool, embedder))
    model_with_tools = model.bind_tools(list(tools.values()))

    def agent_node(state: MessagesState):
        msgs = [{"role": "system", "content": SYSTEM_PROMPT}] + state["messages"]
        response = model_with_tools.invoke(msgs)
        return {
            "messages": [
                {
                    "role": "assistant",
                    "content": response.text,
                    "tool_calls": response.tool_calls,
                }
            ],
            "iterations": state["iterations"] + 1,
        }

    def tool_node(state: MessagesState):
        last_message = state["messages"][-1]
        out = []
        for tool in last_message.get("tool_calls") or []:
            fn = tools.get(tool["name"])
            if fn is None:
                result = f"Unknown tool {tool['name']!r}.Available: {', '.join(tools)}."
            else:
                try:
                    result = fn.invoke(tool["args"])
                except (TypeError, ValueError, ValidationError) as e:
                    result = f"Invalid arguments for {tool['name']}: {e}"
            out.append(
                {
                    "role": "tool",
                    "tool_call_id": tool["id"],
                    "content": str(result),
                }
            )

        return {"messages": out}

    def validator_node(state: MessagesState):
        answer = state["messages"][-1]["content"]
        problems = check_citations(pool, answer)
        return {"citation_problems": problems}

    def should_continue(state: MessagesState) -> Literal["tool_node", END]:  # type: ignore
        if state["iterations"] >= iter_cap:
            return END
        if not state["messages"][-1].get("tool_calls"):
            return "validator_node"
        return "tool_node"

    agent_builder = StateGraph(MessagesState)

    agent_builder.add_node("agent_node", agent_node)
    agent_builder.add_node("tool_node", tool_node)
    agent_builder.add_node("validator_node", validator_node)

    agent_builder.add_edge(START, "agent_node")
    agent_builder.add_edge("validator_node", END)
    agent_builder.add_conditional_edges(
        "agent_node", should_continue, ["tool_node", "validator_node", END]
    )
    agent_builder.add_edge("tool_node", "agent_node")

    with pool.connection() as conn:
        conn.autocommit = True
        PostgresSaver(conn).setup()
        conn.autocommit = False

    checkpointer = PostgresSaver(pool)

    return agent_builder.compile(checkpointer=checkpointer)
