# Auto News Bot — India / World / Business / Sports → Instagram + Facebook

Fully automated pipeline: fetches breaking news → generates a branded image →
writes a caption + hashtags → posts to Instagram and Facebook → repeats on a
GitHub Actions schedule. No human interaction needed once it's set up.

## How it works

Each run (triggered by GitHub Actions cron):

1. **`scripts/select_and_generate.py`** — fetches news (GNews API + RSS
   feeds), skips anything already posted (`state/posted_log.json`),
   round-robins across India / World / Business / Sports, generates a
   1080×1080 "Breaking News" image into `docs/images/`, and writes
   `state/pending_post.json`.
2. The workflow **commits and pushes** that image so GitHub Pages serves it
   at a public URL.
3. **`scripts/publish_post.py`** waits until the image is actually live on
   Pages, then posts the image + caption to Instagram and Facebook via the
   Graph API, and updates `state/posted_log.json` so it's never reposted.

Everything is plain Python + Pillow — no image is ever downloaded from a
news site (avoids copyright issues); the image is an original template we
generate from the headline text.

## One-time setup

### 1. Enable GitHub Pages
Repo → **Settings → Pages** → Source: `Deploy from a branch` → Branch:
`main`, folder: `/docs`. Save. Note the resulting URL, e.g.
`https://yourname.github.io/news-bot`.

### 2. Add a repository variable
Repo → **Settings → Secrets and variables → Actions → Variables** →
New repository variable:
- `PAGES_BASE_URL` = `https://yourname.github.io/news-bot` (no trailing slash)

### 3. Add repository secrets
Repo → **Settings → Secrets and variables → Actions → Secrets** → New secret,
for each of:

| Secret | Where to get it |
|---|---|
| `GNEWS_API_KEY` | Free key at https://gnews.io (optional — RSS feeds work without it, GNews just adds more/better coverage) |
| `IG_USER_ID` | Your Instagram **Business/Creator** account's numeric ID, via Graph API Explorer |
| `IG_ACCESS_TOKEN` | Long-lived Instagram Graph API access token |
| `FB_PAGE_ID` | Your Facebook Page's numeric ID |
| `FB_PAGE_ACCESS_TOKEN` | Long-lived Facebook Page access token |

**Notes on tokens:**
- Instagram posting via the Graph API requires an Instagram **Business or
  Creator** account linked to a Facebook Page — personal IG accounts can't
  be posted to this way.
- Long-lived tokens typically expire after ~60 days. You'll need to
  regenerate and update the secret periodically (Meta doesn't currently
  offer a truly permanent token for this).

### 4. Push this repo to GitHub
```bash
git init
git add .
git commit -m "Initial news bot setup"
git branch -M main
git remote add origin https://github.com/yourname/news-bot.git
git push -u origin main
```

### 5. Test it manually first
Repo → **Actions** tab → "Auto Post Breaking News" → **Run workflow**
(this uses the `workflow_dispatch` trigger). Watch the logs. Confirm a post
actually appears on Instagram and Facebook before trusting the schedule.

## Adjusting the posting frequency

Edit `.github/workflows/post-news.yml`:
```yaml
schedule:
  - cron: "0 */3 * * *"   # every 3 hours (starting point)
```
Once you're confident it's working well, change to:
```yaml
schedule:
  - cron: "*/30 * * * *"  # every 30 minutes
```
GitHub Actions cron on the free tier can run as often as every 5 minutes,
but actual trigger timing isn't guaranteed to the minute — expect a few
minutes of jitter, which is normal for scheduled Actions.

## Things worth knowing

- **Rate limits**: Instagram/Facebook impose posting rate limits per app —
  30-minute intervals (48 posts/day) is generally fine, but check your app's
  current limits in Meta's dashboard before pushing frequency lower.
- **No fact-checking layer**: this bot posts headlines exactly as fetched
  from GNews/RSS with zero human review. If a source publishes something
  wrong or misleading, it goes straight to your page. Consider periodically
  spot-checking, especially early on.
- **De-duplication**: `state/posted_log.json` keeps the last 1000 posted
  article IDs so the same story won't be posted twice, even across restarts.
- **Category rotation**: `state/rotation.json` tracks the last category
  posted so consecutive posts cycle through India → World → Business →
  Sports rather than clumping.
- **Template design**: `scripts/generate_image.py` is fully editable — swap
  colors, fonts (`fonts/`), or layout to match your own brand.

## Local testing (before pushing to GitHub)

```bash
pip install -r requirements.txt
python scripts/select_and_generate.py   # generates docs/images/<uid>.png + state/pending_post.json
```
`publish_post.py` needs `PAGES_BASE_URL` pointing at a URL where the image
is *already* publicly reachable, so it's best tested only after your first
real GitHub Actions run (or by pointing it at any temporary public image
host for a dry run).
