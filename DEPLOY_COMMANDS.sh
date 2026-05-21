# Quick Deploy Commands

# 1. Push to GitHub (run from /app)
git add .
git commit -m "feat: AniPulse landing page ready for deployment"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main

# 2. Deploy to Vercel
# Option A: Use Vercel Dashboard (recommended)
# - Go to vercel.com
# - Import your GitHub repo
# - Click Deploy

# Option B: Use Vercel CLI
npm install -g vercel
vercel login
vercel --prod
