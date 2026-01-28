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

### Option 2: Alternative Deployment

Consider deploying to:
- **Railway** - Better for long-running processes
- **Render** - Supports Flask with persistent storage
- **Fly.io** - Good for Dockerized apps
- **Heroku** - Traditional PaaS option

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
