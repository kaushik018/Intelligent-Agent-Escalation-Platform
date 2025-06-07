## Intelligent-Agent-Escalation-Platform

A human-in-the-loop AI receptionist solution designed for salons, managing customer calls, escalating complex issues to human supervisors, and continuously improving its internal knowledge base.

**Key Features**

- AI-driven call management with natural, conversational interactions
- Tailored, salon-specific professional responses
- Appointment booking and schedule management
- Detailed service and pricing information
- Staff availability and expertise lookup
- Seamless escalation to human supervisors when necessary
- Real-time tracking and management of customer requests
- Adaptive knowledge base with ongoing learning and updates

**Technology Stack**

- **Backend:** Python with FastAPI
- **Frontend:** React
- **Voice Processing:** LiveKit
- **AI Components:**
  - Deepgram: Converts spoken input to text
  - OpenAI: Generates context-aware, intelligent replies
  - Cartesia: Transforms text responses into lifelike speech
- **Knowledge Base:** Cartesia
- **Database:** Firebase
- **Real-time Communication:** WebSocket

**Project Structure**

```
smart-agent-escalation-suite/
├── backend/                 # FastAPI backend services
│   ├── agent.py            # LiveKit voice agent logic
│   └── requirements.txt    # Python dependencies
├── frontend/               # React user interface
├── config/                 # Configuration files
└── docs/                   # Documentation resources
```

**Setup Guide**

*Prerequisites*

- Python 3.8 or newer
- Node.js 16 or newer
- Firebase account
- API credentials for:
  - OpenAI
  - Deepgram
  - Cartesia
  - LiveKit

*Installation Steps*

1. Clone the repository

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   # or
   .venv\Scripts\activate     # Windows
   ```

3. Install backend dependencies:

   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. Install frontend dependencies:

   ```bash
   cd frontend
   npm install
   ```

5. Configure environment variables:

   ```bash
   cp .env.example .env
   # Edit .env with your credentials:
   # - LIVEKIT_URL
   # - LIVEKIT_API_KEY
   # - LIVEKIT_API_SECRET
   # - OPENAI_API_KEY
   # - DEEPGRAM_API_KEY
   ```

*Running the System*

- Launch the backend:

  ```bash
  cd backend
  uvicorn main:app --reload
  ```

- Start the frontend:

  ```bash
  cd frontend
  npm start
  ```

- Run the LiveKit agent:

  ```bash
  cd backend
  python agent.py
  ```

**System Overview**

| Component                 | Responsibilities                                                                 |
|---------------------------|----------------------------------------------------------------------------------|
| AI Receptionist Agent     | Handles calls, processes queries, manages speech-to-text and text-to-speech,     |
|                           | escalates to supervisors, and updates the knowledge base                         |
| Supervisor Dashboard      | Displays and manages escalated requests, enables supervisor responses,           |
|                           | monitors performance, and allows knowledge base updates                          |
| Knowledge Base System     | Stores Q&A pairs, provides context for AI, and evolves based on supervisor input |

This suite empowers salons with an intelligent, responsive, and ever-improving receptionist platform that balances automation with human oversight.
