# Frontend Configuration for Railway Backend

## Update Backend URL in Frontend

After deploying backend to Railway, update your frontend to use the deployed backend URL.

### Step 1: Get Railway Backend URL

After deploying to Railway, you'll get a URL like:
```
https://anipulse-backend-production.up.railway.app
```

Or your custom domain:
```
https://api.anipulse.com
```

### Step 2: Update Vercel Environment Variables

1. Go to your Vercel project: https://vercel.com/dashboard
2. Click on your project: `anipulse-landing`
3. Go to **Settings** → **Environment Variables**
4. Update or add `REACT_APP_BACKEND_URL`:

```
Variable Name: REACT_APP_BACKEND_URL
Value: https://anipulse-backend-production.up.railway.app
Environment: Production, Preview, Development
```

5. Click **Save**

### Step 3: Redeploy Frontend

Option A: **Automatic Redeploy**
- Vercel will automatically redeploy when you save env variables
- Wait 2-3 minutes for deployment

Option B: **Manual Redeploy**
```bash
# Using Vercel CLI
vercel --prod

# Or push to GitHub (triggers auto-deploy)
git commit --allow-empty -m "Trigger redeploy with new backend URL"
git push origin main
```

### Step 4: Verify Connection

1. Open your frontend: https://anipulse-landing.vercel.app
2. Go to `/upload` page
3. Check browser console (F12)
4. You should see successful API calls to Railway backend

## Alternative: Update .env Locally for Testing

If you want to test locally first:

1. **Update frontend/.env:**
```bash
REACT_APP_BACKEND_URL=https://anipulse-backend-production.up.railway.app
```

2. **Restart frontend:**
```bash
cd /app/frontend
yarn start
```

3. **Test upload functionality**

## Troubleshooting

### CORS Errors

If you see CORS errors in browser console:

1. **Check Railway environment variables:**
   - Make sure `CORS_ORIGINS` includes your Vercel domain
   - Example: `https://anipulse-landing.vercel.app,https://*.vercel.app`

2. **Check Railway logs:**
   - Go to Railway dashboard
   - Click on your backend service
   - Check logs for CORS-related messages

3. **Update CORS_ORIGINS:**
   - Add your exact Vercel domain
   - Include preview deployments: `https://*.vercel.app`
   - Redeploy backend

### API Not Found (404)

- Verify backend URL is correct
- Check that `/api` prefix is included in requests
- Example: `https://backend.railway.app/api/upload/sessions`

### Connection Refused

- Backend might not be deployed yet
- Check Railway deployment status
- Verify backend health: `https://backend.railway.app/health`

## Environment Variables Summary

### Railway (Backend)
```
MONGO_URL=mongodb+srv://...
DB_NAME=anipulse
CORS_ORIGINS=https://anipulse-landing.vercel.app,https://*.vercel.app
PORT=8000
```

### Vercel (Frontend)
```
REACT_APP_BACKEND_URL=https://anipulse-backend-production.up.railway.app
```

## Testing Checklist

- [ ] Backend deployed to Railway
- [ ] MongoDB connected (check health endpoint)
- [ ] CORS configured with Vercel domains
- [ ] Frontend env variable updated in Vercel
- [ ] Frontend redeployed
- [ ] Upload session creation works
- [ ] File uploads work
- [ ] No CORS errors in console
- [ ] All API endpoints responding

## Quick Test Commands

```bash
# Test backend health
curl https://your-backend.railway.app/health

# Test API root
curl https://your-backend.railway.app/api/

# Test create session
curl -X POST https://your-backend.railway.app/api/upload/sessions

# Should return: {"success": true, "session": {...}}
```

## Next Steps

1. Deploy backend to Railway (see RAILWAY_DEPLOYMENT.md)
2. Get Railway backend URL
3. Update Vercel environment variable
4. Redeploy frontend
5. Test upload workflow
6. Monitor Railway logs for any issues
