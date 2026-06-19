# 🦅 Facebook AI Wildlife Content Pipeline

Fully automated, serverless Facebook content system.
Runs on GitHub Actions — your laptop never needs to be on.

**Stack:** Gemini 2.5 Pro → Veo3 Lite → GitHub Releases → Facebook Graph API

---

## What runs automatically

| Pipeline | Schedule (EAT) | What it does | Cost |
|---|---|---|---|
| 1 — Prompt Factory | 8:00 AM daily | Gemini generates 10 animal POV scripts + captions | FREE |
| 2 — Video Factory | 2:00 PM daily | Veo3 generates MP4s, uploads to GitHub Releases | ~$0.72/day (3 clips) |
| 3 — Facebook Poster | 10pm, 11pm, midnight | Posts one video per slot to your pages at US prime-time | FREE |
| 4 — Boost Post | Manual trigger | Reshares underperforming posts from booster account | FREE |

**US prime-time from Kenya:** 10pm–midnight EAT = 7pm–9pm EST. No proxy needed.

---

## One-time setup (~20 minutes)

### Step 1 — Fork/create the GitHub repo

Push this folder to a **public** GitHub repo.
(Public repos get unlimited free Actions minutes.)

```bash
git init
git add .
git commit -m "init: fb wildlife pipeline"
git remote add origin https://github.com/YOUR_USERNAME/fb-wildlife-pipeline.git
git push -u origin main
```

---

### Step 2 — Get your Gemini API key (FREE)

1. Go to **aistudio.google.com**
2. Click **Get API key** → Create API key
3. Copy the key — you'll add it as a GitHub Secret

Free tier: 250 requests/day for Gemini 2.5 Pro (text). More than enough.

---

### Step 3 — Get your Facebook Page Access Tokens

**A. Create a Facebook Developer App:**
1. Go to **developers.facebook.com/apps**
2. Create app → type: **Business**
3. Add product: **Facebook Login for Business**
4. Note your **App ID** and **App Secret**

**B. Get a short-lived user token:**
1. Go to **developers.facebook.com/tools/explorer**
2. Select your app
3. Click **Generate Access Token**
4. Add these permissions:
   - `pages_manage_posts`
   - `pages_read_engagement`
   - `pages_show_list`
   - `publish_video`
5. Copy the token

**C. Run the token setup script locally:**
```bash
pip install requests python-dotenv

# Create .env file
echo "FB_APP_ID=your_app_id" > .env
echo "FB_APP_SECRET=your_app_secret" >> .env

python scripts/setup_tokens.py --short-token YOUR_SHORT_TOKEN
```

The script prints each page's token value and the Secret name to add it under.

---

### Step 4 — Add GitHub Secrets

Go to: **Your Repo → Settings → Secrets and variables → Actions → New repository secret**

Add these secrets:

| Secret Name | Value | Where to get it |
|---|---|---|
| `GEMINI_API_KEY` | Your Gemini API key | aistudio.google.com |
| `GOOGLE_API_KEY` | Same key (for Veo3 billing) | aistudio.google.com |
| `FB_PAGE_TOKEN_1` | Token for page 1 | From setup_tokens.py output |
| `FB_PAGE_TOKEN_2` | Token for page 2 | From setup_tokens.py output |
| `FB_PAGE_TOKEN_3` | Token for page 3 | From setup_tokens.py output |
| `FB_PAGE_IDS` | `pageID1,pageID2,pageID3` | From setup_tokens.py output |
| `FB_BOOSTER_TOKEN` | Token for your booster account | From setup_tokens.py (50k+ follower page) |

> ⚠️ Never put real tokens in code files. Secrets only.

---

### Step 5 — Enable Veo3 billing (for video generation)

1. Go to **console.cloud.google.com**
2. Enable billing on your project
3. Enable the **Vertex AI API** and **Generative Language API**
4. Add a payment method

**Cost control:** Pipeline 2 defaults to `MAX_VIDEOS=3` (≈$0.72/day).
You can override this per-run in Actions → Workflow dispatch.

**To skip video costs entirely:** Generate videos manually in Google Flow
(your AI Pro sub includes 1,000 Flow credits/month), download the MP4s,
and upload them to a GitHub Release tagged `videos-YYYY-MM-DD`.
Pipeline 3 will pick them up and post automatically.

---

### Step 6 — Enable GitHub Actions

1. Go to **Your Repo → Actions**
2. Click **Enable Actions**
3. The workflows will run automatically on schedule

**Test run (without spending money):**
- Go to Actions → **1 — Prompt Factory** → Run workflow
- Check `data/prompts/` for today's JSON file
- Go to Actions → **3 — Facebook Poster** → Run workflow
- This will attempt to post — make sure your page tokens are correct first

---

## File structure

```
fb-wildlife-pipeline/
├── .github/
│   └── workflows/
│       ├── 1-prompt-factory.yml    ← 8am EAT daily
│       ├── 2-video-factory.yml     ← 2pm EAT daily
│       ├── 3-fb-poster.yml         ← 10pm, 11pm, midnight EAT
│       └── 4-boost-post.yml        ← manual trigger
├── scripts/
│   ├── generate_prompts.py         ← Gemini API → batch JSON
│   ├── generate_videos.py          ← Veo3 API → MP4 files
│   ├── post_to_facebook.py         ← Graph API → Facebook
│   ├── boost_post.py               ← Booster account reshare
│   └── setup_tokens.py             ← One-time token setup
├── data/
│   └── prompts/                    ← Auto-populated daily
├── pages_config.json               ← Page IDs (no tokens)
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Daily flow (what happens automatically)

```
8:00 AM EAT  → Gemini writes 10 video scripts + captions → saved to data/prompts/
2:00 PM EAT  → Veo3 generates 3 MP4s → uploaded to GitHub Release
10:00 PM EAT → Video 0 posted to Page 1 (= 7pm EST)
11:00 PM EAT → Video 1 posted to Page 2 (= 8pm EST)
12:00 AM EAT → Video 2 posted to Page 3 (= 9pm EST)
```

If a video gets fewer than expected views after 24 hours:
- Go to Actions → **4 — Boost Post** → Run workflow
- Enter the post ID → done

---

## Costs summary

| Item | Monthly cost |
|---|---|
| GitHub Actions | FREE (public repo) |
| Gemini 2.5 Pro (text) | FREE (250 req/day) |
| Veo3 Lite (3 clips/day) | ~$22/month |
| GitHub Releases storage | FREE (2GB) |
| **Total** | **~$22/month** |

With Veo3 skipped (manual video uploads): **$0/month**

---

## Troubleshooting

**Pipeline 1 fails:** Check GEMINI_API_KEY is set correctly. Test at aistudio.google.com.

**Pipeline 2 fails with billing error:** Enable billing on your Google Cloud project and make sure the Vertex AI API is enabled.

**Pipeline 3 fails with OAuthException:** Your page token expired (user tokens expire in 60 days, page tokens don't if obtained correctly). Re-run `setup_tokens.py`.

**Videos get 0 views:** Make sure the Facebook page is in Professional Mode and has at least some content/followers before expecting organic reach. New pages need 2–4 weeks of consistent posting.

**Actions not running:** Check the repo is public and Actions are enabled under Settings → Actions → General.
