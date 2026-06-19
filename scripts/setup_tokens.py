"""
Token Setup Helper
==================
Run this ONCE locally to get your Facebook Page Access Tokens.
Then add them as GitHub Secrets — never commit them to the repo.

Prerequisites:
  pip install requests python-dotenv

Steps:
  1. Create a Facebook App at developers.facebook.com/apps
  2. Add product: Facebook Login for Business
  3. Go to Graph API Explorer: developers.facebook.com/tools/explorer
  4. Select your app → Generate User Access Token
  5. Add permissions: pages_manage_posts, pages_read_engagement,
     pages_show_list, publish_video
  6. Copy the short-lived token
  7. Run: python scripts/setup_tokens.py --short-token YOUR_TOKEN

Output: prints each page token + the GitHub Secret name to add it under.
"""
import os
import sys
import argparse
import requests
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE = "https://graph.facebook.com/v21.0"
APP_ID = os.getenv("FB_APP_ID", "")
APP_SECRET = os.getenv("FB_APP_SECRET", "")


def exchange_token(short_token: str) -> str:
    """Exchange short-lived (2hr) token for long-lived (60 day) token."""
    if not APP_ID or not APP_SECRET:
        print("\nERROR: Set FB_APP_ID and FB_APP_SECRET in your .env file first.")
        print("  FB_APP_ID=your_app_id")
        print("  FB_APP_SECRET=your_app_secret\n")
        sys.exit(1)

    resp = requests.get(f"{BASE}/oauth/access_token", params={
        "grant_type": "fb_exchange_token",
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "fb_exchange_token": short_token,
    }, timeout=30)

    data = resp.json()
    if "access_token" in data:
        days = data.get("expires_in", 5184000) // 86400
        print(f"✓ Long-lived user token obtained (~{days} days)")
        return data["access_token"]
    else:
        err = data.get("error", {}).get("message", "Unknown error")
        print(f"✗ Token exchange failed: {err}")
        sys.exit(1)


def fetch_pages(user_token: str) -> list:
    """Fetch all pages the user manages."""
    resp = requests.get(f"{BASE}/me/accounts", params={
        "access_token": user_token,
        "fields": "id,name,fan_count,access_token,category",
    }, timeout=30)

    data = resp.json()
    if "data" not in data:
        err = data.get("error", {}).get("message", "Unknown error")
        print(f"✗ Failed to fetch pages: {err}")
        sys.exit(1)

    return data["data"]


def inspect_token(token: str) -> dict:
    """Check token validity and permissions."""
    if not APP_ID or not APP_SECRET:
        return {}
    resp = requests.get(f"{BASE}/debug_token", params={
        "input_token": token,
        "access_token": f"{APP_ID}|{APP_SECRET}",
    }, timeout=30)
    return resp.json().get("data", {})


def main():
    parser = argparse.ArgumentParser(description="Facebook Token Setup")
    parser.add_argument("--short-token", required=True,
                        help="Short-lived user token from Graph API Explorer")
    args = parser.parse_args()

    print("\n" + "="*55)
    print("  Facebook Page Token Setup")
    print("="*55)

    # Step 1: Exchange for long-lived token
    print("\n[1/3] Exchanging for long-lived token...")
    long_token = exchange_token(args.short_token)

    # Step 2: Fetch all pages
    print("\n[2/3] Fetching your managed pages...")
    pages = fetch_pages(long_token)

    if not pages:
        print("No pages found. Make sure you manage at least one Facebook Page.")
        sys.exit(1)

    print(f"Found {len(pages)} page(s).\n")

    # Step 3: Print instructions
    print("[3/3] Add these as GitHub Secrets:")
    print("      Repo → Settings → Secrets → Actions → New repository secret\n")
    print("-"*55)

    page_ids = []
    for i, page in enumerate(pages, 1):
        secret_name = f"FB_PAGE_TOKEN_{i}"
        page_ids.append(page["id"])

        # Check if token has publish_video permission
        info = inspect_token(page["access_token"])
        scopes = info.get("scopes", [])
        has_video = "publish_video" in scopes

        print(f"\nPage {i}: {page['name']}")
        print(f"  Page ID:      {page['id']}")
        print(f"  Followers:    {page.get('fan_count', 0):,}")
        print(f"  Category:     {page.get('category', 'N/A')}")
        print(f"  Secret name:  {secret_name}")
        print(f"  Token value:  {page['access_token'][:40]}...")
        if not has_video:
            print(f"  ⚠ Missing publish_video permission — regenerate token with that scope")

    print("\n" + "-"*55)
    print("\nFB_PAGE_IDS secret value (comma-separated):")
    print(f"  {','.join(page_ids)}")

    print("\n" + "="*55)
    print("Next steps:")
    print("  1. Add each FB_PAGE_TOKEN_N secret to your GitHub repo")
    print("  2. Add FB_PAGE_IDS secret with the comma-separated IDs above")
    print("  3. Add GEMINI_API_KEY from aistudio.google.com")
    print("  4. Add GOOGLE_API_KEY (same key, for Veo3 billing)")
    print("  5. Push this repo to GitHub and enable Actions")
    print("="*55 + "\n")


if __name__ == "__main__":
    main()
