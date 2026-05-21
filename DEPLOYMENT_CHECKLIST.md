# AniPulse Railway + Vercel Deployment Checklist

## ✅ Phase 1: MongoDB Setup (5 minutes)

### Option A: MongoDB Atlas (Recommended)

- [ ] Go to https://cloud.mongodb.com
- [ ] Create free account (if needed)
- [ ] Click "Build a Database" → "Free Tier" (M0)
- [ ] Choose region (closest to your users)
- [ ] Create cluster (wait 3-5 minutes)
- [ ] Click "Database Access" → "Add Database User"
  - Username: `anipulse`
  - Password: Generate secure password
  - Database User Privileges: Read and write to any database
- [ ] Click "Network Access" → "Add IP Address"
  - Allow access from anywhere: `0.0.0.0/0` (for Railway)
- [ ] Click "Connect" → "Connect your application"
  - Copy connection string
  - Replace `<password>` with your actual password
  - Replace `<dbname>` with `anipulse`
  - Example: `mongodb+srv://anipulse:PASSWORD@cluster0.xxxxx.mongodb.net/anipulse?retryWrites=true&w=majority`

### Option B: Railway MongoDB Plugin

- [ ] Go to Railway project
- [ ] Click "New" → "Database" → "MongoDB"
- [ ] Railway auto-configures `${{MongoDB.MONGO_URL}}`
- [ ] Use this in environment variables

## ✅ Phase 2: Railway Backend Deployment (10 minutes)

- [ ] **Create Railway Account**
  - Go to https://railway.app
  - Sign up with GitHub

- [ ] **Create New Project**
  - Click "New Project"
  - Select "Deploy from GitHub repo"
  - Choose `aarushpatil739-lab/anipulse-landing`
  - Click "Deploy"

- [ ] **Configure Service**
  - Click on the deployed service
  - Go to "Settings"
  - Set "Root Directory": `backend`
  - Save

- [ ] **Add Environment Variables**
  - Click "Variables" tab
  - Add the following (click "Add Variable" for each):

```
MONGO_URL
mongodb+srv://anipulse:YOUR_PASSWORD@cluster.mongodb.net/anipulse

DB_NAME
anipulse

CORS_ORIGINS
https://anipulse-landing.vercel.app,https://*.vercel.app

PORT
8000
```

- [ ] **Trigger Redeploy**
  - Click "Deployments" tab
  - Click "Redeploy" (or it auto-deploys after env vars)
  - Wait 2-3 minutes for build

- [ ] **Get Railway URL**
  - Click "Settings" → "Domains"
  - Click "Generate Domain" (if not auto-generated)
  - Copy URL: `https://anipulse-backend-production-xxxx.up.railway.app`

- [ ] **Test Backend**
  - Open in browser: `https://YOUR-BACKEND-URL.railway.app/health`
  - Should show: `{"status": "healthy", "database": "connected"}`
  - Test API: `https://YOUR-BACKEND-URL.railway.app/api/`
  - Should show: API info

## ✅ Phase 3: Vercel Frontend Configuration (3 minutes)

- [ ] **Update Environment Variable**
  - Go to https://vercel.com/dashboard
  - Click your project: `anipulse-landing`
  - Go to "Settings" → "Environment Variables"
  - Find `REACT_APP_BACKEND_URL` or add new variable:
    - Name: `REACT_APP_BACKEND_URL`
    - Value: `https://YOUR-RAILWAY-URL.railway.app` (your Railway backend URL)
    - Environment: Check all (Production, Preview, Development)
  - Click "Save"

- [ ] **Redeploy Frontend**
  - Go to "Deployments" tab
  - Click "..." on latest deployment → "Redeploy"
  - Or: Make any commit to trigger auto-deploy
  - Wait 2-3 minutes

## ✅ Phase 4: Testing (5 minutes)

- [ ] **Test Frontend Connection**
  - Go to: `https://anipulse-landing.vercel.app`
  - Open browser console (F12)
  - Click "Start Creating" or go to `/upload`
  - Check console for API calls - no CORS errors

- [ ] **Test Upload Workflow**
  - Go to `/upload` page
  - Check that session is created (no errors)
  - Try uploading a small video file (test.mp4)
  - Try uploading an audio file (test.mp3)
  - Verify upload progress shows
  - Check files appear in UI

- [ ] **Check Backend Logs**
  - Go to Railway dashboard
  - Click your backend service
  - Click "Logs" or "Deployments" → latest → "View Logs"
  - Look for:
    - `MongoDB connection successful`
    - `Starting AniPulse Backend API`
    - No error messages

- [ ] **Check Database**
  - Go to MongoDB Atlas dashboard
  - Click "Browse Collections"
  - Should see `anipulse` database
  - Should see `upload_sessions` collection
  - Should have documents from test uploads

## ✅ Phase 5: Verification (2 minutes)

### Test These URLs:

```bash
# Health check
curl https://YOUR-BACKEND.railway.app/health

# API root
curl https://YOUR-BACKEND.railway.app/api/

# Create session
curl -X POST https://YOUR-BACKEND.railway.app/api/upload/sessions

# Frontend
https://anipulse-landing.vercel.app/upload
```

### Expected Results:

- [x] Health endpoint returns "healthy"
- [x] API returns service info
- [x] Session creation returns session ID
- [x] Frontend loads without errors
- [x] Upload page creates session
- [x] Can upload files
- [x] No CORS errors

## 🐛 Troubleshooting

### Backend Issues

**Build Fails:**
- Check Railway logs for specific error
- Verify `requirements.txt` is in `/backend` folder
- Verify `runtime.txt` specifies Python 3.11

**MongoDB Connection Fails:**
- Verify connection string is correct
- Check password has no special characters (or URL encode them)
- Verify IP whitelist includes `0.0.0.0/0`
- Test connection string locally first

**Service Won't Start:**
- Check Railway logs
- Verify `PORT` environment variable is set
- Check for import errors in logs

### Frontend Issues

**CORS Errors:**
- Verify `CORS_ORIGINS` in Railway includes exact Vercel domain
- Include both production and preview: `https://anipulse-landing.vercel.app,https://*.vercel.app`
- Redeploy backend after updating CORS

**API 404 Errors:**
- Verify `REACT_APP_BACKEND_URL` is set correctly in Vercel
- Must NOT have trailing slash
- Must include `https://`
- Redeploy frontend after updating

**Session Creation Fails:**
- Check backend logs in Railway
- Verify MongoDB is connected (health endpoint)
- Check browser network tab for actual error

### Database Issues

**Collections Not Created:**
- MongoDB creates collections on first write
- Upload a file to trigger collection creation
- Check Railway logs for MongoDB errors

**Authentication Fails:**
- Verify database user was created
- Check password is correct in connection string
- Ensure user has read/write permissions

## 📊 Cost Estimate

### Free Tier Usage:

**Railway:**
- $5 free credits per month
- Estimated usage: ~$3-4/month (light use)
- Sufficient for MVP/testing

**MongoDB Atlas:**
- Free tier: 512MB storage
- Unlimited connections
- Good for 100K+ sessions

**Vercel:**
- Free tier: 100GB bandwidth
- Unlimited deployments
- Good for ~50K visitors/month

**Total Cost:** $0-5/month for MVP

## 🎯 Success Criteria

- ✅ Backend deployed and healthy
- ✅ MongoDB connected
- ✅ Frontend can reach backend
- ✅ Upload workflow works end-to-end
- ✅ No CORS errors
- ✅ Files persist in database
- ✅ All logs show success messages

## 📱 Share Your App

Once deployed, share:
- Frontend: `https://anipulse-landing.vercel.app`
- API Docs: `https://YOUR-BACKEND.railway.app/docs`

## 🔄 Future Updates

To deploy changes:

1. **Backend Updates:**
   - Push to GitHub
   - Railway auto-deploys
   - Check logs for success

2. **Frontend Updates:**
   - Push to GitHub
   - Vercel auto-deploys
   - Check deployment status

3. **Environment Variables:**
   - Update in Railway/Vercel dashboards
   - Trigger manual redeploy

## ⏱️ Total Time Estimate

- MongoDB Setup: 5 minutes
- Railway Deployment: 10 minutes
- Vercel Configuration: 3 minutes
- Testing: 5 minutes
- **Total: ~25 minutes**

## 🆘 Need Help?

- Railway Discord: https://discord.gg/railway
- Railway Docs: https://docs.railway.app
- MongoDB Support: https://www.mongodb.com/docs/atlas/
- Vercel Support: https://vercel.com/support
