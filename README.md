# E-Commerce Research Agent Backend

A complete FastAPI + LangGraph backend for an agentic e-commerce research platform.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)

```bash
cp .env.example .env
# Edit .env with your API keys (optional - works with mock data without keys)
```

### 3. Run the Server

```bash
chmod +x run.sh
./run.sh
```

Or manually:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Access the API

- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## 📡 API Endpoints

### POST /api/research (Streaming)

Stream research results as the agent processes each step.

```bash
curl -X POST http://localhost:8000/api/research \
  -H "Content-Type: application/json" \
  -d '{"query": "research this product: Apple AirPods 4", "mode": "product-analysis"}'
```

### POST /api/research/sync

Get complete research results synchronously.

```bash
curl -X POST http://localhost:8000/api/research/sync \
  -H "Content-Type: application/json" \
  -d '{"query": "Apple AirPods 4", "mode": "product-analysis"}'
```

## 🧠 Agent Workflow

The LangGraph workflow consists of 6 agent nodes:

1. **URL Detector** - Detects if query contains a URL
2. **Search Agent** - Searches for product URLs if needed
3. **Scraper Agent** - Scrapes product data (stub)
4. **Summarize Agent** - Generates product summary
5. **Sentiment Agent** - Analyzes product sentiment
6. **Compare Agent** - Compares with alternatives

## 📁 Project Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration settings
│   ├── dependencies.py         # Dependency injection
│   ├── routers/
│   │   └── research_router.py  # Research API endpoints
│   ├── agents/
│   │   ├── graph.py            # LangGraph workflow
│   │   ├── llm_router.py       # LLM model routing
│   │   └── nodes/              # Agent nodes
│   ├── schemas/                # Pydantic schemas
│   ├── services/               # External services (stubs)
│   └── utils/                  # Utility functions
├── requirements.txt
└── run.sh
```

## 🔧 Tech Stack

- **FastAPI** - Modern web framework
- **LangGraph** - Agent workflow orchestration
- **Pydantic** - Data validation
- **Uvicorn** - ASGI server
- **httpx** - Async HTTP client
- **Playwright** - Web scraping (stub)

## 📝 Notes

- This is an MVP with stub implementations for scraping and LLM calls
- Works without API keys using mock data
- Add real API keys to `.env` for production use
