import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Utility to validate ObjectId strings
class ObjectIdStr(BaseModel):
    id: str

    @property
    def oid(self) -> ObjectId:
        try:
            return ObjectId(self.id)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid ID")


# Auth models (simple email-based login placeholder)
class LoginRequest(BaseModel):
    name: str
    email: str
    avatar_url: Optional[str] = None


@app.get("/")
def read_root():
    return {"message": "Backend ready"}


@app.post("/auth/login")
def login(req: LoginRequest):
    # Upsert user by email
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    existing = db["user"].find_one({"email": req.email})
    if existing:
        db["user"].update_one({"_id": existing["_id"]}, {"$set": {"name": req.name, "avatar_url": req.avatar_url}})
        user_id = str(existing["_id"])
    else:
        user_id = create_document("user", req.dict())
    return {"user_id": user_id}


# Project endpoints
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


@app.post("/projects")
def create_project(payload: ProjectCreate, user_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    data = {"user_id": user_id, **payload.dict()}
    project_id = create_document("project", data)
    return {"project_id": project_id}


@app.get("/projects")
def list_projects(user_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    projects = get_documents("project", {"user_id": user_id})
    # Convert ObjectIds
    for p in projects:
        p["_id"] = str(p["_id"]) if "_id" in p else None
    return {"projects": projects}


# Chat endpoints
class ChatCreate(BaseModel):
    project_id: str
    title: str


@app.post("/chats")
def create_chat(payload: ChatCreate, user_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    # validate project belongs to user
    proj = db["project"].find_one({"_id": ObjectId(payload.project_id), "user_id": user_id})
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    chat_id = create_document("chat", payload.dict())
    return {"chat_id": chat_id}


@app.get("/chats")
def list_chats(project_id: str, user_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    # verify access
    proj = db["project"].find_one({"_id": ObjectId(project_id), "user_id": user_id})
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    chats = get_documents("chat", {"project_id": project_id})
    for c in chats:
        c["_id"] = str(c["_id"]) if "_id" in c else None
    return {"chats": chats}


# Messages
class MessageCreate(BaseModel):
    chat_id: str
    role: str
    content: str


@app.post("/messages")
def create_message(payload: MessageCreate, user_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    # validate chat belongs to user via project
    chat = db["chat"].find_one({"_id": ObjectId(payload.chat_id)})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    proj = db["project"].find_one({"_id": ObjectId(chat["project_id"]), "user_id": user_id})
    if not proj:
        raise HTTPException(status_code=403, detail="Forbidden")
    msg_id = create_document("message", payload.dict())
    return {"message_id": msg_id}


@app.get("/messages")
def list_messages(chat_id: str, user_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    chat = db["chat"].find_one({"_id": ObjectId(chat_id)})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")
    proj = db["project"].find_one({"_id": ObjectId(chat["project_id"]), "user_id": user_id})
    if not proj:
        raise HTTPException(status_code=403, detail="Forbidden")
    msgs = get_documents("message", {"chat_id": chat_id})
    for m in msgs:
        m["_id"] = str(m["_id"]) if "_id" in m else None
    return {"messages": msgs}


# Simple echo assistant for now
class CompletionRequest(BaseModel):
    chat_id: str
    prompt: str


@app.post("/assistant/complete")
def assistant_complete(req: CompletionRequest, user_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    # Very simple echo logic to mock agent response
    reply = f"Echo: {req.prompt}"
    # store user prompt and assistant reply
    create_document("message", {"chat_id": req.chat_id, "role": "user", "content": req.prompt})
    create_document("message", {"chat_id": req.chat_id, "role": "assistant", "content": reply})
    return {"reply": reply}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
