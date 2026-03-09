# Contributing to AVATAR

Welcome to the AVATAR project! This guide will help you understand our development process and how to contribute effectively.

## Project Structure

- `backend/`: FastAPI backend application.
  - `app/agents/`: Specialized AI agents (Master, Sync, Analytic, etc.).
  - `app/models/`: SQLAlchemy data models.
  - `app/routers/`: FastAPI route handlers.
  - `app/core/`: Core logic and utilities.
- `frontend/`: Next.js frontend application.
- `docs/`: Technical documentation and architecture overviews.
- `infra/`: Deployment configurations and server scripts.
- `scripts/`: Maintenance and utility scripts.
- `tests/`: Test files and data.

## Workflow

1.  **Branching**: Create a new branch for each feature or bugfix.
2.  **Environment**: Copy `.env.example` to `.env` and fill in necessary API keys (OpenAI, Database URL).
3.  **Development**: Follow the established code style and use specialized agents for AI-related tasks.
4.  **Documentation**: Update `SYSTEM_ARCHITECTURE.md` if you make changes to the system core or agent roles.
5.  **Testing**: Place new tests in the `tests/` directory.

## Core Rules

- **Strict Narrative Scanner**: Always follow the 5-layer narrative rules in `SyncAgent`.
- **UserPortrait First**: All diagnostic data must be aggregated into `UserPortrait` for long-term memory.
- **No Direct Interpretation**: Agents should only extract projection material; interpretation happens in the "Mirror" phase.

---
*Developed by the AVATAR Team | 2026*
