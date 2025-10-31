# Deployment Guide

## Option 1: Streamlit Community Cloud (Recommended - FREE)

Streamlit Community Cloud is the easiest and best way to deploy Streamlit apps. It's free and designed specifically for Streamlit.

### Steps:

1. **Push your code to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/yourusername/inventory-processor.git
   git push -u origin main
   ```

2. **Sign up at Streamlit Community Cloud**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Sign in with your GitHub account

3. **Deploy your app**
   - Click "New app"
   - Select your repository
   - Set the main file path to: `app.py`
   - Click "Deploy"

4. **Your app will be live!**
   - You'll get a URL like: `https://your-app-name.streamlit.app`

### Required Files (Already Created):
- ✅ `app.py` - Main application file
- ✅ `process_inventory.py` - Processing logic
- ✅ `requirements.txt` - Python dependencies
- ✅ `.streamlit/config.toml` - Streamlit configuration

## Option 2: Alternative Hosting Platforms

If you need alternatives to Streamlit Community Cloud:

### Render (Free tier available)
- Supports Streamlit apps
- Connect GitHub repo
- Auto-deploys on push

### Railway (Free tier available)
- Easy deployment
- Connect GitHub repo
- Good for Streamlit apps

### Heroku (Paid now, but has alternatives)
- Was free, now requires payment
- Consider Railway or Render instead

## Why Not Netlify?

Netlify is designed for:
- Static websites (HTML, CSS, JavaScript)
- Serverless functions (short-lived, event-driven)
- JAMstack applications

Streamlit requires:
- Long-running Python server
- Persistent connections for WebSocket
- Full Python runtime environment

Therefore, Streamlit apps cannot run on Netlify directly.

## Converting for Netlify (Not Recommended)

If you absolutely need Netlify, you would need to:
1. Rewrite the entire app in JavaScript/React
2. Use client-side libraries for CSV processing
3. Use serverless functions for file processing (limited to 10 seconds on free tier)
4. Lose many Streamlit features

**This is not recommended** - Streamlit Community Cloud is the perfect solution!

