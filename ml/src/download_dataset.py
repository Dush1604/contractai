
"""
Downloads a labeled image dataset from Unsplash for the 8 project
categories, respecting rate limits and resuming safely across runs.

Unsplash's free tier is rate-limited (50 req/hour on Demo access,
higher once Production access is approved). This script is safe to
stop and restart — it tracks what's already downloaded and skips it.
"""
import os
import time
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ACCESS_KEY = os.environ["UNSPLASH_ACCESS_KEY"]
API_URL = "https://api.unsplash.com/search/photos"

# Search terms chosen to bias toward exterior/interior construction
# photos rather than generic lifestyle shots of the same word.
CATEGORIES = {
    "deck": ["wooden deck house exterior", "deck railing stairs house", "elevated wood deck construction", "deck patio house backyard", "residential deck addition",],
    "fence": "wood fence installation",
    "roofing": "roof shingles house",
    "flooring": "hardwood flooring installation",
    "drywall": ["drywall installation construction", "drywall sheets wall framing", "drywall taping mudding", "unfinished drywall interior", "drywall hanging construction worker",],
    "landscaping": "landscaping yard design",
    "kitchen": "kitchen renovation interior",
    "bathroom": "bathroom renovation interior",
}

TARGET_PER_CATEGORY = 200
DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
REQUEST_DELAY_SECONDS = 2  # conservative pacing to avoid hitting rate limits


def load_manifest(category_dir: Path) -> set[str]:
    """Returns the set of Unsplash photo IDs already downloaded for this
    category, so re-running the script doesn't re-fetch them."""
    manifest_path = category_dir / "manifest.json"
    if manifest_path.exists():
        return set(json.loads(manifest_path.read_text()))
    return set()


def save_manifest(category_dir: Path, photo_ids: set[str]) -> None:
    manifest_path = category_dir / "manifest.json"
    manifest_path.write_text(json.dumps(sorted(photo_ids)))


def download_category(category: str, query) -> None:
    queries = [query] if isinstance(query, str) else query

    category_dir = DATA_DIR / category
    category_dir.mkdir(parents=True, exist_ok=True)

    downloaded_ids = load_manifest(category_dir)
    existing_count = len(downloaded_ids)

    if existing_count >= TARGET_PER_CATEGORY:
        print(f"[{category}] already have {existing_count}/{TARGET_PER_CATEGORY}, skipping")
        return

    for q in queries:
        if len(downloaded_ids) >= TARGET_PER_CATEGORY:
            break

        print(f"[{category}] have {len(downloaded_ids)}/{TARGET_PER_CATEGORY}, trying query: '{q}'")

        page = 1
        while len(downloaded_ids) < TARGET_PER_CATEGORY:
            resp = requests.get(
                API_URL,
                params={"query": q, "page": page, "per_page": 30, "orientation": "landscape"},
                headers={"Authorization": f"Client-ID {ACCESS_KEY}"},
            )

            if resp.status_code == 403:
                print(f"[{category}] rate limited — stopping for now. Re-run script later to continue.")
                return
            resp.raise_for_status()

            results = resp.json().get("results", [])
            if not results:
                print(f"[{category}] no more results for '{q}' at page {page}, trying next query")
                break

            for photo in results:
                if len(downloaded_ids) >= TARGET_PER_CATEGORY:
                    break

                photo_id = photo["id"]
                if photo_id in downloaded_ids:
                    continue

                image_url = photo["urls"]["regular"]
                image_resp = requests.get(image_url)
                image_resp.raise_for_status()

                (category_dir / f"{photo_id}.jpg").write_bytes(image_resp.content)
                downloaded_ids.add(photo_id)
                save_manifest(category_dir, downloaded_ids)

                print(f"[{category}] {len(downloaded_ids)}/{TARGET_PER_CATEGORY} — saved {photo_id}")
                time.sleep(REQUEST_DELAY_SECONDS)

            page += 1

    print(f"[{category}] done: {len(downloaded_ids)}/{TARGET_PER_CATEGORY}")

if __name__ == "__main__":
    for category, query in CATEGORIES.items():
        download_category(category, query)
        time.sleep(REQUEST_DELAY_SECONDS)

    print("\nDataset download complete (or rate-limited — safe to re-run later).")
    