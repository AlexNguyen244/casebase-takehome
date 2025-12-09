# Deployment Guide

Complete guide for deploying the CaseBase application:
- **Frontend** → GitHub Pages
- **Backend** → Render

## 📋 Prerequisites

Before deploying, ensure you have:
- ✅ GitHub account
- ✅ Render account (https://render.com)
- ✅ AWS account with S3 bucket created
- ✅ OpenAI API key
- ✅ Pinecone account with index created
- ✅ SendGrid API key (optional, for email features)

## 🚀 Part 1: Deploy Backend to Render

### Step 1: Prepare Your Repository

1. **Push your code to GitHub** (if not already done):
```bash
cd /path/to/casebase-takehome
git add .
git commit -m "Prepare for deployment"
git push origin main
```

### Step 2: Create Render Service

1. **Go to Render Dashboard**: https://dashboard.render.com/

2. **Click "New +" → "Web Service"**

3. **Connect your GitHub repository**:
   - Click "Connect account" if needed
   - Select your `casebase-takehome` repository
   - Click "Connect"

4. **Configure the service**:
   - **Name**: `casebase-api` (or your preferred name)
   - **Region**: Choose closest to your users
   - **Branch**: `main`
   - **Root Directory**: `server`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: `Free` (or paid for production)

5. **Click "Advanced"** and add environment variables:

   **Required Variables:**
   ```
   AWS_ACCESS_KEY_ID=<your_aws_access_key>
   AWS_SECRET_ACCESS_KEY=<your_aws_secret_key>
   AWS_REGION=us-east-1
   S3_BUCKET_NAME=<your_bucket_name>
   OPENAI_API_KEY=<your_openai_api_key>
   PINECONE_API_KEY=<your_pinecone_api_key>
   PINECONE_INDEX_NAME=casebase-documents
   PINECONE_DIMENSION=1536
   PINECONE_CLOUD=aws
   PINECONE_REGION=us-east-1
   ```

   **Optional Variables:**
   ```
   SENDGRID_API_KEY=<your_sendgrid_api_key>
   SENDGRID_FROM_EMAIL=noreply@casebase.com
   ```

   **IMPORTANT - CORS Configuration:**
   ```
   ALLOWED_ORIGINS=https://<YOUR-GITHUB-USERNAME>.github.io
   ```
   ⚠️ **Replace `<YOUR-GITHUB-USERNAME>` with your actual GitHub username!**

6. **Click "Create Web Service"**

7. **Wait for deployment** (takes 5-10 minutes):
   - Watch the logs for any errors
   - Once deployed, note your service URL (e.g., `https://casebase-api.onrender.com`)

### Step 3: Test Backend

```bash
# Test health endpoint
curl https://your-app-name.onrender.com/health

# Should return: {"status": "healthy"}
```

### Step 4: Update Frontend Configuration

1. **Update `client/.env.production`**:
```bash
cd client
nano .env.production
```

2. **Replace with your Render URL**:
```env
REACT_APP_API_URL=https://your-app-name.onrender.com
```
Replace `your-app-name` with your actual Render service name!

## 🌐 Part 2: Deploy Frontend to GitHub Pages

### Step 1: Update Package.json

1. **Edit `client/package.json`**:
```bash
cd client
nano package.json
```

2. **Update the `homepage` field**:
```json
"homepage": "https://<YOUR-GITHUB-USERNAME>.github.io/casebase-takehome",
```
Replace `<YOUR-GITHUB-USERNAME>` with your actual GitHub username!

### Step 2: Install Dependencies

```bash
cd client
npm install gh-pages --save-dev
```

### Step 3: Deploy to GitHub Pages

```bash
# Make sure you're in the client directory
cd client

# Deploy
npm run deploy
```

This will:
1. Build the production version (`npm run build`)
2. Deploy to GitHub Pages (`gh-pages -d build`)

### Step 4: Enable GitHub Pages

1. **Go to your GitHub repository**:
   - Navigate to `https://github.com/<YOUR-USERNAME>/casebase-takehome`

2. **Go to Settings → Pages**:
   - Under "Source", select branch: `gh-pages`
   - Under "Folder", select: `/ (root)`
   - Click "Save"

3. **Wait a few minutes** for deployment

4. **Visit your site**:
   ```
   https://<YOUR-GITHUB-USERNAME>.github.io/casebase-takehome
   ```

## 🔄 Part 3: Update Backend CORS

After deploying frontend, if you haven't already:

1. **Go to Render Dashboard** → Your service → Environment

2. **Update `ALLOWED_ORIGINS`**:
```
ALLOWED_ORIGINS=https://<YOUR-GITHUB-USERNAME>.github.io
```

3. **Click "Save Changes"**

4. **Service will automatically redeploy**

## ✅ Part 4: Verify Deployment

### Test Frontend
1. Visit: `https://<YOUR-GITHUB-USERNAME>.github.io/casebase-takehome`
2. Should see the CaseBase UI

### Test Upload
1. Upload a PDF through the UI
2. Check if it appears in the list
3. Verify in Render logs that RAG processing completed

### Test Chat
1. Type a message in the chatbot
2. Should receive AI response with sources

### Test API Directly
```bash
# Test health
curl https://your-app-name.onrender.com/health

# Test list PDFs
curl https://your-app-name.onrender.com/api/pdfs
```

## 🛠️ Part 5: Updating Your Deployment

### Update Frontend

```bash
cd client
npm run deploy
```

### Update Backend

Just push to GitHub:
```bash
git add .
git commit -m "Update backend"
git push origin main
```

Render will automatically redeploy!

## 🐛 Troubleshooting

### Frontend Issues

**Site not loading:**
- Check GitHub Pages settings are correct
- Verify `homepage` in package.json matches your GitHub Pages URL
- Wait 5-10 minutes after deployment

**CORS errors:**
- Verify `ALLOWED_ORIGINS` in Render matches your GitHub Pages URL
- Check browser console for exact error

**API calls failing:**
- Verify `REACT_APP_API_URL` in `.env.production` is correct
- Check backend is running on Render
- Test backend health endpoint directly

### Backend Issues

**Deployment failed:**
- Check Render logs for errors
- Verify all environment variables are set
- Check `requirements.txt` has all dependencies

**Health check failing:**
- Check logs for startup errors
- Verify port is using `$PORT` environment variable
- Check Python version (should be 3.11)

**PDF upload failing:**
- Verify AWS credentials are correct
- Check S3 bucket exists and has correct permissions
- Review Render logs for specific errors

**RAG not working:**
- Verify OpenAI API key is valid
- Check Pinecone credentials and index exists
- Review logs for embedding generation errors

**Email not sending:**
- Verify SendGrid API key is set
- Check SendGrid account is verified
- Review logs for SendGrid errors

### Common Render Issues

**Service sleeping (Free plan):**
- Free tier services sleep after 15 minutes of inactivity
- First request after sleep takes 30-60 seconds to wake up
- Upgrade to paid plan for always-on service

**Build timeout:**
- Increase build timeout in Render settings
- Optimize dependencies

**Environment variables not working:**
- Make sure variables don't have quotes in Render dashboard
- Rebuild service after adding variables

## 📊 Monitoring

### Render Dashboard
- View logs: Dashboard → Your service → Logs
- Monitor usage: Dashboard → Your service → Metrics
- Check deployments: Dashboard → Your service → Events

### GitHub Pages
- Check deployment: Repository → Actions
- View builds: Repository → Settings → Pages

## 💰 Cost Considerations

### Free Tier Limits

**Render Free Tier:**
- ✅ 750 hours/month (enough for 1 service always-on)
- ⚠️ Service sleeps after 15 min inactivity
- ⚠️ 512 MB RAM
- ✅ Automatic SSL

**GitHub Pages:**
- ✅ Completely free
- ✅ Unlimited bandwidth
- ✅ Custom domains supported

### Upgrade Recommendations

For production use:
- **Render**: $7/month (always-on, more RAM)
- **Domain**: $10-15/year (optional)

## 🔐 Security Checklist

Before going to production:

- [ ] Change all default secrets
- [ ] Enable S3 encryption
- [ ] Configure S3 bucket policies
- [ ] Use environment-specific API keys
- [ ] Add authentication to frontend
- [ ] Set up rate limiting
- [ ] Configure monitoring/alerts
- [ ] Regular security updates

## 📱 Custom Domain (Optional)

### For GitHub Pages:
1. Buy domain from provider (Namecheap, Google Domains, etc.)
2. Add CNAME record pointing to `<username>.github.io`
3. In GitHub repo: Settings → Pages → Custom domain
4. Enter your domain and save
5. Enable "Enforce HTTPS"

### For Render:
1. In Render Dashboard → Your service → Settings
2. Under "Custom Domain", click "Add Custom Domain"
3. Follow DNS configuration instructions
4. SSL certificate automatically provisioned

## 🎉 Success!

Your application should now be live:
- **Frontend**: `https://<YOUR-GITHUB-USERNAME>.github.io/casebase-takehome`
- **Backend**: `https://your-app-name.onrender.com`

## 📚 Additional Resources

- [GitHub Pages Documentation](https://docs.github.com/en/pages)
- [Render Documentation](https://render.com/docs)
- [React Deployment Guide](https://create-react-app.dev/docs/deployment/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
