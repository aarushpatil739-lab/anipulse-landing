# 🚀 Deployment Guide: GitHub + Vercel

## Step 1: Prepare Your GitHub Repository

### Create a New Repository on GitHub

1. Go to [github.com](https://github.com) and log in
2. Click the "+" icon in the top right corner
3. Select "New repository"
4. Name your repository (e.g., `anipulse-landing`)
5. Choose "Public" (required for free Vercel deployment)
6. **Do NOT** initialize with README, .gitignore, or license (we already have these)
7. Click "Create repository"

## Step 2: Push Your Code to GitHub

Run these commands from your project root (`/app`):

```bash
# Check current status
git status

# Add all files
git add .

# Commit your changes
git commit -m "feat: AniPulse landing page - cyberpunk anime video editor"

# Set main as default branch
git branch -M main

# Add your GitHub repository as remote (replace with your repo URL)
git remote add origin https://github.com/YOUR_USERNAME/anipulse-landing.git

# Push to GitHub
git push -u origin main
```

**Replace `YOUR_USERNAME` with your actual GitHub username!**

## Step 3: Deploy to Vercel

### Option A: Via Vercel Dashboard (Easiest)

1. **Go to Vercel**
   - Visit [vercel.com](https://vercel.com)
   - Click "Sign Up" or "Log In"
   - Connect with your GitHub account

2. **Import Your Project**
   - Click "Add New..." → "Project"
   - Select "Import Git Repository"
   - Find your `anipulse-landing` repository
   - Click "Import"

3. **Configure Project**
   - **Framework Preset:** Other (or None)
   - **Root Directory:** Leave as `./` (Vercel will use vercel.json config)
   - **Build Command:** Auto-detected from vercel.json
   - **Output Directory:** Auto-detected from vercel.json
   - **Install Command:** Auto-detected from vercel.json

4. **Environment Variables**
   - Click "Environment Variables" (if needed)
   - Add `REACT_APP_BACKEND_URL` = `https://your-api-domain.com` (if you plan to add backend later)
   - For now, you can skip this since it's a static landing page

5. **Deploy**
   - Click "Deploy"
   - Wait 2-3 minutes for build to complete
   - ✅ Your site will be live at `https://anipulse-landing.vercel.app`

### Option B: Via Vercel CLI

```bash
# Install Vercel CLI globally
npm install -g vercel

# Login to Vercel
vercel login

# Deploy from project root
cd /app
vercel

# Follow the prompts:
# - Set up and deploy? Y
# - Which scope? [Your account]
# - Link to existing project? N
# - Project name? anipulse-landing
# - In which directory is your code located? ./

# For production deployment
vercel --prod
```

## Step 4: Custom Domain (Optional)

1. In Vercel dashboard, go to your project
2. Click "Settings" → "Domains"
3. Add your custom domain (e.g., `anipulse.com`)
4. Follow Vercel's DNS instructions
5. SSL certificate is automatically provisioned

## Step 5: Automatic Deployments

✅ **Good news:** Every push to your `main` branch will automatically deploy to Vercel!

```bash
# Make changes to your code
# ...

# Commit and push
git add .
git commit -m "update: improved animations"
git push

# Vercel automatically builds and deploys! 🎉
```

## 🔧 Troubleshooting

### Build Fails

**Error: "Command failed: cd frontend && yarn build"**

- Check that `package.json` has all dependencies
- Ensure Node.js version is compatible (16+)
- Try building locally first: `cd frontend && yarn build`

**Error: "Module not found"**

- Missing dependency. Add it: `yarn add <package-name>`
- Commit and push again

### Deployment is Slow

- First deployment takes 2-3 minutes
- Subsequent deployments are faster (1-2 minutes)
- Vercel caches dependencies

### Site Shows 404

- Check that `vercel.json` has the rewrite rule for SPA routing
- Verify output directory is set to `frontend/build`

### Images Not Loading

- Verify image URLs in `frontend/src/lib/content.js`
- Check if Unsplash/Pexels URLs are accessible
- Consider hosting images on Vercel or CDN for production

## 📊 Monitoring & Analytics

### Vercel Analytics (Free)

1. In Vercel dashboard, go to your project
2. Click "Analytics" tab
3. Enable Vercel Analytics (free tier available)
4. Get insights on:
   - Page views
   - Performance metrics (Web Vitals)
   - Geographic distribution

### Add Google Analytics (Optional)

1. Get your GA4 measurement ID
2. Add to `frontend/public/index.html`:

```html
<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-XXXXXXXXXX"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-XXXXXXXXXX');
</script>
```

## 🚀 Post-Deployment Checklist

- [ ] Test site on mobile and desktop
- [ ] Verify all sections load correctly
- [ ] Check animations are smooth
- [ ] Test navigation links
- [ ] Verify images load
- [ ] Check console for errors (F12 → Console)
- [ ] Test mobile menu
- [ ] Run Lighthouse audit (F12 → Lighthouse)
- [ ] Add custom domain (optional)
- [ ] Enable Vercel Analytics
- [ ] Share your live URL! 🎉

## 📝 Environment Variables (Future Backend)

When you add a backend API:

1. In Vercel dashboard → Settings → Environment Variables
2. Add:
   ```
   REACT_APP_BACKEND_URL = https://your-api.com
   ```
3. Redeploy for changes to take effect

## 🌐 Your Live URLs

- **Vercel URL:** `https://your-project.vercel.app` (after deployment)
- **Custom Domain:** `https://anipulse.com` (if configured)

---

**Need help?** Open an issue on GitHub or check [Vercel documentation](https://vercel.com/docs)

**Happy deploying! 🎉**
