# Production Deployment Fix Guide

## Problem Identified
Your frontend (Vercel) was trying to call `http://localhost:8000` which doesn't exist in production, causing random request failures.

## Solution Applied

### Code Changes Made:
1. ✅ **Fixed `next.config.js`** - Now only uses rewrites in development
2. ✅ **Backend already supports** `FRONTEND_URL` environment variable

---

## Required Actions (Do These Now!)

### Step 1: Configure Vercel Environment Variables

Go to your Vercel project settings → Environment Variables and add:

```
NEXT_PUBLIC_API_URL=https://your-backend.onrender.com
```

Replace `your-backend.onrender.com` with your actual Render backend URL.

**Important:**
- Make sure it starts with `https://` (not `http://`)
- Don't include `/api/v1` at the end
- Add this for Production, Preview, and Development environments

### Step 2: Configure Render Environment Variables

Go to your Render dashboard → Your service → Environment and add:

```
FRONTEND_URL=https://your-app.vercel.app
```

Replace `your-app.vercel.app` with your actual Vercel frontend URL.

**Also verify these are set:**
```
GEMINI_API_KEY=<your-key>
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-key>
```

### Step 3: Redeploy Both Services

1. **Vercel**:
   - Push this updated code to your git repo
   - Vercel will auto-deploy with new `next.config.js`
   - OR manually trigger redeploy in Vercel dashboard

2. **Render**:
   - Should auto-redeploy when you push
   - OR manually trigger redeploy to pick up new `FRONTEND_URL` variable

---

## Verification

After deploying, test these scenarios:

1. ✅ Upload a presentation - should work consistently
2. ✅ Check processing status - should update reliably
3. ✅ View lecture slides - images should load
4. ✅ Play audio - should work without errors
5. ✅ Open browser DevTools → Network tab - should show requests to `https://your-backend.onrender.com`, NOT `localhost`

---

## Additional Issues Found (Not Urgent)

### Security Issue
Your `.env` file contains API keys committed to the repository:
```
backend/.env
```

**Recommendation:**
- Add `backend/.env` to `.gitignore`
- Remove it from git history
- Rotate your API keys (especially `GEMINI_API_KEY` and AWS credentials)
- Only use environment variables in Render for secrets

### Missing SSE Endpoint
Frontend has code for `subscribeToProgress()` using Server-Sent Events, but backend doesn't implement `/api/v1/stream/{sessionId}`. Currently using polling as workaround (works fine, just less efficient).

---

## Expected Behavior After Fix

- ✅ All requests should succeed consistently
- ✅ No more random failures
- ✅ Dashboard updates should be reliable
- ✅ Slide images and audio should load every time
- ✅ Network tab should show correct backend URL

---

## Troubleshooting

### If requests still fail:

1. **Check CORS errors in browser console:**
   - If you see CORS errors, verify `FRONTEND_URL` is set correctly on Render
   - Make sure it matches your Vercel URL exactly

2. **Check API URL in Network tab:**
   - Open DevTools → Network
   - Click on a failed request
   - Check the URL - should be `https://your-backend.onrender.com/api/v1/...`
   - If it's still `localhost:8000`, the environment variable isn't set correctly

3. **Verify environment variables:**
   - Vercel: Settings → Environment Variables
   - Render: Dashboard → Environment
   - Make sure both are set and services are redeployed

4. **Check Render logs:**
   - Look for CORS-related errors
   - Verify backend is starting correctly
   - Check for any errors during request processing

---

## Summary

**What was wrong:**
- Frontend used `localhost:8000` in production
- Next.js rewrites pointed to localhost
- CORS might not have included your Vercel URL

**What was fixed:**
- `next.config.js` now supports production URLs
- Backend already supports `FRONTEND_URL` env var
- Just need to configure environment variables correctly

**Your action items:**
1. Set `NEXT_PUBLIC_API_URL` in Vercel
2. Set `FRONTEND_URL` in Render
3. Redeploy both services
4. Test thoroughly
