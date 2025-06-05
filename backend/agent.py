import asyncio
import json
import os
import logging
import datetime
from dotenv import load_dotenv
import websockets
import requests
from datetime import datetime

from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import (
    openai,
    cartesia,
    deepgram,
    noise_cancellation,
    silero,
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from livekit.agents.llm.chat_context import ChatContext, ChatMessage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()


class SalonReceptionistAgent(Agent):
    def __init__(self) -> None:
        print("[SalonReceptionistAgent] __init__ called")
        super().__init__(
            instructions="""You are a professional salon receptionist AI assistant. Your role is to:
            1. Greet customers warmly and professionally
            2. Handle appointment scheduling and inquiries
            3. Provide information about salon services and pricing
            4. Answer questions about staff availability and expertise
            5. Escalate complex queries to human supervisors when needed
            6. Maintain a helpful and friendly tone throughout the conversation
            
            If you don't know the answer or need human intervention, say: 'Let me check with my supervisor and get back to you.'"""
        )
        self.backend_url = "http://localhost:8000"
        self.predefined_knowledge = {}  # Pre-defined knowledge base
        self.learned_knowledge = {}     # Learned knowledge base
        self.websocket = None
        self._initialized = False

    async def initialize(self):
        """Initialize the agent"""
        if not self._initialized:
            await self.load_knowledge_bases()
            await self.connect_to_server()
            self._initialized = True

    async def load_knowledge_bases(self):
        """Load both predefined and learned knowledge bases"""
        try:
            # Load predefined knowledge
            response = requests.get(
                f"{self.backend_url}/knowledge-base/predefined/")
            if response.status_code == 200:
                self.predefined_knowledge = {
                    entry["question"].lower(): {
                        "answer": entry["answer"],
                        "confidence": 1.0,
                        "verified": True
                    }
                    for entry in response.json()
                }
                logger.info(
                    f"Loaded {len(self.predefined_knowledge)} predefined knowledge entries")

            # Load learned knowledge
            response = requests.get(
                f"{self.backend_url}/knowledge-base/learned/")
            if response.status_code == 200:
                self.learned_knowledge = {
                    entry["question"].lower(): {
                        "answer": entry["answer"],
                        "confidence": entry["confidence"],
                        "verified": entry["verified"],
                        "times_used": entry["times_used"],
                        "success_rate": entry["success_rate"],
                        # Store the document ID for updates
                        "id": entry.get("id")
                    }
                    for entry in response.json()
                }
                logger.info(
                    f"Loaded {len(self.learned_knowledge)} learned knowledge entries")
        except Exception as e:
            logger.error(f"Error loading knowledge bases: {str(e)}")

    async def connect_to_server(self):
        """Connect to the server's WebSocket endpoint"""
        try:
            self.websocket = await websockets.connect(f"ws://localhost:8000/ws")
            logger.info("Connected to server WebSocket")
            asyncio.create_task(self.listen_for_messages())
        except Exception as e:
            logger.error(f"Failed to connect to server: {str(e)}")

    async def listen_for_messages(self):
        """Listen for messages from the server"""
        try:
            while True:
                message = await self.websocket.recv()
                data = json.loads(message)
                if data["type"] == "supervisor_response":
                    await self.handle_supervisor_response(data["data"])
        except websockets.exceptions.ConnectionClosed:
            logger.error("WebSocket connection closed")
        except Exception as e:
            logger.error(f"Error in message listener: {str(e)}")

    async def handle_supervisor_response(self, data):
        print(f"[handle_supervisor_response] Received data: {data}")
        try:
            request_id = data["request_id"]
            supervisor_answer = data["response"]
            question = data.get("question", "")

            if not question:
                logger.error("No question provided in supervisor response")
                return

            # Update the help request status
            requests.put(
                f"{self.backend_url}/help-requests/{request_id}",
                json={
                    "status": "resolved",
                    "supervisor_response": supervisor_answer,
                    "question": question
                }
            )

            # Add to learned knowledge base
            learned_entry = {
                "question": question,
                "answer": supervisor_answer,
                "confidence": 1.0,
                "verified": False,
                "source_request_id": request_id,
                "times_used": 0,
                "success_rate": 1.0
            }

            # Add to backend
            resp = requests.post(
                f"{self.backend_url}/knowledge-base/learned/",
                json=learned_entry
            )

            if resp.status_code == 200:
                print("[handle_supervisor_response] Learned knowledge added")
                # Update local knowledge base
                self.learned_knowledge[question.lower()] = {
                    **learned_entry,
                    "id": resp.json().get("id")
                }
                logger.info(f"Added new learned knowledge: {question}")
            else:
                print(
                    f"[handle_supervisor_response] Failed to add learned knowledge: {resp.text}")
            await self.speak_response(supervisor_answer)
            print("[handle_supervisor_response] Supervisor answer spoken")

        except Exception as e:
            print(f"[handle_supervisor_response] Error: {str(e)}")

    async def check_knowledge_base(self, query: str) -> str:
        """Check both knowledge bases for an answer"""
        print(f"[check_knowledge_base] Checking for: {query}")
        query = query.lower()

        if query in self.predefined_knowledge:
            print("[check_knowledge_base] Found in predefined")
            entry = self.predefined_knowledge[query]
            return entry["answer"]

        if query in self.learned_knowledge:
            entry = self.learned_knowledge[query]
            print(
                f"[check_knowledge_base] Found in learned, verified: {entry['verified']}, confidence: {entry['confidence']}, success_rate: {entry['success_rate']}")
            if entry["verified"] or (entry["confidence"] > 0.8 and entry["success_rate"] > 0.8):
                entry["times_used"] += 1
                if entry.get("id"):
                    try:
                        requests.put(
                            f"{self.backend_url}/knowledge-base/learned/{entry['id']}",
                            json={
                                "question": query,
                                "answer": entry["answer"],
                                "confidence": entry["confidence"],
                                "verified": entry["verified"],
                                "times_used": entry["times_used"],
                                "success_rate": entry["success_rate"]
                            }
                        )
                    except Exception as e:
                        print(
                            f"[check_knowledge_base] Error updating usage: {str(e)}")
                return entry["answer"]

        print("[check_knowledge_base] Not found in any knowledge base")
        return None

    async def create_help_request(self, question: str, track_id: str):
        """Create a help request via server"""
        print(
            f"[create_help_request] Creating help request for: {question}, track_id: {track_id}")
        try:
            help_request = {
                "caller_details": {
                    "track_id": track_id,
                    "timestamp": datetime.now().isoformat()
                },
                "question": question,
                "context": f"Call from track {track_id}",
                "status": "pending"
            }

            response = requests.post(
                f"{self.backend_url}/help-requests/",
                json=help_request
            )

            if response.status_code == 200:
                print("[create_help_request] Help request created successfully")
                await self.speak_response("Let me check with my supervisor and get back to you.")
            else:
                print(
                    f"[create_help_request] Failed to create help request: {response.text}")
                await self.speak_response("I apologize, but I'm having trouble processing your request. Please try again in a moment.")
        except Exception as e:
            print(f"[create_help_request] Exception: {str(e)}")
            await self.speak_response("I apologize, but I'm having trouble processing your request. Please try again in a moment.")

    async def speak_response(self, text: str):
        print(f"[speak_response] Called with text: {text}")
        print(f"[speak_response] Text type: {type(text)}")
        print(f"[speak_response] Session exists: {hasattr(self, 'session')}")
        print(
            f"[speak_response] Session value: {self.session if hasattr(self, 'session') else 'None'}")
        try:
            if hasattr(self, 'session') and self.session:
                print("[speak_response] Generating reply")
                await self.session.generate_reply(
                    instructions=f"Say this to the caller: {text}"
                )
                print("[speak_response] Reply generated")
            else:
                print("[speak_response] Session is NOT set!")
                logger.error("Session is not set on the agent!")
        except Exception as e:
            print(f"[speak_response] Error: {str(e)}")
            logger.error(f"Error speaking response: {str(e)}")

    async def on_user_turn_completed(self, turn_ctx, new_message):
        print("[on_user_turn_completed] Called")
        user_text = getattr(new_message, "content", str(new_message))
        # Always flatten lists to a string
        if isinstance(user_text, list):
            user_text = " ".join(str(x) for x in user_text)
        print(f"[on_user_turn_completed] User said: {user_text}")

        try:
            # Check knowledge base first
            answer = await self.check_knowledge_base(user_text)
            print(f"[on_user_turn_completed] Knowledge base answer: {answer}")
            if answer:
                print("[on_user_turn_completed] Using knowledge base answer")
                await self.speak_response(answer)
                return

            # If not in knowledge base, try OpenAI
            print("[on_user_turn_completed] Trying OpenAI")
            print("[ask_openai] llm.chat signature:",
                  dir(self.session.llm.chat))
            openai_response = await self.ask_openai(user_text)
            print(
                f"[on_user_turn_completed] OpenAI response: {openai_response}")
            if openai_response:
                print("[on_user_turn_completed] Using OpenAI response")
                await self.speak_response(openai_response)
                return

            print("[on_user_turn_completed] No response found, creating help request")
            await self.create_help_request(user_text, getattr(turn_ctx, 'track_id', None))

        except Exception as e:
            print(f"[on_user_turn_completed] Error: {str(e)}")
            await self.speak_response("I apologize, but I'm having trouble processing your request. Please try again in a moment.")

    async def ask_openai(self, message: str) -> str:
        print(f"[ask_openai] Processing message: {message}")
        try:
            # Ensure chat_context exists
            if not hasattr(self.session, "chat_context") or self.session.chat_context is None:
                self.session.chat_context = ChatContext()
                print("[ask_openai] ChatContext dir:",
                      dir(self.session.chat_context))

            # Add the user message to the context using ChatMessage and add_message
            user_msg = ChatMessage(role="user", content=[message])
            self.session.chat_context.add_message(user_msg)

            # Call the LLM with the current context
            response = await self.session.llm(self.session.chat_context)
            print(f"[ask_openai] Got response type: {type(response)}")

            # If response is a string, return it directly
            if isinstance(response, str):
                print(f"[ask_openai] Response: {response}")
                self.session.chat_context.add_message(
                    ChatMessage(role="assistant", content=[response]))
                return response

            # If response is an object, try to extract content
            if hasattr(response, 'content'):
                print(f"[ask_openai] Response content: {response.content}")
                self.session.chat_context.add_message(
                    ChatMessage(role="assistant", content=[response.content]))
                return response.content

            print(f"[ask_openai] Unknown response format: {response}")
            return str(response)

        except Exception as e:
            print(f"[ask_openai] Error: {str(e)}")
            print(f"[ask_openai] Error type: {type(e)}")
            import traceback
            print(f"[ask_openai] Traceback: {traceback.format_exc()}")
            return None


async def entrypoint(ctx: agents.JobContext):
    print("[entrypoint] Entrypoint called")
    await ctx.connect()

    # Initialize the session with all required providers
    session = AgentSession(
        # Deepgram: Converts user's speech to text
        stt=deepgram.STT(
            model="nova-3",
            language="multi"
        ),

        # OpenAI: Generates intelligent responses
        llm=openai.LLM(
            model="gpt-4o-mini"
        ),

        # Cartesia: Converts text responses to natural-sounding speech
        tts=cartesia.TTS(),

        # Voice Activity Detection
        vad=silero.VAD.load(),

        # Turn Detection for natural conversation flow
        turn_detection=MultilingualModel(),
    )

    # Create agent instance
    agent = SalonReceptionistAgent()

    # Initialize agent
    await agent.initialize()

    # Start the session with noise cancellation for better audio quality
    await session.start(
        room=ctx.room,
        agent=agent,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    # Initial greeting
    await session.generate_reply(
        instructions="""Greet the caller warmly and introduce yourself as the salon's AI receptionist. 
        Ask how you can help them today, mentioning that you can assist with appointments, 
        service information, and general inquiries."""
    )

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
