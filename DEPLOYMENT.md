# AI Lecturer Deployment Guide

## Overview
This guide will help you deploy:
- **Backend**: Railway (Python FastAPI server)
- **Frontend**: Vercel (Next.js app)
- **Custom Domain**: Your Namecheap domain

## Prerequisites
- [Railway account](https://railway.app) (free tier available)
- [Vercel account](https://vercel.com) (free tier available)
- Namecheap domain
- Google Cloud credentials (Gemini API key + TTS service account JSON)

---

## Part 1: Deploy Backend to Railway

### Step 1: Create Railway Project
1. Go to [Railway](https://railway.app) and log in
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Connect your GitHub account and select your repository
5. Railway will auto-detect the Python app

### Step 2: Configure Environment Variables
In Railway project settings, add these environment variables:

```bash
# Gemini API Key
GEMINI_API_KEY=AIzaSyBytri0Lcpg-kw8gukPcyuPUz0R7adhl-c

# Google Cloud TTS Credentials (see note below)
GOOGLE_TTS_CREDENTIALS_PATH=/app/credentials.json
```

**Important: Google Cloud TTS Credentials**
You cannot upload files directly to Railway, so you need to convert your JSON credentials to an environment variable:

1. Copy contents of your `ai-lecture-482508-82c1952b6b6a.json` file
2. In Railway, add a new variable: `GOOGLE_APPLICATION_CREDENTIALS_JSON`
3. Paste the entire JSON contents as the value

Then update `backend/app/services/tts/google_tts_provider.py` to load credentials from environment:
```python
import json
import os
from google.oauth2 import service_account

# In __init__ method:
if credentials_path:
    credentials = service_account.Credentials.from_service_account_file(credentials_path)
elif os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON'):
    # Load from environment variable
    creds_dict = json.loads(os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON'))
    credentials = service_account.Credentials.from_service_account_info(creds_dict)
else:
    credentials = None
```

### Step 3: Deploy
1. Railway will automatically deploy when you push to your main branch
2. Wait for deployment to complete (~2-3 minutes)
3. Copy your Railway URL (e.g., `https://your-app.railway.app`)

### Step 4: Add Custom Domain (Optional)
1. In Railway project settings, go to **"Settings" → "Domains"**
2. Click **"Add Domain"**
3. Enter your subdomain (e.g., `api.yourdomain.com`)
4. Railway will provide DNS records - save these for later

---

## Part 2: Deploy Frontend to Vercel

### Step 1: Create Vercel Project
1. Go to [Vercel](https://vercel.com) and log in
2. Click **"Add New Project"**
3. Import your GitHub repository
4. Vercel will auto-detect Next.js

### Step 2: Configure Build Settings
- **Framework Preset**: Next.js
- **Root Directory**: `frontend`
- **Build Command**: `npm run build`
- **Output Directory**: `.next` (auto-detected)

### Step 3: Add Environment Variable
Add this environment variable in Vercel project settings:

```bash
NEXT_PUBLIC_API_URL=https://your-app.railway.app
```

Or if using custom domain:
```bash
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

### Step 4: Deploy
1. Click **"Deploy"**
2. Wait for deployment (~1-2 minutes)
3. Vercel will give you a URL (e.g., `https://your-app.vercel.app`)

### Step 5: Add Custom Domain
1. In Vercel project settings, go to **"Settings" → "Domains"**
2. Add your domain (e.g., `yourdomain.com` or `www.yourdomain.com`)
3. Vercel will provide DNS records

---

## Part 3: Configure Namecheap DNS

### For Backend (Railway)
If you set up `api.yourdomain.com`:

1. Log in to Namecheap
2. Go to **Domain List** → Your domain → **Manage**
3. Go to **Advanced DNS** tab
4. Add the DNS records Railway provided:
   - Type: `CNAME`
   - Host: `api`
   - Value: `your-app.railway.app`
   - TTL: Automatic

### For Frontend (Vercel)
For `yourdomain.com`:

1. In Namecheap Advanced DNS, add:
   - Type: `A`
   - Host: `@`
   - Value: `76.76.21.21` (Vercel's IP)
   - TTL: Automatic

For `www.yourdomain.com`:
   - Type: `CNAME`
   - Host: `www`
   - Value: `cname.vercel-dns.com`
   - TTL: Automatic

**Note**: DNS propagation can take 1-48 hours, but usually works within 15 minutes.

---

## Part 4: Update CORS Settings

Once your frontend is deployed, update the backend CORS settings in `backend/app/config.py`:

```python
# In Settings class
frontend_url: str = "https://yourdomain.com"
```

Or set it as an environment variable in Railway:
```bash
FRONTEND_URL=https://yourdomain.com
```

---

## Part 5: Test Deployment

1. Visit your frontend URL (e.g., `https://yourdomain.com`)
2. Upload a small PDF (2-3 slides) to test
3. Check Railway logs if anything fails:
   - Go to Railway project → **"Deployments"** → Click latest deployment → **"View Logs"**

---

## Cost Management

### Set Spending Limits
1. **Google Cloud Console**:
   - Go to [Billing](https://console.cloud.google.com/billing)
   - Set budget alerts (e.g., $10/month)
   - Enable budget notifications

2. **Railway**:
   - Free tier: $5 credit/month
   - After that: ~$5-10/month for basic usage
   - Set up billing alerts

3. **Vercel**:
   - Free tier: Unlimited for personal projects
   - No credit card required

### Current Protections
- ✅ Rate limiting: 5 lectures per 24 hours per IP
- ✅ Slide limit: Maximum 150 slides per presentation
- ✅ Session persistence: Presentations saved to disk

---

## Monitoring

### Railway Logs
View real-time logs in Railway dashboard to monitor:
- API requests
- Error messages
- TTS generation status

### Vercel Analytics
Enable Vercel Analytics (free) to track:
- Page views
- User engagement
- Performance metrics

---

## Troubleshooting

### Frontend can't reach backend
- Check `NEXT_PUBLIC_API_URL` is set correctly in Vercel
- Verify CORS settings include your frontend URL
- Check Railway service is running

### TTS not working
- Verify `GOOGLE_APPLICATION_CREDENTIALS_JSON` is set in Railway
- Check Google Cloud TTS API is enabled
- Verify credentials have proper permissions

### Rate limiting too strict
- Update `max_requests` in `server.py:81`
- Current: 5 lectures per 24 hours

---

## Security Checklist

- ✅ API keys in environment variables (not in code)
- ✅ `.gitignore` excludes credentials and output files
- ✅ Rate limiting enabled
- ✅ CORS configured for specific domains
- ✅ Slide count limited to 150
- ⬜ Enable 2FA on Railway and Vercel accounts
- ⬜ Set up Google Cloud budget alerts

---

## Next Steps

After deployment:
1. Test with various PDF sizes
2. Monitor Railway logs for errors
3. Set up budget alerts on Google Cloud
4. Share your app with users!

Your app architecture:
```
User → yourdomain.com (Vercel)
     → api.yourdomain.com (Railway)
     → Google Gemini API
     → Google Cloud TTS API
```

---

## Support

- Railway Docs: https://docs.railway.app
- Vercel Docs: https://vercel.com/docs
- Google Cloud TTS: https://cloud.google.com/text-to-speech/docs
