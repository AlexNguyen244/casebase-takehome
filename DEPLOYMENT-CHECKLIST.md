# Deployment Checklist

Use this checklist to deploy CaseBase to production.

## ✅ Pre-Deployment Checklist

### Accounts & Services
- [ ] GitHub account created
- [ ] Render account created (https://render.com)
- [ ] AWS S3 bucket created
- [ ] OpenAI API key obtained
- [ ] Pinecone index created
- [ ] SendGrid account setup (optional)

### Code Ready
- [ ] All code committed to git
- [ ] Code pushed to GitHub
- [ ] Tests passing locally
- [ ] Environment variables documented

## 📝 Configuration Updates

### 1. Update Frontend Package.json
**File:** `client/package.json`

Replace:
```json
"homepage": "https://<YOUR-GITHUB-USERNAME>.github.io/casebase-takehome",
```

**Your value:**
```
https://______________.github.io/casebase-takehome
```

### 2. Update Frontend Production Environment
**File:** `client/.env.production`

Replace:
```
REACT_APP_API_URL=https://your-app-name.onrender.com
```

**Your value (fill in after deploying backend):**
```
REACT_APP_API_URL=https://______________.onrender.com
```

### 3. Backend Render Configuration
**File:** `server/render.yaml`

Replace:
```yaml
ALLOWED_ORIGINS: https://<YOUR-GITHUB-USERNAME>.github.io
```

**Your value:**
```
ALLOWED_ORIGINS: https://______________.github.io
```

## 🚀 Deployment Steps

### Backend Deployment (Render)

- [ ] **Step 1:** Push code to GitHub
- [ ] **Step 2:** Go to Render dashboard
- [ ] **Step 3:** Create new Web Service
- [ ] **Step 4:** Connect GitHub repository
- [ ] **Step 5:** Configure service:
  - Name: `casebase-api`
  - Root Directory: `server`
  - Build: `pip install -r requirements.txt`
  - Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- [ ] **Step 6:** Add environment variables (see list below)
- [ ] **Step 7:** Create service
- [ ] **Step 8:** Wait for deployment to complete
- [ ] **Step 9:** Note your service URL: `https://______________.onrender.com`
- [ ] **Step 10:** Test health endpoint: `curl https://your-url.onrender.com/health`

### Frontend Deployment (GitHub Pages)

- [ ] **Step 1:** Update `client/.env.production` with Render URL
- [ ] **Step 2:** Update `client/package.json` homepage field
- [ ] **Step 3:** Install dependencies: `npm install`
- [ ] **Step 4:** Deploy: `npm run deploy`
- [ ] **Step 5:** Enable GitHub Pages in repo settings
- [ ] **Step 6:** Select `gh-pages` branch
- [ ] **Step 7:** Save and wait 2-3 minutes
- [ ] **Step 8:** Visit: `https://<username>.github.io/casebase-takehome`

## 🔑 Environment Variables for Render

Copy these to Render dashboard (Environment section):

**Required:**
```
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
S3_BUCKET_NAME=

OPENAI_API_KEY=

PINECONE_API_KEY=
PINECONE_INDEX_NAME=casebase-documents
PINECONE_DIMENSION=1536
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1

ALLOWED_ORIGINS=
```

**Optional:**
```
SENDGRID_API_KEY=
SENDGRID_FROM_EMAIL=noreply@casebase.com
```

## ✔️ Post-Deployment Verification

### Test Checklist

- [ ] Frontend loads without errors
- [ ] Backend health endpoint responds
- [ ] API docs accessible: `https://your-app.onrender.com/docs`
- [ ] Upload a test PDF
- [ ] PDF appears in list
- [ ] View PDF works
- [ ] Delete PDF works
- [ ] Chat responds to messages
- [ ] Chat includes source citations
- [ ] PDF creation works (if tested)
- [ ] Email works (if SendGrid configured)

### Troubleshooting Checklist

If something doesn't work:

- [ ] Check browser console for errors
- [ ] Check Render logs for backend errors
- [ ] Verify all environment variables are set
- [ ] Confirm CORS settings match frontend URL
- [ ] Wait for Render service to wake up (free tier)
- [ ] Check GitHub Pages deployment status
- [ ] Verify API URL in frontend is correct

## 📊 Deployment Status

**Backend:**
- [ ] Deployed
- [ ] Tested
- URL: `______________________________`

**Frontend:**
- [ ] Deployed
- [ ] Tested
- URL: `______________________________`

**Full Integration:**
- [ ] Working end-to-end

## 🎉 Success Criteria

Deployment is successful when:

✅ Frontend loads at GitHub Pages URL
✅ Backend responds to health checks
✅ Can upload PDFs through UI
✅ Can chat with documents
✅ CORS configured correctly
✅ No console errors
✅ All features functional

## 📞 Need Help?

Refer to:
- `DEPLOYMENT-QUICKSTART.md` - Quick reference
- `DEPLOYMENT.md` - Detailed guide
- Render logs for backend issues
- Browser console for frontend issues

---

**Deployment Date:** _______________
**Deployed By:** _______________
**Notes:** _______________
