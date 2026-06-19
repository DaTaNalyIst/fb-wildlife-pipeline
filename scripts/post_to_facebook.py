"""
Pipeline 3: Facebook Poster
============================
Runs at US prime-time (10pm, 11pm, midnight EAT = 7-9pm EST).
Each cron run posts one video to one Facebook page.

Slot 0 (10pm EAT / 7pm EST) → Page 1, Video 1
Slot 1 (11pm EAT / 8pm EST) → Page 2, Video 2
Slot 2 (midnight EAT / 9pm EST) → Page 3, Video 3

Reads video manifest from today's GitHub Release.
Downloads MP4, uploads to Facebook as a Reel.
Logs results back to the repo.

Cost: FREE — Facebook Graph API is free
"""
import os
import io
import json
import time
import requests
from datetime import datetime, date, timezone
from pathlib import Path

# ─── Config ───────────────────────────────────────────────────────────────────

TODAY = date.today().isoformat()
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")
RELEASE_TAG = os.environ.get("RELEASE_TAG", f"videos-{TODAY}")
FB_BASE = "https://graph.facebook.com/v21.0"

# Load page config
page_ids_raw = os.environ.get("FB_PAGE_IDS", "")
page_ids = [p.strip() for p in page_ids_raw.split(",") if p.strip()]

page_tokens = []
for i in range(1, 11):  # support up to 10 pages
    tok = os.environ.get(f"FB_PAGE_TOKEN_{i}", "")
    if tok:
        page_tokens.append(tok)

# Load optional group IDs for cross-sharing (max 3 to avoid spam flag)
group_ids_raw = os.environ.get("FB_GROUP_IDS", "")
group_ids = [g.strip() for g in group_ids_raw.split(",") if g.strip()][:3]

print(f"Facebook Poster — {TODAY}")
print(f"Release: {RELEASE_TAG}")
print(f"Pages configured: {len(page_ids)}")
print(f"Groups configured: {len(group_ids)}")

# ─── Determine posting slot ───────────────────────────────────────────────────

force_slot = os.environ.get("FORCE_SLOT", "").strip()
if force_slot.isdigit():
    slot = int(force_slot)
    print(f"Forced slot: {slot}")
else:
    utc_hour = datetime.now(timezone.utc).hour
    slot = {19: 0, 20: 1, 21: 2}.get(utc_hour, 0)
    print(f"Auto slot {slot} from UTC hour {utc_hour}")

page_index = slot % len(page_ids) if page_ids else 0
video_index = slot

if not page_ids or not page_tokens:
    print("ERROR: No FB_PAGE_IDS or page tokens set in secrets.")
    exit(1)

page_id = page_ids[page_index % len(page_ids)]
page_token = page_tokens[page_index % len(page_tokens)]
print(f"Target: Page ID {page_id} (index {page_index}), Video #{video_index}")


# ─── GitHub Release helpers ───────────────────────────────────────────────────

def gh_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }


def get_release_assets() -> list:
    """Fetch all assets from the target release."""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/tags/{RELEASE_TAG}"
    resp = requests.get(url, headers=gh_headers(), timeout=30)
    if resp.status_code == 404:
        print(f"Release {RELEASE_TAG} not found.")
        return []
    resp.raise_for_status()
    return resp.json().get("assets", [])


def download_asset(asset: dict) -> bytes:
    """Download a release asset and return its bytes."""
    # Use the browser_download_url with auth header
    resp = requests.get(
        asset["url"],
        headers={**gh_headers(), "Accept": "application/octet-stream"},
        stream=True,
        timeout=300,
    )
    resp.raise_for_status()
    return resp.content


# ─── Fetch manifest ───────────────────────────────────────────────────────────

print(f"\nFetching release assets from {RELEASE_TAG}...")
assets = get_release_assets()
if not assets:
    print("No assets found. Pipeline 2 may not have run yet.")
    exit(1)

print(f"Found {len(assets)} assets: {[a['name'] for a in assets]}")

# Find manifest
manifest_asset = next(
    (a for a in assets if "manifest" in a["name"].lower()),
    None
)
if not manifest_asset:
    print("No manifest.json in release assets.")
    exit(1)

manifest_bytes = download_asset(manifest_asset)
manifest = json.loads(manifest_bytes)
videos = manifest.get("videos", [])

print(f"Manifest: {len(videos)} videos, {manifest.get('generated', 0)} successful")

if video_index >= len(videos):
    print(f"No video at index {video_index}. Only {len(videos)} videos today.")
    exit(0)

pkg = videos[video_index]
if pkg.get("status") not in ("success", "skipped"):
    print(f"Video {video_index} failed generation. Nothing to post.")
    exit(0)

caption = pkg["caption"]
animal = pkg["animal"]
expected_filename = pkg.get("filename", "")
print(f"\nPosting: {animal}")
print(f"Caption: {caption}")


# ─── Find and download the video file ────────────────────────────────────────

video_asset = None
if expected_filename:
    video_asset = next((a for a in assets if a["name"] == expected_filename), None)

if not video_asset:
    # Fuzzy match by animal slug
    slug = animal.lower().replace(" ", "_").replace("-", "_")
    video_asset = next(
        (a for a in assets if slug in a["name"].lower() and a["name"].endswith(".mp4")),
        None
    )

if not video_asset:
    # Fall back: any MP4 at the right index
    mp4s = [a for a in assets if a["name"].endswith(".mp4")]
    if video_index < len(mp4s):
        video_asset = mp4s[video_index]

if not video_asset:
    print(f"Could not find MP4 for {animal} in release assets.")
    print(f"Available: {[a['name'] for a in assets]}")
    exit(1)

print(f"Downloading {video_asset['name']} ({video_asset['size']/1024/1024:.1f} MB)...")
video_bytes = download_asset(video_asset)
print(f"Downloaded {len(video_bytes)/1024/1024:.1f} MB")


# ─── Upload to Facebook as Reel ───────────────────────────────────────────────

print(f"\nUploading to Facebook page {page_id}...")

upload_resp = requests.post(
    f"{FB_BASE}/{page_id}/videos",
    data={
        "description": caption,
        "access_token": page_token,
    },
    files={
        "source": (video_asset["name"], io.BytesIO(video_bytes), "video/mp4")
    },
    timeout=600,  # large file upload
)

result = upload_resp.json()

if "error" in result:
    err = result["error"]
    print(f"FAILED: [{err.get('code')}] {err.get('message')}")
    # Common errors:
    # 200 = Permissions error — check token has pages_manage_posts
    # 368 = Temporary block — page posted too fast, wait 1hr
    # 100 = Invalid parameter
    exit(1)

post_id = result.get("id", "")
print(f"Posted! Post ID: {post_id}")


# ─── Cross-share to groups (max 3) ───────────────────────────────────────────

if group_ids and post_id:
    print(f"\nCross-sharing to {len(group_ids)} group(s)...")
    for gid in group_ids:
        time.sleep(5)  # rate limit buffer between shares
        share_resp = requests.post(
            f"{FB_BASE}/{gid}/feed",
            data={
                "link": f"https://www.facebook.com/{post_id}",
                "access_token": page_token,
            },
            timeout=30,
        )
        share_result = share_resp.json()
        if "id" in share_result:
            print(f"  Shared to group {gid}: {share_result['id']}")
        else:
            print(f"  Share to {gid} failed: {share_result.get('error', {}).get('message', 'Unknown')}")


# ─── Save log ────────────────────────────────────────────────────────────────

log_dir = Path("data")
log_dir.mkdir(exist_ok=True)
log_path = log_dir / f"post_log_{TODAY}.json"

existing_logs = []
if log_path.exists():
    with open(log_path) as f:
        existing_logs = json.load(f)

log_entry = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "slot": slot,
    "page_id": page_id,
    "animal": animal,
    "post_id": post_id,
    "caption": caption,
    "groups_shared": group_ids,
    "status": "success",
}
existing_logs.append(log_entry)

with open(log_path, "w") as f:
    json.dump(existing_logs, f, indent=2)

print(f"\nLogged to {log_path}")
print(f"Done. Slot {slot} complete.")
