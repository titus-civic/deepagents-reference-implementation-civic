import json
import os
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from deepagents import create_deep_agent
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from langchain_mcp_adapters.client import MultiServerMCPClient
from pydantic import BaseModel

# session_id -> list of {"role": "user"|"assistant", "content": str}
sessions: dict[str, list[dict]] = {}
_agent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _agent
    mcp = MultiServerMCPClient(
        {
            "civic-nexus": {
                "transport": "streamable_http",
                "url": os.environ["CIVIC_URL"],
                "headers": {"Authorization": f"Bearer {os.environ['CIVIC_TOKEN']}"},
            }
        }
    )
    tools = await mcp.get_tools()
    _agent = create_deep_agent(
        model="anthropic:claude-sonnet-4-6",
        tools=tools,
        system_prompt=(
            "You are a personal assistant with access to calendar and email tools "
            "via Civic Nexus. Help the user manage their schedule and read their "
            "emails. Be concise and direct."
        ),
    )
    yield


app = FastAPI(title="Civic DeepAgent", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


class ChatMessage(BaseModel):
    session_id: str
    message: str


@app.get("/")
async def index():
    with open("static/index.html") as f:
        return HTMLResponse(f.read())


@app.post("/session")
async def new_session():
    sid = str(uuid.uuid4())
    sessions[sid] = []
    return {"session_id": sid}


@app.post("/chat")
async def chat(req: ChatMessage):
    history = sessions.setdefault(req.session_id, [])
    history.append({"role": "user", "content": req.message})

    async def stream():
        response_text = ""
        try:
            async for event in _agent.astream_events(
                {"messages": history},
                version="v2",
            ):
                if event["event"] != "on_chat_model_stream":
                    continue
                content = event["data"]["chunk"].content
                # Anthropic streams content as a list of typed blocks
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text = block.get("text", "")
                            if text:
                                response_text += text
                                yield f"data: {json.dumps({'text': text})}\n\n"
                elif isinstance(content, str) and content:
                    response_text += content
                    yield f"data: {json.dumps({'text': content})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            if response_text:
                history.append({"role": "assistant", "content": response_text})
            yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")
