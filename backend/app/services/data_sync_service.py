"""
SignalShift Review Sync Service
================================
Scrapes reviews directly from Google Play Store and Apple App Store
using open-source scraper libraries. Replaces the old Kaggle-based sync.

Supported sources:
  - Google Play Store  (via google-play-scraper)
  - Apple App Store    (via app-store-scraper)
"""

import os
import json
import time
import pandas as pd
from datetime import datetime, date

from .paths import processed_data_dir, raw_data_dir

# ── Optional imports (graceful degradation) ──────────────────────────────────
try:
    from google_play_scraper import Sort, reviews as gplay_reviews
    HAS_GPLAY = True
except ImportError:
    HAS_GPLAY = False

# App Store scraper uses native requests-based iTunes RSS parsing
HAS_APPSTORE = True


# ── Default app configuration ────────────────────────────────────────────────
# Netflix is the default target app; users can override via the sync endpoint.
DEFAULT_PLAYSTORE_ID = "com.netflix.mediaclient"
DEFAULT_APPSTORE_NAME = "netflix"
DEFAULT_APPSTORE_ID = 363590051  # Netflix iOS app ID


class DataSyncService:
    def __init__(self, data_dir: str | None = None):
        if data_dir is None:
            data_dir = raw_data_dir()
        self.data_dir = data_dir
        self.sync_meta_path = os.path.join(processed_data_dir(), "sync_metadata.json")

        # Ensure directories exist
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(processed_data_dir(), exist_ok=True)

    # ─────────────────────────────────────────────────────────────────────────
    # Sync metadata helpers
    # ─────────────────────────────────────────────────────────────────────────

    def get_sync_status(self):
        """Returns the last sync date and current state."""
        if os.path.exists(self.sync_meta_path):
            with open(self.sync_meta_path, "r") as f:
                return json.load(f)
        return {"last_sync": None, "status": "never_synced"}

    def _update_sync_meta(self, status="success", sources=None):
        meta = {
            "last_sync": datetime.now().isoformat(),
            "last_sync_date": str(date.today()),
            "status": status,
            "sources": sources or [],
        }
        with open(self.sync_meta_path, "w") as f:
            json.dump(meta, f)
        return meta

    def needs_sync(self):
        """Checks if a sync is needed (only once per day)."""
        status = self.get_sync_status()
        last_date = status.get("last_sync_date")
        current_date = str(date.today())
        return last_date != current_date

    # ─────────────────────────────────────────────────────────────────────────
    # Google Play Store scraper
    # ─────────────────────────────────────────────────────────────────────────

    def scrape_play_store(
        self,
        app_id: str = DEFAULT_PLAYSTORE_ID,
        months_back: int = 12,
        lang: str = "en",
        country: str = "us",
        progress_callback=None,
    ) -> pd.DataFrame:
        """
        Scrape reviews from Google Play Store.

        Returns a DataFrame with columns:
            reviewId, userName, content, score, thumbsUpCount, at, appVersion
        """
        if not HAS_GPLAY:
            raise ImportError(
                "google-play-scraper is not installed. "
                "Install it with: pip install google-play-scraper"
            )

        from datetime import datetime, timedelta
        import time
        now = datetime.now()
        cutoff_date = now - timedelta(days=30 * months_back)
        total_time_range = (now - cutoff_date).total_seconds()
        print(f"[PlayStore] Scraping reviews for {app_id} since {cutoff_date.date()}...")

        if progress_callback:
            progress_callback(5, 100, "scraping_playstore", 0)

        all_reviews = []
        continuation_token = None
        batch_size = 200  # Google Play max per request
        start_time = time.time()

        while True:
            try:
                result, continuation_token = gplay_reviews(
                    app_id,
                    lang=lang,
                    country=country,
                    sort=Sort.NEWEST,
                    count=batch_size,
                    continuation_token=continuation_token,
                )

                if not result:
                    break

                def get_naive_dt(dt_val):
                    if hasattr(dt_val, "replace"):
                        return dt_val.replace(tzinfo=None)
                    return dt_val

                valid_reviews = [r for r in result if r.get('at') and get_naive_dt(r['at']) >= cutoff_date]
                all_reviews.extend(valid_reviews)

                if result:
                    oldest_date = get_naive_dt(result[-1]['at'])
                    if oldest_date > now: oldest_date = now
                    elapsed_range = (now - oldest_date).total_seconds()
                    pct = min(max(int((elapsed_range / total_time_range) * 100), 5), 100)
                    
                    time_taken = time.time() - start_time
                    eta = int((time_taken / pct) * (100 - pct)) if pct > 0 else 0

                    if progress_callback:
                        progress_callback(pct, 100, "scraping_playstore", eta)

                print(f"[PlayStore] Fetched {len(all_reviews)} reviews so far...")

                if len(valid_reviews) < len(result):
                    # We hit reviews older than the cutoff date
                    break

                if continuation_token is None:
                    break

                # Small delay to be respectful
                time.sleep(0.3)

            except Exception as e:
                print(f"[PlayStore] Batch error: {e}")
                break

        if not all_reviews:
            return pd.DataFrame()

        # Normalize to standard schema
        df = pd.DataFrame(all_reviews)
        df = df.rename(columns={
            "reviewId": "reviewId",
            "userName": "userName",
            "content": "content",
            "score": "score",
            "thumbsUpCount": "thumbsUpCount",
            "at": "at",
            "appVersion": "appVersion",
        })

        # Keep only columns we need
        keep_cols = ["reviewId", "userName", "content", "score", "thumbsUpCount", "at", "appVersion"]
        df = df[[c for c in keep_cols if c in df.columns]]
        df["source"] = "play_store"
        df["app"] = app_id

        # Save raw CSV
        out_path = os.path.join(self.data_dir, f"{app_id}_playstore_raw.csv")
        df.to_csv(out_path, index=False)
        print(f"[PlayStore] Saved {len(df)} reviews to {out_path}")

        return df

    # ─────────────────────────────────────────────────────────────────────────
    # Apple App Store scraper
    # ─────────────────────────────────────────────────────────────────────────

    def scrape_app_store(
        self,
        app_name: str = DEFAULT_APPSTORE_NAME,
        app_id: int = DEFAULT_APPSTORE_ID,
        months_back: int = 12,
        country: str = "us",
        progress_callback=None,
    ) -> pd.DataFrame:
        """
        Scrape reviews from Apple App Store.

        Returns a DataFrame with columns:
            reviewId, userName, content, score, at, title
        """
        import requests
        from datetime import datetime, timedelta
        import time

        now = datetime.now()
        cutoff_date = now - timedelta(days=30 * months_back)
        total_time_range = (now - cutoff_date).total_seconds()
        print(f"[AppStore] Scraping reviews for {app_name} (ID: {app_id}) since {cutoff_date.date()}...")

        if progress_callback:
            progress_callback(5, 100, "scraping_appstore", 0)

        all_reviews = []
        start_time = time.time()

        for page in range(1, 11):
            url = f"https://itunes.apple.com/{country}/rss/customerreviews/id={app_id}/sortBy=mostRecent/page={page}/json"
            try:
                r = requests.get(url, timeout=10)
                if r.status_code != 200:
                    break
                data = r.json()
                entries = data.get("feed", {}).get("entry", [])
                
                if isinstance(entries, dict):
                    entries = [entries]
                    
                if not entries:
                    break

                for entry in entries:
                    if "im:rating" not in entry:
                        continue
                        
                    date_str = entry.get("updated", {}).get("label", "")
                    try:
                        dt = datetime.fromisoformat(date_str).replace(tzinfo=None)
                    except:
                        dt = now
                        
                    if dt < cutoff_date:
                        break
                        
                    all_reviews.append({
                        "reviewId": entry.get("id", {}).get("label", ""),
                        "userName": entry.get("author", {}).get("name", {}).get("label", ""),
                        "content": entry.get("content", {}).get("label", ""),
                        "score": int(entry.get("im:rating", {}).get("label", "0")),
                        "thumbsUpCount": 0,
                        "at": dt,
                        "appVersion": entry.get("im:version", {}).get("label", ""),
                        "title": entry.get("title", {}).get("label", "")
                    })
                else:
                    if all_reviews:
                        # Since Apple's RSS is capped at 10 pages (500 reviews),
                        # a time-based percentage stays at 5%. We use page-based instead.
                        pct = int((page / 10) * 100)
                        
                        time_taken = time.time() - start_time
                        eta = int((time_taken / pct) * (100 - pct)) if pct > 0 else 0

                        if progress_callback:
                            progress_callback(pct, 100, "scraping_appstore", eta)

                    time.sleep(0.8) # Slight delay to let the UI catch and display the fast App Store sync
                    continue
                
                # Inner loop broke, hit cutoff
                break
                
            except Exception as e:
                print(f"[AppStore] Page {page} error: {e}")
                break

        print(f"[AppStore] Fetched {len(all_reviews)} reviews.")

        if progress_callback:
            progress_callback(100, 100, "scraping_appstore", 0)

        if not all_reviews:
            return pd.DataFrame()

        df = pd.DataFrame(all_reviews)
        df["source"] = "app_store"
        df["app"] = app_name

        out_path = os.path.join(self.data_dir, f"{app_id}_appstore_raw.csv")
        df.to_csv(out_path, index=False)
        print(f"[AppStore] Saved {len(df)} reviews to {out_path}")

        return df

    # ─────────────────────────────────────────────────────────────────────────
    # Unified sync: scrape from both stores and merge
    # ─────────────────────────────────────────────────────────────────────────

    def sync_reviews(
        self,
        sources: list[str] | None = None,
        playstore_id: str = DEFAULT_PLAYSTORE_ID,
        appstore_name: str = DEFAULT_APPSTORE_NAME,
        appstore_id: int = DEFAULT_APPSTORE_ID,
        months_back: int = 12,
        progress_callback=None,
    ) -> str:
        """
        Scrape reviews from selected sources and merge into a single CSV.

        Args:
            sources: List of sources to scrape. Options: ["play_store", "app_store"].
                     Defaults to all available scrapers.
            months_back: Fetch reviews up to this many months back.
            progress_callback: Function(processed, total, status) for UI updates.

        Returns:
            Path to the merged CSV file.
        """
        if sources is None:
            sources = []
            if HAS_GPLAY:
                sources.append("play_store")
            if HAS_APPSTORE:
                sources.append("app_store")

        if not sources:
            raise RuntimeError(
                "No review sources available. Install at least one of: "
                "google-play-scraper, app-store-scraper"
            )

        frames = []
        active_sources = []
        total_steps = len(sources) * 100
        completed_steps = 0

        def make_sub_callback(source_idx):
            """Creates a progress callback scoped to one source."""
            def cb(processed, total, status, eta=0):
                overall = int(((source_idx * 100 + processed) / total_steps) * 100)
                if progress_callback:
                    progress_callback(overall, 100, status, eta)
            return cb

        for idx, source in enumerate(sources):
            try:
                sub_cb = make_sub_callback(idx)

                if source == "play_store":
                    df = self.scrape_play_store(
                        app_id=playstore_id,
                        months_back=months_back,
                        progress_callback=sub_cb,
                    )
                    if not df.empty:
                        frames.append(df)
                        active_sources.append("play_store")

                elif source == "app_store":
                    df = self.scrape_app_store(
                        app_name=appstore_name,
                        app_id=appstore_id,
                        months_back=months_back,
                        progress_callback=sub_cb,
                    )
                    if not df.empty:
                        frames.append(df)
                        active_sources.append("app_store")

            except Exception as e:
                print(f"[SyncService] {source} scraping failed: {e}")

        if not frames:
            self._update_sync_meta("error: no reviews scraped", active_sources)
            raise RuntimeError("No reviews were scraped from any source.")

        # Merge all sources
        merged = pd.concat(frames, ignore_index=True)

        # Drop duplicates by content text
        merged = merged.drop_duplicates(subset=["content"], keep="first")

        # Sort by date (newest first)
        if "at" in merged.columns:
            merged["at"] = pd.to_datetime(merged["at"], errors="coerce")
            merged = merged.sort_values("at", ascending=False)

        # Save merged CSV
        merged_path = os.path.join(self.data_dir, "synced_reviews.csv")
        merged.to_csv(merged_path, index=False)

        if progress_callback:
            progress_callback(100, 100, "download_complete")

        self._update_sync_meta("success", active_sources)
        print(f"[SyncService] Merged {len(merged)} reviews from {active_sources}")

        return merged_path

    def load_latest_data(self):
        """Loads the most recently synced review CSV into a DataFrame."""
        path = os.path.join(self.data_dir, "synced_reviews.csv")
        if os.path.exists(path):
            return pd.read_csv(path)
        return None
