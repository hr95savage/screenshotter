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

## Railway Deployment (recommended)

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
- Screenshots are stored on the container; they're lost on redeploy unless you add persistent storage.
- Free tier has usage limits; check [Railway pricing](https://railway.app/pricing).
- **If you see "Executable doesn't exist" for Chromium:** In Railway → your service → **Settings** → ensure **Builder** is **Dockerfile** (not Nixpacks). Then redeploy.
