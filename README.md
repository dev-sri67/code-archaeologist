# Code Archaeologist

AI-powered codebase exploration and visualization tool. Analyze GitHub repositories, visualize code architecture, and chat with your code using natural language.

![Code Archaeologist](https://img.shields.io/badge/Code%20Archaeologist-AI%20Powered-blue)

## Features

- 🔍 **Repository Analysis** - Clone and analyze any GitHub repository
- 📊 **Interactive Graphs** - Visualize code architecture with React Flow
- 💬 **AI Chat** - Ask questions about your codebase in natural language (RAG-powered)
- 📁 **File Explorer** - Browse files with AI-generated summaries
- 🧠 **Smart Insights** - Automatic function/class detection with LLM explanations

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   React     │────▶│  FastAPI    │────▶│   SQLite    │
│  Frontend   │     │   Backend   │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
                        │      │
                 ┌──────┘      └──────┐
                 ▼                    ▼
          ┌─────────────┐     ┌─────────────┐
          │   Ollama     │     │  Sentence   │
          │   (LLM)     │     │ Transformers│
          └─────────────┘     └─────────────┘
```

## Quick Start

### Prerequisites: Ollama

This project uses [Ollama](https://ollama.com) for LLM-powered code analysis. Install it first:

1. **Download and install Ollama** from https://ollama.com/download
2. **Pull the default model:**
   ```bash
   ollama pull deepseek-coder-v2:16b
   ```
3. **Verify Ollama is running:**
   ```bash
   curl http://localhost:11434/v1/models
   ```

> **Note:** You can use any Ollama model by changing `OPENAI_MODEL` in your `.env` file.
> Smaller models like `deepseek-coder-v2:lite` or `codellama:7b` work on machines with less RAM.

### Using Docker (Recommended)

```bash
cd code-archaeologist

# (Optional) Set a GitHub token for private repos
export GITHUB_TOKEN=your_token_here

# Start all services (includes Ollama, backend, frontend)
docker compose up --build

# The first run will download the Ollama model inside the container.
# Pull the model manually if needed:
docker exec codearch-ollama ollama pull deepseek-coder-v2:16b

# Frontend: http://localhost:3000
# API:      http://localhost:8000
# API docs: http://localhost:8000/docs
```

### Local Development

**Requirements:**
- Python 3.11+
- Node.js 18+
- Ollama running locally (see Prerequisites above)

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate          # Linux/Mac
# venv\Scripts\activate           # Windows

pip install -r requirements.txt

# Create .env file (defaults work out of the box with Ollama)
cp .env.example .env

# Start server (tables auto-created on startup)
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Using OpenAI Instead of Ollama

To use OpenAI's API instead of Ollama, update your `backend/.env`:

```env
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
```

Any OpenAI-compatible API (OpenRouter, Together AI, etc.) can be used by setting the appropriate `OPENAI_BASE_URL` and `OPENAI_API_KEY`.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `sqlite:///./codearch.db` |
| `OPENAI_API_KEY` | API key (`"ollama"` for Ollama) | `ollama` |
| `OPENAI_BASE_URL` | LLM API base URL | `http://localhost:11434/v1` |
| `OPENAI_MODEL` | LLM model name | `deepseek-coder-v2:16b` |
| `OPENAI_TEMPERATURE` | LLM temperature | `0.3` |
| `EMBEDDING_MODEL` | Sentence-transformers model | `all-MiniLM-L6-v2` |
| `VECTOR_DB_DIR` | Vector store path | `./vector_db` |
| `GITHUB_TOKEN` | GitHub token (optional, for private repos) | - |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/repos/analyze` | Start repo analysis |
| `GET` | `/api/repos/{id}/status` | Check analysis progress |
| `GET` | `/api/repos/{id}/graph` | Get visualization data |
| `POST` | `/api/chat/query` | RAG chat query |
| `GET` | `/api/files/{id}/explain` | AI file explanation |

Full interactive API docs available at `/docs` when the backend is running.

## Tech Stack

**Backend:**
- FastAPI + Uvicorn - Async Python API
- SQLAlchemy + aiosqlite - Async SQLite database
- sentence-transformers - Local embeddings (all-MiniLM-L6-v2)
- Ollama (via OpenAI-compatible client) - LLM code analysis
- Tree-sitter - Code parsing (Python & JavaScript)

**Frontend:**
- React 18 + Vite
- React Flow (@xyflow/react) - Graph visualization
- Tailwind CSS - Styling
- Vitest - Testing

## License

MIT