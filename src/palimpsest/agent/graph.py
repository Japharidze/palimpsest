from palimpsest.agent.tools import Toolbox, build_registry
from palimpsest.llm import LLM


def loop(
    conn,
    embedder,
    model: LLM,
    messages: list[dict],
    iteration: int = 0,
    iter_cap: int = 8,
):
    if iteration == iter_cap:
        prompt = ". ".join([x["content"] for x in messages])
        return model.complete(
            f"failure message for agent loop after this messages {prompt}"
        ).text

    tools = build_registry(Toolbox(conn, embedder))

    response = model.chat(messages, list(tools.values()))
    messages.append({"role": "assistant", "content": response.text})

    if not response.tool_calls:
        return response.text

    print(response.tool_calls)
    for tool in response.tool_calls:
        fn = tools.get(tool.function.name)
        if fn is None:
            result = (
                f"Unknown tool {tool.function.name!r}. "
                f"Available: {', '.join(tools)}."
            )
        else:
            try:
                result = fn(**tool.function.arguments)
            except TypeError as e:
                result = f"Invalid arguments for {tool.function.name}: {e}"

        messages.append({
            "role": "tool",
            "tool_name": tool.function.name,
            "content": str(result),
        })

    iteration += 1
    return loop(conn, embedder, model, messages, iteration)
