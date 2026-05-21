# Railway Deployment Guide for AniPulse Backend

## Prerequisites

1. Railway account (https://railway.app)
2. MongoDB Atlas account (or Railway MongoDB plugin)
3. GitHub repository with backend code

## Step 1: Setup MongoDB

### Option A: MongoDB Atlas (Recommended)

1. Go to https://www.mongodb.com/cloud/atlas
2. Create a free cluster
3. Create a database user
4. Whitelist all IPs (0.0.0.0/0) for Railway access
5. Get connection string: `mongodb+srv://username:password@cluster.mongodb.net/anipulse?retryWrites=true&w=majority`

### Option B: Railway MongoDB Plugin

1. In Railway project, click "New"
2. Select "Database" → "MongoDB"
3. Railway will auto-configure connection string

## Step 2: Deploy Backend to Railway

### Via Railway Dashboard

1. **Create New Project**
   - Go to https://railway.app/new
   - Click "Deploy from GitHub repo"
   - Select `aarushpatil739-lab/anipulse-landing`

2. **Configure Service**
   - Root directory: `backend`
   - Click "Add variables"

3. **Add Environment Variables**
   ```
   MONGO_URL=mongodb+srv://username:password@cluster.mongodb.net/anipulse
   DB_NAME=anipulse
   CORS_ORIGINS=https://anipulse-landing.vercel.app,https://*.vercel.app
   PORT=8000
   ```

4. **Deploy**
   - Railway will automatically detect Python and deploy
   - Wait 2-3 minutes for build
   - Get deployment URL: `https://anipulse-backend.up.railway.app`

### Via Railway CLI

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Link project
cd /path/to/backend
railway link

# Set environment variables
railway variables set MONGO_URL="your-mongo-url"
railway variables set DB_NAME="anipulse"
railway variables set CORS_ORIGINS="https://anipulse-landing.vercel.app"

# Deploy
railway up
```

## Step 3: Configure Custom Domain (Optional)

1. In Railway project settings
2. Go to "Settings" → "Domains"
3. Click "Generate Domain" for free Railway domain
4. Or add custom domain: `api.anipulse.com`

## Step 4: Update Frontend Environment Variables

In Vercel project settings:

1. Go to Settings → Environment Variables
2. Update `REACT_APP_BACKEND_URL`:
   ```
   REACT_APP_BACKEND_URL=https://anipulse-backend.up.railway.app
   ```
3. Redeploy frontend

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|----------|
| `MONGO_URL` | MongoDB connection string | `mongodb+srv://user:pass@cluster.mongodb.net/db` |
| `DB_NAME` | Database name | `anipulse` |
| `CORS_ORIGINS` | Allowed frontend origins | `https://anipulse-landing.vercel.app` |
| `PORT` | Server port (Railway auto-sets) | `8000` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|----------|
| `LOG_LEVEL` | Logging level | `INFO` |
| `MAX_UPLOAD_SIZE` | Max file size | `2GB` |

## Verify Deployment

1. **Check health endpoint:**
   ```bash
   curl https://your-backend.railway.app/api/
   ```

2. **Test upload session creation:**
   ```bash
   curl -X POST https://your-backend.railway.app/api/upload/sessions
   ```

3. **Check logs in Railway dashboard**

## Troubleshooting

### Build Fails

- Check `requirements.txt` is present
- Verify Python version in `runtime.txt`
- Check Railway build logs

### MongoDB Connection Fails

- Verify MongoDB connection string
- Check IP whitelist (allow 0.0.0.0/0)
- Ensure database user has read/write permissions

### CORS Errors

- Add Vercel domain to `CORS_ORIGINS`
- Include both production and preview URLs
- Format: `https://domain1.com,https://domain2.com`

### Upload Fails

- Check file size limits
- Verify storage directory permissions
- Check Railway logs for errors

## Railway Project Structure

```
Railway Project: anipulse-backend
├── Service: backend (from GitHub)
│   ├── Root: /backend
│   ├── Build: pip install -r requirements.txt
│   ├── Start: uvicorn server:app --host 0.0.0.0 --port $PORT
│   └── Environment Variables
└── Database: MongoDB (optional plugin)
```

## Monitoring

1. **Railway Dashboard**
   - View logs
   - Monitor CPU/Memory usage
   - Track deployments

2. **Health Checks**
   - Railway auto-monitors your service
   - Restarts on failure
   - Sends alerts

## Scaling

**Free Tier:**
- $5 free credits/month
- Shared CPU
- 512MB RAM
- Good for MVP

**Paid Tier:**
- Pay per usage
- More CPU/RAM
- Better performance
- Custom domains

## Cost Optimization

1. Use MongoDB Atlas free tier (512MB)
2. Optimize file storage (move to S3 later)
3. Monitor Railway usage dashboard
4. Set usage alerts

## Next Steps

1. Deploy backend to Railway
2. Configure MongoDB connection
3. Update frontend env vars
4. Test upload workflow
5. Monitor logs and performance

## Support

- Railway Docs: https://docs.railway.app
- Railway Discord: https://discord.gg/railway
- MongoDB Atlas: https://www.mongodb.com/docs/atlas/
