# Vertex AI Setup — Step by Step

## Your Credentials
- **API Key:** AQ.Ab8RN6Jhz4HSqpXz_O15D_8gsklKalrO16Yf_Hf0BtEA9VZR_A
- **Project ID:** storyboard-engine-491200

## Files Changed (2 files only)
1. `app.py` — new `get_client()` function with Vertex AI support
2. `templates/index.html` — added Project ID field in settings

## Files NOT Changed (keep your existing ones)
- `engine.py` — no changes needed
- `requirements.txt` — no changes needed
- `Procfile` — no changes needed
- `railway.json` — no changes needed

## Step-by-Step Deploy

### 1. Replace files in your GitHub repo
Copy these 2 files into your repo, replacing the old ones:
- `app.py` → root of repo
- `templates/index.html` → templates folder

### 2. Push to GitHub
```bash
git add app.py templates/index.html
git commit -m "Switch to Vertex AI for $300 credit"
git push
```

### 3. Railway auto-deploys
Railway will detect the push and redeploy automatically.
Wait for the deploy to finish (check Railway dashboard).

### 4. Open your app on phone
Go to your Railway URL.

### 5. Enter credentials in Settings
- Tap ⚙ Settings
- **API Key:** AQ.Ab8RN6Jhz4HSqpXz_O15D_8gsklKalrO16Yf_Hf0BtEA9VZR_A
- **Cloud Project ID:** storyboard-engine-491200
- Settings auto-save

### 6. Test one image
Upload a storyboard, run Characters step, generate ONE character.
Check the log — it should say:
```
✅ Vertex AI mode (project: storyboard-engine-491200)
```

### 7. Verify billing
Go to console.cloud.google.com → Billing → Credits
Check if "$0 out of $300 used" changes to something like "$0.05 out of $300"

If yes → you're using the credit! Run everything.
If no → check that billing account is linked to storyboard-engine project.

## How It Works
- When Project ID is filled in → Vertex AI mode → $300 credit
- When Project ID is empty → AI Studio mode → charges your card
- Same models, same quality, different billing pipe

## Troubleshooting
- **"Permission denied"** → Vertex AI API not enabled on project
- **"Invalid API key"** → Make sure you're using the Vertex AI key (starts with AQ.), not the AI Studio key (starts with AIza)
- **429 errors** → Rate limited, the app auto-waits 30s and retries
- **Credit not moving** → Check Billing → make sure project is linked to billing account with $300
