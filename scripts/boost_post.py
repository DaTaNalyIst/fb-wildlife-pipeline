"""
Booster Script
==============
Reshares underperforming posts via a high-follower booster account.
Run manually or trigger via workflow_dispatch when a video stalls.

A "booster" is a Facebook account/page with 50,000+ followers.
Resharing from it signals the algorithm to re-push the original post.

Usage (local):
  python scripts/boost_post.py --post-id 1234567890_9876543210

Usage (GitHub Actions — workflow_dispatch):
  Trigger "Booster" workflow from Actions tab, enter the post ID.
"""
import os
import sys
import argparse
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE = "https://graph.facebook.com/v21.0"


def get_post_insights(post_id: str, page_token: str) -> dict:
    """Fetch view/reach metrics for a post to decide if it needs boosting."""
    resp = requests.get(
        f"{BASE}/{post_id}/insights",
        params={
            "metric": "post_impressions,post_video_views,post_reach",
            "access_token": page_token,
        },
        timeout=30,
    )
    data = resp.json()
    if "data" in data:
        return {item["name"]: item["values"][0]["value"] for item in data["data"]}
    return {}


def reshare_post(post_id: str, booster_token: str, message: str = "") -> dict:
    """Reshare a post from the booster account's feed."""
    post_url = f"https://www.facebook.com/{post_id.replace('_', '/posts/')}"
    resp = requests.post(
        f"{BASE}/me/feed",
        data={
            "link": post_url,
            "message": message,
            "access_token": booster_token,
        },
        timeout=30,
    )
    return resp.json()


def reshare_to_groups(post_id: str, booster_token: str, group_ids: list[str]) -> list:
    """Share into up to 3 groups from booster account. Hard cap enforced."""
    results = []
    post_url = f"https://www.facebook.com/{post_id.replace('_', '/posts/')}"

    for group_id in group_ids[:3]:  # NEVER more than 3
        resp = requests.post(
            f"{BASE}/{group_id}/feed",
            data={
                "link": post_url,
                "access_token": booster_token,
            },
            timeout=30,
        )
        result = resp.json()
        status = "✓" if "id" in result else "✗"
        print(f"  {status} Group {group_id}: {result.get('id', result.get('error', {}).get('message', 'failed'))}")
        results.append({"group_id": group_id, "result": result})

        import time; time.sleep(5)  # Rate limit buffer

    return results


def main():
    parser = argparse.ArgumentParser(description="Boost an underperforming Facebook post")
    parser.add_argument("--post-id", required=True,
                        help="Facebook post ID (format: pageID_postID)")
    parser.add_argument("--check-views", action="store_true",
                        help="Print current view count before boosting")
    parser.add_argument("--groups", default="",
                        help="Comma-separated group IDs to share into (max 3)")
    args = parser.parse_args()

    booster_token = os.environ.get("FB_BOOSTER_TOKEN", "")
    page_token = os.environ.get("FB_PAGE_TOKEN_1", booster_token)

    if not booster_token:
        print("ERROR: FB_BOOSTER_TOKEN environment variable not set.")
        print("Add it to .env locally or as a GitHub Secret for Actions.")
        sys.exit(1)

    print(f"\nBoosting post: {args.post_id}")

    # Optionally check current performance
    if args.check_views and page_token:
        print("Fetching current insights...")
        insights = get_post_insights(args.post_id, page_token)
        if insights:
            print(f"  Impressions: {insights.get('post_impressions', 'N/A')}")
            print(f"  Video views: {insights.get('post_video_views', 'N/A')}")
            print(f"  Reach:       {insights.get('post_reach', 'N/A')}")

    # Reshare from booster account's timeline
    print("\nResharing from booster account...")
    result = reshare_post(args.post_id, booster_token)

    if "id" in result:
        print(f"✓ Booster reshare posted: {result['id']}")
    else:
        err = result.get("error", {}).get("message", str(result))
        print(f"✗ Reshare failed: {err}")

    # Share into groups if specified
    if args.groups:
        group_ids = [g.strip() for g in args.groups.split(",") if g.strip()]
        print(f"\nSharing into {min(len(group_ids), 3)} group(s)...")
        reshare_to_groups(args.post_id, booster_token, group_ids)

    print("\nDone. Leave the original post running — the algorithm needs time to re-push it.")


if __name__ == "__main__":
    main()
