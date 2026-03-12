# deepagents-reference-implementation-civic

A reference implementation showing how to connect [LangChain DeepAgents](https://github.com/langchain-ai/deepagents) to [Civic Nexus](https://docs.civic.com/nexus/quickstart/clients/agents) via MCP to create a personal calendar and email assistant.

## How it works

1. On startup, the app connects to Civic Nexus over HTTP MCP (`streamable_http`) and fetches the tool list for your profile.
2. Those tools are passed into `create_deep_agent`, which wires them into a LangGraph agent alongside DeepAgents' built-in tools (file system, todos, sub-agents).
3. A FastAPI server exposes a `/chat` endpoint that streams agent responses via SSE.
4. A minimal chat UI in `static/index.html` connects to that endpoint.

## Setup

```bash
cp .env.example .env
# Fill in CIVIC_TOKEN, CIVIC_URL, ANTHROPIC_API_KEY

uv sync
uv run uvicorn main:app --reload
```

Open http://localhost:8000.

## Environment variables

| Variable | Description |
|---|---|
| `CIVIC_TOKEN` | Token from [nexus.civic.com](https://nexus.civic.com) |
| `CIVIC_URL` | Full MCP hub URL including `accountId`, `profile`, and `lock=true` |
| `ANTHROPIC_API_KEY` | Anthropic API key |

The `lock=true` query param in `CIVIC_URL` prevents the agent from switching profiles mid-session (recommended for all non-interactive deployments).
