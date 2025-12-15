# Consilium

Multi-agent medieval battle wargaming engine.

## Setup

1. Copy `.env.example` to `.env` and configure API keys
2. Install dependencies: `pip install -e .`
3. Run the server: `uvicorn backend.main:app --reload`

## Architecture

Consilium uses a multi-expert deliberation system where:

- **Consilium Chamber**: Domain experts contribute structured analysis
- **Red Team Chamber**: Adversarial experts challenge assumptions
- **Moderator**: Synthesizes contributions, applies deltas, certifies state

The system maintains a **ScenarioSheet** as the single source of truth. Experts propose delta changes; only the Moderator writes.

## API Endpoints

- `GET /health` - Health check
- `GET /api/config` - Available configuration options
- `POST /api/scenario` - Create new scenario
- `POST /api/scenario/{id}/answers` - Submit interrogation answers
- `GET /api/deliberate/{id}` - SSE stream of deliberation
- `GET /api/output/{id}` - Get final scenario output
