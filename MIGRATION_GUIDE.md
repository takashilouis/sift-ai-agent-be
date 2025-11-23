# 🔄 Migration Guide: Mock → Real LLM System

## What Changed

Your backend has been upgraded from a mock keyword-based system to a **real LLM-powered agentic platform**.

### Before (v1.0 - Mock System)
```python
# ❌ OLD: Keyword matching
if "summary" in prompt_lower:
    return "Canned summary text..."

# ❌ OLD: Fixed pipeline
url_detector → search → scrape → summarize → sentiment → compare
```

### After (v2.0 - Real LLM System)
```python
# ✅ NEW: LLM Planner
plan = await gemini.create_plan(query)

# ✅ NEW: Dynamic execution
for task in plan.tasks:
    execute_task(task)
```

## Breaking Changes

### 1. API Response Structure

**Old Response:**
```json
{
  "query": "...",
  "url": "...",
  "product_data": {...},
  "summary": "...",
  "sentiment": {...},
  "comparison": {...}
}
```

**New Response:**
```json
{
  "query": "...",
  "plan": {
    "intent": "product_research",
    "tasks": [...]
  },
  "task_results": {
    "0": {"search_results": [...]},
    "1": {"product_data": {...}},
    "2": {"summary": "..."},
    ...
  },
  "final_report": "# Comprehensive markdown report..."
}
```

### 2. Required API Keys

**Old:** No API keys needed (mock data)

**New:** REQUIRED API keys:
- `GEMINI_API_KEY` - For LLM planner and agents
- `TAVILY_API_KEY` - For real web search

See [API_KEYS_SETUP.md](./API_KEYS_SETUP.md) for setup instructions.

### 3. Streaming Format

**Old:** Fixed steps
```json
{"step": "url_detector", "state": {...}}
{"step": "search_agent", "state": {...}}
{"step": "scraper_agent", "state": {...}}
```

**New:** Dynamic steps based on plan
```json
{"step": "planner", "state": {"plan": {...}}}
{"step": "task_executor", "state": {"current_task_index": 0, ...}}
{"step": "task_executor", "state": {"current_task_index": 1, ...}}
{"step": "finalize", "state": {"final_report": "..."}}
```

### 4. Cost Implications

**Old:** Free (mock responses)

**New:** ~$0.02-$0.10 per research query
- Gemini API calls
- Tavily search calls

## Migration Steps

### 1. Update Dependencies

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure API Keys

```bash
# Edit .env file
nano .env

# Add your keys:
GEMINI_API_KEY=your_actual_key_here
TAVILY_API_KEY=your_actual_key_here
```

### 3. Update Frontend (if applicable)

If you have a frontend consuming the API:

**Update response parsing:**
```typescript
// OLD
const { summary, sentiment, comparison } = response;

// NEW
const { plan, task_results, final_report } = response;

// Extract specific results
const summary = task_results["2"]?.summary;
const sentiment = task_results["3"]?.sentiment;
```

**Handle new streaming format:**
```typescript
// Listen for planner output
if (chunk.step === "planner") {
  const plan = chunk.state.plan;
  console.log(`Plan: ${plan.tasks.length} tasks`);
}

// Listen for task execution
if (chunk.step === "task_executor") {
  const taskIndex = chunk.state.current_task_index;
  console.log(`Executing task ${taskIndex}`);
}
```

### 4. Test the System

```bash
# Start server
./run.sh

# In another terminal, test
curl -X POST http://localhost:8000/api/research/sync \
  -H "Content-Type: application/json" \
  -d '{"query": "Apple AirPods 4"}'
```

## Backward Compatibility

The `/api/research/sync` endpoint maintains **partial backward compatibility**:

```json
{
  // New fields
  "plan": {...},
  "task_results": {...},
  "final_report": "...",
  
  // Legacy fields (extracted from task_results)
  "url": "...",
  "product_data": {...},
  "summary": "...",
  "sentiment": {...},
  "comparison": "..."
}
```

This allows existing clients to continue working while you migrate to the new structure.

## Rollback Plan

If you need to rollback to the mock system:

```bash
git checkout <previous-commit>
pip install -r requirements.txt
./run.sh
```

## Feature Comparison

| Feature | Mock System (v1.0) | Real LLM System (v2.0) |
|---------|-------------------|----------------------|
| **Planning** | Fixed pipeline | LLM-generated dynamic plan |
| **Search** | Mock URLs | Real Tavily search |
| **Scraping** | Mock data | Real Playwright + LLM extraction |
| **Summary** | Canned text | Real Gemini LLM |
| **Sentiment** | Mock percentages | Real LLM analysis |
| **Comparison** | Mock alternatives | Real multi-product LLM comparison |
| **Cost** | Free | ~$0.02-$0.10/query |
| **Quality** | Generic | Contextual & accurate |
| **Flexibility** | Fixed flow | Adapts to query |

## New Capabilities

### 1. Intelligent Planning
The LLM analyzes your query and creates an optimal plan:

```
Query: "Compare AirPods 4 vs Galaxy Buds"
→ Plan: search(AirPods) → scrape → search(Galaxy) → scrape → compare
```

### 2. Real Data Extraction
Playwright scrapes actual product pages with LLM-based extraction:
- Works across different e-commerce sites
- Adapts to page structure changes
- Extracts structured data reliably

### 3. Contextual Analysis
All LLM responses are based on actual product data:
- Summaries highlight real features
- Sentiment reflects actual ratings/reviews
- Comparisons use real specifications

### 4. Final Report Synthesis
Comprehensive markdown report combining all analyses:
- Executive summary
- Detailed findings
- Recommendations
- Professional formatting

## Troubleshooting

### Server won't start
```bash
# Check API keys are set
python -c "from app.config import settings; print(settings.GEMINI_API_KEY[:10])"

# Check dependencies
pip list | grep -E "google-generativeai|tavily|playwright"
```

### "API key required" errors
- Verify `.env` file exists in `backend/` directory
- Check keys are not placeholder values
- Restart server after updating `.env`

### Playwright errors
```bash
# Reinstall browsers
playwright install chromium
```

### High costs
- Monitor usage in Gemini/Tavily dashboards
- Adjust `MAX_TOKENS` in `.env` to reduce costs
- Use caching for repeated queries (future feature)

## Support

For issues or questions:
1. Check [API_KEYS_SETUP.md](./API_KEYS_SETUP.md)
2. Review server logs for errors
3. Test with simple queries first

## Next Steps

1. ✅ Set up API keys
2. ✅ Test with sample queries
3. 🔄 Update frontend to use new response format
4. 📊 Monitor costs and usage
5. 🚀 Deploy to production
