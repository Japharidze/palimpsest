import operator
from typing import Annotated, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from palimpsest.agent.tools import Toolbox, build_registry
from palimpsest.llm import LLM


class MessagesState(TypedDict):
    messages: Annotated[list[dict], operator.add]


def build_graph(conn, embedder, model: LLM):
    tools = build_registry(Toolbox(conn, embedder))

    def agent_node(state: MessagesState):
        response = model.chat(state["messages"], tools=list(tools.values()))
        return {
            "messages": [
                {
                    "role": "assistant",
                    "content": response.text,
                    "tool_calls": response.tool_calls,
                }
            ]
        }

    def tool_node(state: MessagesState):
        last_message = state["messages"][-1]
        out = []
        for tool in last_message.get("tool_calls") or []:
            fn = tools.get(tool.function.name)
            if fn is None:
                result = (
                    f"Unknown tool {tool.function.name!r}."
                    f"Available: {', '.join(tools)}."
                )
            else:
                try:
                    result = fn(**tool.function.arguments)
                except TypeError as e:
                    result = f"Invalid arguments for {tool.function.name}: {e}"
            out.append(
                {
                    "role": "tool",
                    "tool_name": tool.function.name,
                    "content": str(result),
                }
            )

        return {"messages": out}

    def should_continue(state: MessagesState) -> Literal["tool_node", END]: # type: ignore
        if state["messages"][-1].get("tool_calls"):
            return "tool_node"
        return END

    agent_builder = StateGraph(MessagesState)

    agent_builder.add_node("agent_node", agent_node)
    agent_builder.add_node("tool_node", tool_node)

    agent_builder.add_edge(START, "agent_node")
    agent_builder.add_conditional_edges(
        "agent_node", should_continue, ["tool_node", END]
    )
    agent_builder.add_edge("tool_node", "agent_node")

    return agent_builder.compile()
