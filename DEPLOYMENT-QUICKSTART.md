# Deployment Quick Start

**One-page guide to deploy CaseBase to production.**

## 🎯 Goal
- Frontend → GitHub Pages
- Backend → Render

## ⚡ Prerequisites Checklist

- [ ] GitHub account
- [ ] Render account (render.com)
- [ ] AWS S3 bucket created
- [ ] OpenAI API key
- [ ] Pinecone index created
- [ ] SendGrid API key (optional)
- [ ] Repository pushed to GitHub

## 🚀 Deployment Steps

### 1️⃣ Deploy Backend to Render (15 minutes)

```bash
# Ensure code is pushed to GitHub
git push origin main
```

**In Render Dashboard:**
1. New + → Web Service
2. Connect GitHub repo: `casebase-takehome`
3. Configure:
   - Name: `casebase-api`
   - Root Directory: `server`
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`

4. Add Environment Variables:
```
AWS_ACCESS_KEY_ID=<your_key>
AWS_SECRET_ACCESS_KEY=<your_secret>
S3_BUCKET_NAME=<your_bucket>
OPENAI_API_KEY=<your_key>
PINECONE_API_KEY=<your_key>
PINECONE_INDEX_NAME=casebase-documents
ALLOWED_ORIGINS=https://<YOUR-GITHUB-USERNAME>.github.io
```

5. Create → Wait for deployment
6. **Note your URL**: `https://your-app.onrender.com`

### 2️⃣ Update Frontend Config (2 minutes)

```bash
cd client

# Edit .env.production
echo "REACT_APP_API_URL=https://your-app.onrender.com" > .env.production

# Edit package.json - update homepage field:
# "homepage": "https://<YOUR-GITHUB-USERNAME>.github.io/casebase-takehome"
```

### 3️⃣ Deploy Frontend to GitHub Pages (5 minutes)

```bash
# Install gh-pages (if not already)
npm install

# Deploy
npm run deploy
```

**In GitHub:**
1. Go to repo → Settings → Pages
2. Source: `gh-pages` branch
3. Save
4. Wait 2-3 minutes

### 4️⃣ Test Your Deployment (5 minutes)

**Visit:** `https://<YOUR-GITHUB-USERNAME>.github.io/casebase-takehome`

Test:
- [ ] Frontend loads
- [ ] Upload a PDF
- [ ] Chat with documents
- [ ] Create PDF request
- [ ] Email functionality (if SendGrid configured)

## 🔄 Update Deployments

**Backend:**
```bash
git push origin main
# Render auto-deploys
```

**Frontend:**
```bash
cd client
npm run deploy
```

## 🐛 Quick Troubleshooting

| Issue | Fix |
|-------|-----|
| CORS error | Check `ALLOWED_ORIGINS` in Render matches GitHub Pages URL |
| API not responding | Verify backend is awake (free tier sleeps after 15min) |
| Frontend not loading | Wait 5 min after deploy, check GitHub Pages settings |
| PDF upload fails | Check AWS credentials in Render |
| Chat not working | Verify OpenAI & Pinecone keys, check Render logs |

## 📝 Important URLs

**Your deployed app:**
- Frontend: `https://<YOUR-USERNAME>.github.io/casebase-takehome`
- Backend: `https://your-app.onrender.com`
- API Docs: `https://your-app.onrender.com/docs`

**Dashboards:**
- Render: https://dashboard.render.com
- GitHub Pages: `https://github.com/<YOU>/casebase-takehome/settings/pages`

## ⚠️ Remember To Replace

1. `<YOUR-GITHUB-USERNAME>` → Your actual GitHub username
2. `your-app` → Your actual Render service name
3. All `<your_key>` → Your actual API keys

## 🎉 Done!

Full deployment guide: See `DEPLOYMENT.md`

---

**Total time: ~30 minutes** (excluding waiting for deployments)
