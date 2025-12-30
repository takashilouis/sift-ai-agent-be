# Railway Deployment Guide

## Quick Deploy

This backend is configured for Railway deployment with the following files:
- `Procfile` - Tells Railway how to start the app
- `railway.json` - Railway-specific configuration
- `nixpacks.toml` - Build configuration for dependencies

## Prerequisites

1. **Railway Account** - Sign up at [railway.app](https://railway.app)
2. **GitHub Repository** - Push your code to GitHub

## Deployment Steps

### 1. Create New Project in Railway

1. Go to [railway.app](https://railway.app)
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repository
5. **Important**: Set the root directory to `backend` if deploying from a monorepo

### 2. Add PostgreSQL Database

1. In your Railway project, click "New"
2. Select "Database" → "PostgreSQL"
3. Railway will automatically create a `DATABASE_URL` environment variable

### 3. Set Environment Variables

In Railway dashboard, add these variables:

```bash
# Required
GOOGLE_API_KEY=your_gemini_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here

# Optional (Railway auto-provides DATABASE_URL)
ENVIRONMENT=production
DEBUG=false
```

### 4. Deploy

Railway will automatically:
1. Install Python 3.11
2. Install dependencies from `requirements.txt`
3. Install Playwright with Chromium browser
4. Start the FastAPI server

## Memory Requirements

⚠️ **Important**: Playwright requires significant memory.

- **Minimum**: $5/month plan (512MB RAM)
- **Recommended**: $10/month plan (1GB RAM) for stability

## Verify Deployment

After deployment, your API will be available at:
```
https://your-app-name.railway.app
```

Test endpoints:
- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /docs` - API documentation (Swagger UI)

## Troubleshooting

### Build Fails with "pip: command not found"
✅ Fixed in `nixpacks.toml` - uses `python3 -m pip`

### Playwright Installation Fails
✅ Fixed in `nixpacks.toml` - uses `--with-deps` flag

### Out of Memory Errors
- Upgrade to 1GB RAM plan ($10/month)
- Playwright + Chromium needs ~300-400MB

### Database Connection Issues
- Check that `DATABASE_URL` is set (auto-provided by Railway PostgreSQL)
- Verify your database is running in the same project

## Connect Frontend to Backend

After deployment, update your frontend environment variables:

```bash
# In your frontend .env.local or Vercel environment variables
NEXT_PUBLIC_API_URL=https://your-backend.railway.app
```

## Cost Estimate

- Backend (512MB RAM): $5/month
- PostgreSQL (1GB storage): $5/month
- **Total**: ~$10/month

## Support

For Railway-specific issues, check:
- [Railway Docs](https://docs.railway.app)
- [Railway Discord](https://discord.gg/railway)
