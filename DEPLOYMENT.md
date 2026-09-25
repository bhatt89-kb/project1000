# 🚀 Deployment Guide

This guide covers deploying the Legal Document Assistant to various platforms.

## Quick Deploy Options

### 🎯 Render.com (Recommended)

**One-click deployment with the "Deploy to Render" button in README.md**

#### Manual Deployment:

1. Fork/clone the repository to your GitHub account
2. Sign up at [render.com](https://render.com)
3. Click "New +" → "Web Service"
4. Connect your GitHub repository
5. Render auto-detects the `render.yaml` configuration
6. Click "Create Web Service"
7. Wait 3-5 minutes for deployment
8. Your app will be live at `https://your-app-name.onrender.com`

**Configuration:**
- Runtime: Docker (uses multi-stage Dockerfile)
- Region: Oregon (or choose closest to you)
- Plan: Free tier (sufficient for demos)
- Auto-deploy: Enabled (deploys on git push)

**Environment Variables** (optional):
```bash
FLASK_ENV=production
MAX_DOCUMENTS=50
PYTHONUNBUFFERED=1
```

---

### 🐳 Fly.io

**Global edge deployment with 3 free VMs**

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login
flyctl auth login

# Deploy (uses fly.toml config)
flyctl launch

# Your app is live at https://your-app-name.fly.dev
```

**Configuration:**
- Uses included `fly.toml`
- Auto-scaling: 0-1 machines (free tier)
- Region: Seattle (sea) - customize in fly.toml
- Memory: 256MB (sufficient for document processing)

---

### 🚂 Railway.app

**Auto-deploys from GitHub with zero config**

1. Go to [railway.app](https://railway.app)
2. Click "Start a New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repository
5. Railway auto-detects Dockerfile
6. Click "Deploy"
7. Your app is live at `https://your-app.up.railway.app`

**Configuration:**
- Runtime: Docker (automatic)
- Free tier: $5/month credit
- Custom domains: Supported

---

### 🐙 Vercel

**Serverless deployment (experimental)**

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Your app is live at https://your-app.vercel.app
```

**Note:** Uses `vercel.json` configuration. Vercel has 50MB Lambda limit, which may be tight for PDF processing. Consider Render or Fly.io for production.

---

### 🟪 Heroku

**Classic platform with buildpack support**

```bash
# Install Heroku CLI
curl https://cli-assets.heroku.com/install.sh | sh

# Login
heroku login

# Create app
heroku create your-app-name

# Deploy
git push heroku main

# Open app
heroku open
```

**Configuration:**
- Uses included `Procfile`
- Buildpack: Python (automatic)
- Dynos: Free tier (1 web dyno)

**Procfile:**
```
web: gunicorn --bind 0.0.0.0:$PORT --workers 4 --timeout 120 app:app
```

---

### 🐳 Docker (Self-Hosted)

**Deploy anywhere with Docker**

```bash
# Build image
docker build -t legal-doc-assistant .

# Run container
docker run -d -p 8000:8000 --name legal-assistant legal-doc-assistant

# Access at http://localhost:8000
```

**Docker Compose:**
```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - FLASK_ENV=production
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## Platform Comparison

| Platform | Free Tier | Deploy Speed | Best For |
|----------|-----------|--------------|----------|
| **Render** | ✅ 750hrs/mo | 3-5 min | Production demos |
| **Fly.io** | ✅ 3 VMs | 1-2 min | Global edge apps |
| **Railway** | ✅ $5/mo credit | 2-3 min | Rapid prototyping |
| **Vercel** | ✅ Unlimited | <1 min | Serverless (experimental) |
| **Heroku** | ✅ 1 dyno | 5-7 min | Classic deployments |
| **Docker** | N/A | Varies | Self-hosted/VPS |

---

## Post-Deployment Checklist

### 1. Verify Health Check
```bash
curl https://your-app-name.onrender.com/
# Should return HTML with "Legal Document Assistant"
```

### 2. Test Document Upload
- Upload a sample PDF/TXT file
- Verify analysis results appear
- Check risk assessment and entities

### 3. Test Q&A Feature
- Ask a question about the document
- Verify relevant passages are returned

### 4. Test Comparison
- Upload a second document
- Compare with the first
- Verify differences are highlighted

### 5. Monitor Logs
```bash
# Render
render logs --service your-service-name

# Fly.io
flyctl logs

# Railway
railway logs

# Heroku
heroku logs --tail
```

### 6. Set Up Custom Domain (Optional)
Most platforms support custom domains on free tier:
- Render: Settings → Custom Domain
- Fly.io: `flyctl certs add yourdomain.com`
- Railway: Settings → Domains
- Vercel: Automatic with domain verification

---

## Troubleshooting

### Build Failures

**Issue:** Docker build times out
```bash
# Solution: Use Python runtime instead of Docker in render.yaml
# Uncomment the Python config, comment the Docker config
```

**Issue:** Missing dependencies
```bash
# Ensure all dependencies are in requirements.txt
pip freeze > requirements.txt
```

### Runtime Errors

**Issue:** Port binding errors
```bash
# Ensure app.py uses environment PORT variable
port = int(os.environ.get("PORT", 5000))
app.run(host="0.0.0.0", port=port)
```

**Issue:** Memory limits exceeded
```bash
# Reduce MAX_DOCUMENTS limit or upgrade plan
export MAX_DOCUMENTS=25
```

### Performance Issues

**Issue:** Slow PDF processing
```bash
# Enable gunicorn threads
--workers 2 --threads 4
```

**Issue:** Rate limiting too strict
```bash
# Adjust in app.py
limiter = Limiter(
    default_limits=["500 per hour", "100 per minute"]
)
```

---

## Security Recommendations

### Production Checklist
- [ ] Enable HTTPS (automatic on most platforms)
- [ ] Set `FLASK_ENV=production`
- [ ] Configure rate limiting appropriately
- [ ] Review security headers in app.py
- [ ] Enable auto-deploy from main branch only
- [ ] Set up monitoring/alerts
- [ ] Regular dependency updates (`pip list --outdated`)

### Environment Variables
Never commit secrets to git. Use platform environment variables:
```bash
# Render
render env set SECRET_KEY=your-secret-key

# Fly.io
flyctl secrets set SECRET_KEY=your-secret-key

# Railway
railway variables set SECRET_KEY=your-secret-key
```

---

## Monitoring & Maintenance

### Health Monitoring
All platforms provide built-in monitoring:
- Render: Metrics tab
- Fly.io: `flyctl status`
- Railway: Metrics dashboard
- Heroku: Metrics tab

### Log Aggregation
Consider integrating:
- Papertrail (free tier available)
- Logtail
- Better Stack

### Uptime Monitoring
Free options:
- UptimeRobot (50 monitors free)
- Freshping
- StatusCake

---

## Cost Optimization

### Free Tier Limits
- **Render:** 750 hours/month (sleep after 15min inactivity)
- **Fly.io:** 3 shared VMs (auto-stop when idle)
- **Railway:** $5/month credit (~160 hours)
- **Vercel:** Unlimited serverless invocations
- **Heroku:** 1 free dyno (550 hours/month)

### Staying Within Free Tier
1. Enable auto-sleep on inactivity
2. Use Docker for smaller image size
3. Limit document storage (MAX_DOCUMENTS=50)
4. Monitor usage dashboards
5. Set up billing alerts

---

## Getting Help

- **Documentation:** See README.md for architecture details
- **Issues:** Open an issue on GitHub
- **Platform Support:**
  - Render: https://render.com/docs
  - Fly.io: https://fly.io/docs
  - Railway: https://docs.railway.app
  - Vercel: https://vercel.com/docs

---

## Next Steps

1. Deploy to your preferred platform
2. Update README.md with your live demo URL
3. Test all features in production
4. Share with users! 🎉

**Happy Deploying! 🚀**
