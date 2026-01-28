# Deployment Notes

## Git Setup

To push to a git repository:

1. Create a repository on GitHub (or your preferred git host)

2. Add the remote:
```bash
git remote add origin <your-repo-url>
git branch -M main
git push -u origin main
```

## Vercel Deployment

⚠️ **Important Limitations:**

This Flask app uses Playwright which has special requirements:
- Playwright needs browser binaries installed
- Screenshot tasks can be long-running (may exceed Vercel's 10s timeout for Hobby plan, 60s for Pro)
- File storage is ephemeral in serverless functions

### Option 1: Vercel with Playwright (Advanced)

You'll need to:
1. Install Playwright browsers in the build process
2. Use Vercel Pro plan for longer timeouts
3. Consider using external storage (S3, etc.) for screenshots

## Railway Deployment (recommended for full app)

The repo includes a **Dockerfile** and **railway.json** so you can deploy the full screenshot app (with Playwright) to Railway and get a live URL.

### Steps

1. **Sign up / log in** at [railway.app](https://railway.app).

2. **New Project → Deploy from GitHub**
   - Click **New Project**
   - Choose **Deploy from GitHub repo**
   - Select **hr95savage/screenshotter** (or your fork)
   - Railway will detect the Dockerfile and build the app.

3. **Generate a public URL**
   - Open your deployed service
   - Go to **Settings** → **Networking** → **Generate Domain**
   - Railway will give you a URL like `screenshotter-production-xxxx.up.railway.app`

4. **Open the URL** – the full app (URL input, Single / Entire Website, real screenshots) will be live.

### Notes

- First deploy can take a few minutes (installing Chromium).
- Screenshots are stored on the container; they’re lost on redeploy unless you add persistent storage.
- Free tier has usage limits; check [Railway pricing](https://railway.app/pricing).
- **If you see "Executable doesn't exist" for Chromium:** In Railway → your service → **Settings** → ensure **Builder** is **Dockerfile** (not Nixpacks). Then redeploy.

### Vercel Setup (if proceeding):

1. Install Vercel CLI:
```bash
npm i -g vercel
```

2. Deploy:
```bash
vercel
```

3. You may need to modify the app to work within Vercel's serverless constraints.
