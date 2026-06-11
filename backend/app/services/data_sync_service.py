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

try:
    from app_store_scraper import AppStore
    HAS_APPSTORE = True
except ImportError:
    HAS_APPSTORE = False


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
        count: int = 2000,
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

        print(f"[PlayStore] Scraping up to {count} reviews for {app_id}...")

        if progress_callback:
            progress_callback(5, 100, "scraping_playstore")

        all_reviews = []
        continuation_token = None
        batch_size = 200  # Google Play max per request
        fetched = 0

        while fetched < count:
            try:
                result, continuation_token = gplay_reviews(
                    app_id,
                    lang=lang,
                    country=country,
                    sort=Sort.NEWEST,
                    count=min(batch_size, count - fetched),
                    continuation_token=continuation_token,
                )

                if not result:
                    break

                all_reviews.extend(result)
                fetched += len(result)

                # Progress update
                pct = min(int((fetched / count) * 90) + 5, 95)
                if progress_callback:
                    progress_callback(pct, 100, "scraping_playstore")

                print(f"[PlayStore] Fetched {fetched}/{count} reviews...")

                if continuation_token is None:
                    break

                # Small delay to be respectful
                time.sleep(0.3)

            except Exception as e:
                print(f"[PlayStore] Batch error at {fetched}: {e}")
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
        count: int = 2000,
        country: str = "us",
        progress_callback=None,
    ) -> pd.DataFrame:
        """
        Scrape reviews from Apple App Store.

        Returns a DataFrame with columns:
            reviewId, userName, content, score, at, title
        """
        if not HAS_APPSTORE:
            raise ImportError(
                "app-store-scraper is not installed. "
                "Install it with: pip install app-store-scraper"
            )

        print(f"[AppStore] Scraping up to {count} reviews for {app_name} (ID: {app_id})...")

        if progress_callback:
            progress_callback(5, 100, "scraping_appstore")

        try:
            app = AppStore(country=country, app_name=app_name, app_id=app_id)
            app.review(how_many=count)
        except Exception as e:
            print(f"[AppStore] Scraping failed: {e}")
            raise

        raw_reviews = app.reviews

        if progress_callback:
            progress_callback(90, 100, "scraping_appstore")

        if not raw_reviews:
            return pd.DataFrame()

        # Normalize to standard schema
        rows = []
        for r in raw_reviews:
            rows.append({
                "reviewId": r.get("userName", "") + "_" + str(r.get("date", "")),
                "userName": r.get("userName", ""),
                "content": r.get("review", ""),
                "score": r.get("rating", 0),
                "thumbsUpCount": 0,  # App Store doesn't expose this
                "at": r.get("date"),
                "appVersion": "",
                "title": r.get("title", ""),
            })

        df = pd.DataFrame(rows)
        df["source"] = "app_store"
        df["app"] = app_name

        # Save raw CSV
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
        count: int = 2000,
        progress_callback=None,
    ) -> str:
        """
        Scrape reviews from selected sources and merge into a single CSV.

        Args:
            sources: List of sources to scrape. Options: ["play_store", "app_store"].
                     Defaults to all available scrapers.
            count: Number of reviews to fetch per source.
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
            def cb(processed, total, status):
                overall = int(((source_idx * 100 + processed) / total_steps) * 100)
                if progress_callback:
                    progress_callback(overall, 100, status)
            return cb

        for idx, source in enumerate(sources):
            try:
                sub_cb = make_sub_callback(idx)

                if source == "play_store":
                    df = self.scrape_play_store(
                        app_id=playstore_id,
                        count=count,
                        progress_callback=sub_cb,
                    )
                    if not df.empty:
                        frames.append(df)
                        active_sources.append("play_store")

                elif source == "app_store":
                    df = self.scrape_app_store(
                        app_name=appstore_name,
                        app_id=appstore_id,
                        count=count,
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
