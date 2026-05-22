# Frontend-Backend Integration Configuration

## Environment Configuration

### Development (Local)
**File:** `frontend/.env`
```
REACT_APP_BACKEND_URL=https://anipulse-landing-production.up.railway.app
```

### Production (Vercel)
**File:** `frontend/.env.production`
```
REACT_APP_BACKEND_URL=https://anipulse-landing-production.up.railway.app
```

## Backend Endpoints Used

### Upload Workflow
- `POST /api/upload/sessions` - Create upload session
- `POST /api/upload/sessions/{id}/videos` - Upload video clip
- `POST /api/upload/sessions/{id}/audio` - Upload music track

### Generation Workflow
- `POST /api/generate` - Start AMV generation
- `GET /api/generate/{job_id}/status` - Poll progress
- `GET /api/generate/{job_id}/timeline` - Get timeline JSON
- `GET /api/generate/{job_id}/download` - Download final MP4

### Health Checks
- `GET /api/status` - Health check
- `GET /api/generate/queue/stats` - Queue status

## Frontend Flow

1. **Page Load**
   - Create upload session
   - Get `session_id`

2. **Upload Phase**
   - User drops video clips (3-5)
   - Upload each via `/api/upload/sessions/{id}/videos`
   - User drops music file
   - Upload via `/api/upload/sessions/{id}/audio`

3. **Generation Phase**
   - User clicks "Generate AMV"
   - Call `/api/generate` with `session_id`
   - Receive `job_id`

4. **Progress Tracking**
   - Poll `/api/generate/{job_id}/status` every 2 seconds
   - Update progress bar (0-100%)
   - Show stage: Analyzing → Timeline → Rendering

5. **Completion**
   - Status becomes `completed`
   - Show download button
   - Link to `/api/generate/{job_id}/download`

## Error Handling

### Upload Errors
- File size validation (max 100MB)
- File type validation (video/audio)
- Network errors (retry)

### Generation Errors
- No clips uploaded
- No audio uploaded
- Processing failures
- Timeout (5 min)

## CORS Configuration

Backend allows:
- Origin: `https://anipulse-landing.vercel.app`
- Methods: GET, POST, PUT, DELETE, OPTIONS
- Headers: Content-Type, Authorization

## Testing

### Local Testing
```bash
# Test backend health
curl https://anipulse-landing-production.up.railway.app/api/status

# Test session creation
curl -X POST https://anipulse-landing-production.up.railway.app/api/upload/sessions

# Test queue
curl https://anipulse-landing-production.up.railway.app/api/generate/queue/stats
```

### Frontend Testing
1. Visit: https://anipulse-landing.vercel.app/upload
2. Upload 3 video clips
3. Upload music file
4. Click "Generate AMV"
5. Verify progress updates
6. Download final MP4

## Deployment

### Frontend (Vercel)
- Auto-deploys on push to main
- Uses `frontend/.env.production`
- Build: `yarn build`
- Output: `.next/`

### Backend (Railway)
- Auto-deploys on push to main
- Uses Railway environment variables
- Start: `uvicorn server:app --host 0.0.0.0 --port $PORT`

## Status

✅ Backend: Deployed on Railway
✅ Frontend: Connected to Railway backend
✅ Upload workflow: Working
✅ Generation workflow: Implemented
✅ Progress tracking: Real-time
✅ Download: Functional
✅ Error handling: Comprehensive
