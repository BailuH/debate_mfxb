# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Digital Courtroom** is a full-stack courtroom debate simulation system built with LangGraph and FastAPI. The system simulates court cases with three AI-powered or human-controlled agents (plaintiff, defendant, judge) through a structured debate flow managed by a state graph.

**Key Features:**
- REST API for session management and case configuration
- WebSocket real-time communication for live debate updates
- Human-in-the-loop (HITL) support allowing users to participate as any courtroom role
- Async architecture for high concurrency
- Memory-based state persistence (easily extendable to database)

## Architecture

### Core Components

```
src/
├── agent.py           # Agent implementations (Judge, Plaintiff, Defendant)
├── state.py           # CourtState TypedDict definition
├── workflow.py        # LangGraph StateGraph definition with MemorySaver
├── prompt.py          # Role-specific prompts for agents
├── llmconfig.py       # LLM model configuration
├── api/
│   ├── main.py        # FastAPI application entry
│   ├── routes/
│   │   ├── sessions.py    # REST API endpoints
│   │   └── websocket.py   # WebSocket endpoint
│   └── websocket/
│       └── manager.py     # WebSocket connection management
├── services/
│   └── court_service.py   # Core business logic and session management
└── schemas/
    ├── session.py     # Pydantic models for API
    └── message.py     # Message models
```

### State Management

**CourtState** (`src/state.py`) manages the entire simulation:
- `case_info`: Basic case information
- `case_evidence`: List of evidence with speaker attribution
- `phase`: Current phase ("开庭阶段", "交叉质证", "休庭小结")
- `messages`: Conversation history (ChatMessage/HumanMessage)
- `speaker`: Current speaking role
- `human_role`: Which role is human-controlled (if any)
- `rounds`: Debate round counter

### Service Layer

**CourtService** (`src/services/court_service.py`) encapsulates all LangGraph logic:
- Manages active sessions in memory
- Handles session lifecycle (create, retrieve, cleanup)
- Wraps LangGraph's async graph invocation
- Manages human input flow via Command(resume=...)
- Auto-cleanup of expired sessions (3 hours) - uses lazy initialization to avoid event loop issues at import time

### WebSocket Communication

**ConnectionManager** (`src/api/websocket/manager.py`) handles real-time updates:
- Broadcasts debate updates to all connected clients
- Sends `human_input_required` events when HITL is triggered
- Supports multiple observers watching the same session
- Automatic cleanup of disconnected clients

**Event Protocol:**

Server → Client:
- `debate_update`: New message, speaker/phase changes
- `human_input_required`: HITL prompt for user input
- `debate_ended`: Session conclusion
- `status_update`: Full state update

Client → Server:
- `human_input`: Submit human response
- `next_step`: Request AI to continue (pure AI mode)
- `ping`: Heartbeat

## Development Commands

### Setup
```bash
# Install dependencies
uv sync

# Or with pip
pip install -r requirements.txt
```

### Environment Configuration
Create `.env` file:
```
# DeepSeek API (configured as OpenAI-compatible)
OPENAI_API_KEY=your_deepseek_api_key
OPENAI_API_BASE=https://api.deepseek.com/v1
```

### Run Server
```bash
# Start FastAPI server with auto-reload
python main.py

# Server runs at http://localhost:8000
# API docs: http://localhost:8000/docs
# Demo UI: http://localhost:8000/examples/index.html
```

### Test the System
```bash
# Run automated system test
python test_system.py
```

## API Reference

### REST Endpoints

#### Create Session
```http
POST /api/sessions
{
  "case_info": "Case description...",
  "case_evidence": [
    {"speaker": "原告律师", "content": "Evidence details..."}
  ],
  "human_role": "被告律师"  // optional: null for pure AI
}
```

#### Get Session Status
```http
GET /api/sessions/{session_id}
```

#### End Session
```http
DELETE /api/sessions/{session_id}
```

### WebSocket Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/{session_id}?role=被告律师');

ws.onmessage = (event) => {
  const { event, data } = JSON.parse(event.data);

  if (event === 'debate_update') {
    console.log('New message:', data.new_message);
  } else if (event === 'human_input_required') {
    // Show input dialog for user
    const input = prompt(data.prompt);
    ws.send(JSON.stringify({
      event: 'human_input',
      data: { content: input, role: '被告律师' }
    }));
  }
};
```

## Agent System

### Agent Roles

**Judge** (`src/agent.py:13-95`)
- `debate_start()`: Initialize court session
- `judge_summary()`: Summarize arguments and identify key issues
- `judge_should_continue()`: Decide whether to continue or end debate (max 3 rounds)
- `judge_verdict()`: Deliver final verdict

**Plaintiff** (`src/agent.py:97-144`)
- `plaintiff_statement()`: Opening statement
- `plaintiff_argue()`: Cross-examination arguments

**Defendant** (`src/agent.py:147-192`)
- `defendant_reply()`: Response to plaintiff's claims
- `defendant_argue()`: Cross-examination defense

### LLM Models

Configured in `src/llmconfig.py`:
- **DeepSeek-V3**: Plaintiff and defendant (argument generation)
- **DeepSeek-R1**: Judge (analytical tasks, summaries, verdicts)

### Prompts

Role-specific prompts in `src/prompt.py`:
- `STATEMENT_PROMPT`: Plaintiff opening statement guide
- `ARGUE_PROMPT_PL/DE`: Cross-examination strategies
- `DEMURRER_PROMPT`: Defendant defense framework
- `SUMMARY/VERDICT`: Judge instructions

## Human-in-the-Loop Flow

1. **Interrupt Triggered**: When `human_role` matches current speaker, agent calls `interrupt(prompt)`

2. **WebSocket Notification**: Backend catches interruption and sends `human_input_required` event

3. **User Input**: Frontend displays dialog, user submits response

4. **Workflow Continuation**: Backend receives input via WebSocket, uses `Command(resume=input)` to continue graph execution

5. **Debate Resumes**: LangGraph continues with human input as the agent's response

## Frontend Integration

### Example Integration
See `examples/frontend_integration.js` for a complete JavaScript client library.

### Key Integration Points

1. **Create Session**: POST to `/api/sessions` with case info
2. **Connect WebSocket**: Use session_id to establish real-time connection
3. **Handle Events**: Implement handlers for `debate_update`, `human_input_required`, `debate_ended`
4. **Submit Input**: Send `human_input` event when user provides response
5. **AI Mode**: Send `next_step` event to advance without human input

### Demo UI
A complete demo interface is available at `examples/index.html` with:
- Case configuration form
- Real-time message display
- Human input dialog
- Connection status and controls

## Key Implementation Details

### Async Graph Invocation
The service layer wraps LangGraph's synchronous `invoke()` with `asyncio.to_thread()` for async support:

```python
self.state = await asyncio.to_thread(self.app.invoke, input_data, self.config)
```

### Memory-Based Persistence
Uses LangGraph's `MemorySaver` for lightweight state persistence:

```python
from langgraph.checkpoint.memory import MemorySaver
memory = MemorySaver()
app = graph.compile(checkpointer=memory)
```

### Thread Safety
CourtSession uses `asyncio.Lock()` to prevent race conditions during state updates.

### Automatic Cleanup
Background task runs every hour to clean up sessions inactive for 3+ hours.

## Common Development Tasks

### Add New API Endpoint
1. Create Pydantic models in `src/schemas/`
2. Add route function in `src/api/routes/`
3. Implement business logic in `CourtService`
4. Add router to `src/api/main.py`

### Modify Agent Behavior
1. Update prompts in `src/prompt.py`
2. Modify agent methods in `src/agent.py`
3. Adjust graph flow in `src/workflow.py` if needed

### Add New WebSocket Event
1. Add event handler in `src/api/routes/websocket.py`
2. Update ConnectionManager broadcast methods
3. Update frontend event handling

## Testing

### Manual Testing
1. Start server: `python main.py`
2. Open demo: `http://localhost:8000/examples/index.html`
3. Create session with test case
4. Experiment with different human roles
5. Monitor WebSocket messages in browser console

### API Testing
Use the interactive docs at `http://localhost:8000/docs` for testing REST endpoints.

## Performance Considerations

- **Memory Usage**: Sessions stored in memory; scale with session volume
- **WebSocket Connections**: Each connection is lightweight; tested with 100+ concurrent
- **LLM Calls**: Each graph step makes 1-2 LLM calls; latency depends on model
- **Async Design**: All I/O operations are async for high concurrency

## Future Enhancements

The architecture supports easy extension:
- Replace `MemorySaver` with database-backed checkpointer
- Add user authentication layer
- Implement Redis for WebSocket scaling
- Add logging and monitoring
- Create case template system
- Implement scoring and analytics
