# Deployment Guide - Legal Document Assistant

This guide covers deploying your Legal Document Assistant to various hosting platforms.

## 🚀 Quick Deploy Options

### Option 1: Render.com (Recommended - Free Tier Available)

**Why Render?**
- ✅ Free tier available (750 hours/month)
- ✅ Easy one-click deployment from GitHub
- ✅ Automatic HTTPS
- ✅ Simple configuration

**Steps:**

1. **Go to [Render.com](https://render.com)** and sign up

2. **Create New Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository: `https://github.com/bhatt89-kb/project1000`

3. **Configure Service**
   ```
   Name: legal-document-assistant
   Region: Oregon (or closest to you)
   Branch: main
   Runtime: Python 3
   Build Command: pip install -r requirements.txt gunicorn
   Start Command: gunicorn --bind 0.0.0.0:$PORT --workers 4 --timeout 120 app:app
   ```

4. **Select Plan**
   - Choose "Free" plan
   - Note: Free tier sleeps after 15 minutes of inactivity

5. **Deploy**
   - Click "Create Web Service"
   - Wait 2-3 minutes for deployment
   - Your app will be live at: `https://legal-document-assistant.onrender.com`

**OR Use the render.yaml file:**
   - Just push the `render.yaml` file to your repo
   - Render will auto-detect and configure everything!

---

### Option 2: Railway.app (Modern & Developer-Friendly)

**Why Railway?**
- ✅ $5 free credit per month
- ✅ Extremely fast deployments
- ✅ Great developer experience
- ✅ Automatic HTTPS

**Steps:**

1. **Go to [Railway.app](https://railway.app)** and sign up with GitHub

2. **Create New Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose `bhatt89-kb/project1000`

3. **Railway Auto-Detects**
   - Railway will detect the Dockerfile and build automatically
   - No manual configuration needed!

4. **Generate Domain**
   - Go to Settings → Generate Domain
   - Your app will be live at: `https://project1000.up.railway.app`

5. **Environment Variables (Optional)**
   ```
   PORT=8000
   MAX_DOCUMENTS=50
   ```

**Cost:** ~$2-5/month after free credits

---

### Option 3: Fly.io (Global Edge Deployment)

**Why Fly.io?**
- ✅ Free tier (3 shared-cpu VMs + 3GB storage)
- ✅ Deploy to regions worldwide
- ✅ Excellent performance
- ✅ Uses Docker

**Steps:**

1. **Install Fly CLI**
   ```powershell
   # Windows (PowerShell)
   iwr https://fly.io/install.ps1 -useb | iex
   ```

2. **Login and Launch**
   ```bash
   cd d:\final\legallens-lite\legallens-lite
   fly auth login
   fly launch --name legal-doc-assistant
   ```

3. **Follow Prompts**
   - Choose region (closest to you)
   - Don't add PostgreSQL
   - Don't deploy yet (we'll configure first)

4. **Configure fly.toml**
   ```toml
   app = "legal-doc-assistant"
   
   [http_service]
     internal_port = 8000
     force_https = true
     auto_stop_machines = true
     auto_start_machines = true
   
   [[vm]]
     cpu_kind = "shared"
     cpus = 1
     memory_mb = 256
   ```

5. **Deploy**
   ```bash
   fly deploy
   ```

6. **Open App**
   ```bash
   fly open
   ```

**Your app:** `https://legal-doc-assistant.fly.dev`

---

### Option 4: Heroku (Classic Platform)

**Why Heroku?**
- ✅ Well-established platform
- ✅ Simple git-based deployment
- ✅ Eco Dynos available

**Steps:**

1. **Install Heroku CLI**
   - Download from [heroku.com/downloads](https://devcenter.heroku.com/articles/heroku-cli)

2. **Login and Create App**
   ```bash
   cd d:\final\legallens-lite\legallens-lite
   heroku login
   heroku create legal-document-assistant
   ```

3. **Deploy**
   ```bash
   git push heroku main
   ```

4. **Open App**
   ```bash
   heroku open
   ```

**Note:** Heroku ended free tier in November 2022. Eco Dynos cost $5/month.

---

### Option 5: Docker Anywhere

**Use the Dockerfile to deploy anywhere that supports Docker:**

1. **Build Image**
   ```bash
   docker build -t legal-document-assistant .
   ```

2. **Run Locally**
   ```bash
   docker run -p 8000:8000 legal-document-assistant
   ```

3. **Deploy to:**
   - Google Cloud Run
   - AWS ECS/Fargate
   - Azure Container Instances
   - DigitalOcean App Platform
   - Any VPS with Docker

---

## 📋 Deployment Checklist

Before deploying, ensure:

- [x] All code committed to GitHub
- [x] `requirements.txt` includes `gunicorn`
- [x] `.gitignore` excludes sensitive files
- [x] Tests pass (`pytest`)
- [x] Security headers configured
- [x] Error handling in place

## 🔧 Configuration

### Environment Variables

Set these on your hosting platform:

```bash
# Optional - defaults work fine
PORT=8000                    # Port to run on
MAX_DOCUMENTS=50             # Max documents in memory
MAX_UPLOAD_SIZE=5242880      # 5 MB in bytes
```

### Resource Requirements

**Minimum:**
- RAM: 256 MB
- CPU: 0.1 vCPU
- Storage: 100 MB

**Recommended:**
- RAM: 512 MB
- CPU: 0.5 vCPU
- Storage: 500 MB

## 🔒 Security for Production

### 1. HTTPS Only
All recommended platforms provide automatic HTTPS. Ensure it's enabled.

### 2. Rate Limiting
Consider adding Flask-Limiter:

```python
# In app.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["100 per hour", "20 per minute"]
)
```

### 3. CORS (if needed)
Only if you need to access from different domains:

```python
from flask_cors import CORS
CORS(app, origins=["https://yourdomain.com"])
```

## 📊 Monitoring

### Health Check Endpoint

The root `/` endpoint serves as a health check. All platforms can use it.

### Logs

**Render:**
```bash
# View logs in dashboard or:
render logs -t your-service-name
```

**Railway:**
- Real-time logs in dashboard

**Fly.io:**
```bash
fly logs
```

**Heroku:**
```bash
heroku logs --tail
```

## 🚨 Troubleshooting

### App Crashes on Start

**Check:**
1. All dependencies in `requirements.txt`?
2. Correct Python version (3.10+)?
3. Port binding to `0.0.0.0:$PORT`?

**Solution:**
```bash
# View logs
render logs -t your-service-name  # Render
fly logs                          # Fly.io
heroku logs --tail                # Heroku
```

### Timeout Errors

**Increase timeout:**
```bash
# In start command
gunicorn --timeout 120 app:app
```

### Memory Issues

**Reduce document limit:**
```python
# In app.py
MAX_DOCUMENTS = 25  # Instead of 50
```

### Slow First Request

**Cause:** Free tiers sleep after inactivity

**Solution:**
- Upgrade to paid tier
- Use a uptime monitor (e.g., UptimeRobot)
- Accept the cold start delay

## 💰 Cost Comparison

| Platform | Free Tier | Paid Tier | Best For |
|----------|-----------|-----------|----------|
| **Render** | 750 hrs/month | $7/month | Beginners |
| **Railway** | $5 credit/month | Pay-as-you-go | Developers |
| **Fly.io** | 3 VMs free | ~$2-5/month | Performance |
| **Heroku** | None | $5/month | Enterprise |

## 🎯 Recommended Choice

**For this project, I recommend Render.com:**

✅ Easiest setup  
✅ Free tier sufficient  
✅ Auto-deploys from GitHub  
✅ Automatic HTTPS  
✅ Good uptime  

**Steps:**
1. Push code to GitHub ✓ (Already done!)
2. Connect Render to your repo
3. Deploy with `render.yaml` (auto-configured)
4. Done! 🎉

---

## 📞 Support

If you encounter issues:

1. Check platform status pages
2. Review deployment logs
3. Verify all files committed to GitHub
4. Check `SECURITY.md` for production guidelines
5. Test locally with `gunicorn app:app`

## 🔄 Continuous Deployment

All platforms support auto-deploy from GitHub:

**Enable:**
1. Connect GitHub repository
2. Choose branch (main)
3. Enable "Auto-deploy on push"

**Now:** Every git push automatically deploys! 🚀

---

## 📱 Custom Domain (Optional)

Once deployed, add a custom domain:

**Render:**
- Settings → Custom Domain → Add domain

**Railway:**
- Settings → Networking → Custom Domain

**Fly.io:**
```bash
fly certs add yourdomain.com
```

---

**You're ready to deploy!** Choose a platform above and follow the steps. Your Legal Document Assistant will be live in minutes! 🎉
