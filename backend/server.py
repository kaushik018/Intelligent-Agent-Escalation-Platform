from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv
import json
import asyncio
from datetime import datetime
import hmac
import hashlib
import base64
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import redis.asyncio as redis

# Load environment variables
load_dotenv()

# Initialize Redis
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

# Initialize Firebase
cred = credentials.Certificate(os.getenv("FIREBASE_CREDENTIALS_PATH"))
firebase_admin.initialize_app(cred)
db = firestore.client()

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models


class HelpRequest(BaseModel):
    id: Optional[str] = None
    caller_details: Optional[Dict[str, Any]] = None
    question: Optional[str] = None
    context: Optional[str] = None
    status: str = "pending"
    supervisor_response: Optional[str] = None


class KnowledgeBaseEntry(BaseModel):
    question: str
    answer: str
    confidence: float
    last_updated: datetime = datetime.now()
    source: str = "predefined"  # "predefined" or "learned"
    verified: bool = True


class LearnedKnowledgeEntry(BaseModel):
    question: str
    answer: str
    confidence: float
    last_updated: datetime = datetime.now()
    verified: bool = False
    source_request_id: str
    supervisor_id: Optional[str] = None
    times_used: int = 0
    success_rate: float = 1.0


class LiveKitWebhook(BaseModel):
    event: str
    room: dict
    participant: Optional[dict] = None
    track: Optional[dict] = None
    recording: Optional[dict] = None

# WebSocket manager


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


def verify_livekit_signature(request: Request, body: bytes) -> bool:
    """Verify LiveKit webhook signature"""
    signature = request.headers.get("LiveKit-Signature")
    if not signature:
        return False

    api_secret = os.getenv("LIVEKIT_API_SECRET")
    if not api_secret:
        return False

    expected = hmac.new(
        api_secret.encode(),
        body,
        hashlib.sha256
    ).digest()
    expected_b64 = base64.b64encode(expected).decode()

    return hmac.compare_digest(signature, expected_b64)

# LiveKit Webhook endpoint


@app.post("/webhook/livekit")
async def livekit_webhook(request: Request):
    """Handle LiveKit webhook events"""
    try:
        # Log incoming request headers
        print("\n=== LiveKit Webhook Received ===")
        print(f"Headers: {dict(request.headers)}")

        body = await request.body()
        print(f"Raw body: {body.decode()}")

        # Verify webhook signature
        if not verify_livekit_signature(request, body):
            print(" Invalid signature!")
            raise HTTPException(status_code=401, detail="Invalid signature")
        print("Signature verified")

        data = json.loads(body)
        webhook = LiveKitWebhook(**data)
        print(f"Event type: {webhook.event}")
        print(f"Room: {webhook.room}")
        if webhook.participant:
            print(f"Participant: {webhook.participant}")

        # Handle different LiveKit events
        if webhook.event == "room.participant_joined":
            print(f"Participant joined: {webhook.participant['identity']}")
            # Notify supervisors
            await manager.broadcast(json.dumps({
                "type": "participant_joined",
                "data": {
                    "participant": webhook.participant,
                    "room": webhook.room
                }
            }))
            print(" Supervisor notified")

        elif webhook.event == "room.participant_left":
            print(f"Participant left: {webhook.participant['identity']}")
            # Notify supervisors
            await manager.broadcast(json.dumps({
                "type": "participant_left",
                "data": {
                    "participant": webhook.participant,
                    "room": webhook.room
                }
            }))
            print("Supervisor notified")

        elif webhook.event == "room.recording_started":
            print(f"Recording started in room: {webhook.room['name']}")
            # Handle recording start

        elif webhook.event == "room.recording_finished":
            print(f"Recording finished in room: {webhook.room['name']}")
            # Handle recording finish

        print("=== Webhook Processing Complete ===\n")
        return {"status": "success"}

    except Exception as e:
        print(f" Error handling LiveKit webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Routes


@app.on_event("startup")
async def startup():
    await FastAPILimiter.init(redis_client)


@app.get("/", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def root():
    return {"message": "Salon AI Receptionist API"}


@app.post("/help-requests/")
async def create_help_request(request: HelpRequest):
    try:
        # Add to Firebase
        doc_ref = db.collection('help_requests').document()
        request.id = doc_ref.id
        doc_ref.set(request.dict())

        # Notify supervisors via WebSocket
        await manager.broadcast(json.dumps({
            "type": "new_request",
            "data": request.dict()
        }))

        return {"message": "Help request created", "request_id": request.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/help-requests/")
async def get_help_requests(status: Optional[str] = None):
    try:
        collection = db.collection('help_requests')
        if status:
            collection = collection.where('status', '==', status)
        docs = collection.stream()
        requests = [doc.to_dict() for doc in docs]
        return requests
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/help-requests/{request_id}")
async def update_help_request(request_id: str, request: HelpRequest):
    try:
        print(f"Received request data: {request.dict()}")
        print(f"Request ID: {request_id}")

        # Get the current document
        doc_ref = db.collection('help_requests').document(request_id)
        current_doc = doc_ref.get()

        if not current_doc.exists:
            return JSONResponse(
                status_code=404,
                content={"detail": "Help request not found"}
            )

        # Create update data - ensure all fields are included
        update_data = {
            "status": request.status,
            "supervisor_response": request.supervisor_response,
            "timestamp": datetime.now().isoformat()
        }

        # Only update question if provided
        if request.question:
            update_data["question"] = request.question

        print(f"Update data: {update_data}")

        # Update the document
        doc_ref.set(update_data, merge=True)
        print(f"Document updated successfully")

        # If request is resolved, update knowledge base
        if request.status == "resolved" and request.supervisor_response:
            print("Updating knowledge base...")
            current_question = current_doc.get('question')
            await update_knowledge_base(current_question, request.supervisor_response, request_id)

        return JSONResponse(
            status_code=200,
            content={"message": "Help request updated", "data": update_data}
        )
    except Exception as e:
        print(f"Error updating help request: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": str(e)}
        )


@app.post("/knowledge-base/")
async def add_knowledge_entry(entry: KnowledgeBaseEntry):
    try:
        doc_ref = db.collection('knowledge_base').document()
        doc_ref.set(entry.dict())
        return {"message": "Knowledge base entry added"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/knowledge-base/")
async def search_knowledge_base(query: Optional[str] = Query(None)):
    try:
        collection = db.collection('knowledge_base')
        docs = collection.stream()
        entries = [doc.to_dict() for doc in docs]

        if query:
            # Filter entries based on query
            entries = [entry for entry in entries if query.lower()
                       in entry['question'].lower()]

        return entries
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/learned-knowledge/")
async def add_learned_entry(entry: LearnedKnowledgeEntry):
    try:
        doc_ref = db.collection('learned_knowledge').document()
        doc_ref.set(entry.dict())
        return {"message": "Learned knowledge entry added"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/learned-knowledge/")
async def search_learned_knowledge(query: Optional[str] = Query(None)):
    try:
        collection = db.collection('learned_knowledge')
        docs = collection.stream()
        entries = [doc.to_dict() for doc in docs]

        if query:
            entries = [entry for entry in entries if query.lower()
                       in entry['question'].lower()]

        return entries
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/learned-knowledge/{entry_id}/verify")
async def verify_learned_entry(entry_id: str, verified: bool = True):
    try:
        doc_ref = db.collection('learned_knowledge').document(entry_id)
        doc_ref.update({
            "verified": verified,
            "last_updated": datetime.now().isoformat()
        })
        return {"message": "Learned knowledge entry verified"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for real-time updates


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages from supervisors
            message = json.loads(data)
            if message["type"] == "supervisor_response":
                await handle_supervisor_response(message["data"])
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def handle_supervisor_response(data):
    # Update help request
    request_id = data["request_id"]
    response = data["response"]

    # Get the current help request to get the question
    doc_ref = db.collection('help_requests').document(request_id)
    current_doc = doc_ref.get()
    question = current_doc.get('question') if current_doc.exists else None

    # Update the help request with the question included
    await update_help_request(request_id, HelpRequest(
        status="resolved",
        supervisor_response=response,
        question=question
    ))

    # Broadcast the response with question included
    await manager.broadcast(json.dumps({
        "type": "supervisor_response",
        "data": {
            "request_id": request_id,
            "response": response,
            "question": question
        }
    }))


async def update_knowledge_base(question: str, answer: str, request_id: str):
    try:
        print(
            f"Adding to learned knowledge base - Question: {question}, Answer: {answer}")
        entry = LearnedKnowledgeEntry(
            question=question,
            answer=answer,
            confidence=1.0,
            source_request_id=request_id
        )
        doc_ref = db.collection('learned_knowledge').document()
        doc_ref.set(entry.dict())
        print("Learned knowledge entry added successfully")
    except Exception as e:
        print(f"Error updating learned knowledge base: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to update learned knowledge base: {str(e)}")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred"}
    )


@app.put("/knowledge-base/{entry_id}")
async def update_knowledge_entry(entry_id: str, entry: KnowledgeBaseEntry):
    try:
        doc_ref = db.collection('knowledge_base').document(entry_id)
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="Entry not found")

        doc_ref.update(entry.dict())
        return {"message": "Knowledge base entry updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/knowledge-base/{entry_id}")
async def delete_knowledge_entry(entry_id: str):
    try:
        doc_ref = db.collection('knowledge_base').document(entry_id)
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="Entry not found")

        doc_ref.delete()
        return {"message": "Knowledge base entry deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/knowledge-base/predefined/")
async def get_predefined_knowledge():
    try:
        collection = db.collection('knowledge_base')
        docs = collection.where('source', '==', 'predefined').stream()
        entries = [doc.to_dict() for doc in docs]
        return entries
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/knowledge-base/learned/")
async def get_learned_knowledge():
    try:
        collection = db.collection('learned_knowledge')
        docs = collection.stream()
        entries = [doc.to_dict() for doc in docs]
        return entries
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/knowledge-base/predefined/")
async def add_predefined_knowledge(entry: KnowledgeBaseEntry):
    try:
        entry.source = "predefined"
        entry.verified = True
        doc_ref = db.collection('knowledge_base').document()
        doc_ref.set(entry.dict())
        return {"message": "Predefined knowledge entry added"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/knowledge-base/learned/")
async def add_learned_knowledge(entry: dict):
    try:
        # Ensure required fields are present
        if not all(key in entry for key in ['question', 'answer', 'confidence']):
            raise HTTPException(
                status_code=422, detail="Missing required fields")

        # Create new entry with default values
        new_entry = {
            'question': entry['question'],
            'answer': entry['answer'],
            'confidence': entry['confidence'],
            'verified': entry.get('verified', False),
            'last_updated': entry.get('last_updated', datetime.now().isoformat()),
            'times_used': 0,
            'success_rate': 1.0,
            'source_request_id': entry.get('source_request_id', ''),
            'supervisor_id': entry.get('supervisor_id', None)
        }

        doc_ref = db.collection('learned_knowledge').document()
        doc_ref.set(new_entry)
        return {"message": "Learned knowledge entry added", "id": doc_ref.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/knowledge-base/predefined/{entry_id}")
async def update_predefined_knowledge(entry_id: str, entry: KnowledgeBaseEntry):
    try:
        doc_ref = db.collection('knowledge_base').document(entry_id)
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="Entry not found")

        entry.source = "predefined"
        entry.verified = True
        doc_ref.update(entry.dict())
        return {"message": "Predefined knowledge entry updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/knowledge-base/learned/{entry_id}")
async def update_learned_knowledge(entry_id: str, entry: dict):
    try:
        # Validate entry_id
        if not entry_id or entry_id == "undefined":
            raise HTTPException(status_code=400, detail="Invalid entry ID")

        # Get reference to the document
        doc_ref = db.collection('learned_knowledge').document(entry_id)

        # Check if document exists
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Entry not found")

        # Ensure required fields are present
        if not all(key in entry for key in ['question', 'answer', 'confidence']):
            raise HTTPException(
                status_code=422, detail="Missing required fields")

        # Update the document
        update_data = {
            'question': entry['question'],
            'answer': entry['answer'],
            'confidence': entry['confidence'],
            'verified': entry.get('verified', False),
            'last_updated': datetime.now().isoformat(),
            'times_used': entry.get('times_used', 0),
            'success_rate': entry.get('success_rate', 1.0)
        }

        doc_ref.update(update_data)
        return {"message": "Learned knowledge entry updated successfully", "id": entry_id}
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error updating learned knowledge entry: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/knowledge-base/predefined/{entry_id}")
async def delete_predefined_knowledge(entry_id: str):
    try:
        doc_ref = db.collection('knowledge_base').document(entry_id)
        if not doc_ref.get().exists:
            raise HTTPException(status_code=404, detail="Entry not found")

        doc_ref.delete()
        return {"message": "Predefined knowledge entry deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/knowledge-base/learned/{entry_id}")
async def delete_learned_knowledge(entry_id: str):
    try:
        # Get reference to the document
        doc_ref = db.collection('learned_knowledge').document(entry_id)

        # Check if document exists
        doc = doc_ref.get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Entry not found")

        # Delete the document
        doc_ref.delete()

        return {"message": "Learned knowledge entry deleted successfully", "id": entry_id}
    except Exception as e:
        print(f"Error deleting learned knowledge entry: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
