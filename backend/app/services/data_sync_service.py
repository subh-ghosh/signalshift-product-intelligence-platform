import os

from .paths import processed_data_dir, raw_data_dir
import json
import time
from datetime import datetime, date
import pandas as pd
try:
    from kaggle.api.kaggle_api_extended import KaggleApi
except ImportError:
    KaggleApi = None

class DataSyncService:
    def __init__(self, data_dir: str | None = None):
        if data_dir is None:
            data_dir = raw_data_dir()
        self.data_dir = data_dir
        self.dataset_id = "ashishkumarak/netflix-reviews-playstore-daily-updated"
        self.filename = "netflix_reviews.csv"
        self.sync_meta_path = os.path.join(processed_data_dir(), "sync_metadata.json")
        
        # Ensure directories exist
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(processed_data_dir(), exist_ok=True)
        
        self.api = None
        if KaggleApi:
            try:
                self.api = KaggleApi()
                self.api.authenticate()
            except Exception as e:
                print(f"Kaggle Authentication failed: {e}")

    def get_sync_status(self):
        """Returns the last sync date and current state"""
        if os.path.exists(self.sync_meta_path):
            with open(self.sync_meta_path, "r") as f:
                return json.load(f)
        return {"last_sync": None, "status": "never_synced"}

    def _update_sync_meta(self, status="success"):
        meta = {
            "last_sync": datetime.now().isoformat(),
            "last_sync_date": str(date.today()),
            "status": status,
            "dataset": self.dataset_id
        }
        with open(self.sync_meta_path, "w") as f:
            json.dump(meta, f)
        return meta

    def needs_sync(self):
        """Checks if a sync is needed (only once per day)"""
        status = self.get_sync_status()
        last_date = status.get("last_sync_date")
        current_date = str(date.today())
        
        # If we haven't synced today, we need a sync
        return last_date != current_date

    def sync_from_kaggle(self, progress_callback=None):
        """Downloads the latest CSV from Kaggle with granular progress tracking"""
        import threading
        if KaggleApi is None:
            raise Exception(
                "Kaggle sync unavailable: python package 'kaggle' is not installed. "
                "Install it (pip install kaggle) and configure credentials (~/.kaggle/kaggle.json)."
            )
        if not self.api:
            raise Exception(
                "Kaggle API not initialized. Ensure credentials are configured (~/.kaggle/kaggle.json) "
                "and are valid."
            )
            
        print(f"Starting Kaggle sync for {self.dataset_id}...")
        
        try:
            # 1. Get expected file size for progress bar
            total_size = 37606503  # Default fallback (approx 37MB)
            try:
                files = self.api.dataset_list_files(self.dataset_id).files
                for f in files:
                    if f.name == self.filename or f.name == self.filename + ".zip":
                        total_size = f.totalBytes
                        break
            except Exception as e:
                print(f"Metadata fetch failed (using fallback size): {e}")

            expected_zip = os.path.join(self.data_dir, self.filename + ".zip")
            if os.path.exists(expected_zip):
                os.remove(expected_zip)

            # 2. Launch download in a background thread
            if progress_callback:
                progress_callback(2, 100, "downloading")

            def download_thread():
                self.api.dataset_download_file(
                    self.dataset_id, 
                    self.filename, 
                    path=self.data_dir,
                    force=True,
                    quiet=True
                )

            t = threading.Thread(target=download_thread)
            t.start()

            # 3. Proactive Progress: Climb smoothly to ~95% based on estimated time
            # For 37MB, 15-20 seconds is a reasonable estimate for most connections.
            # We climb at a decreasing rate to feel "natural".
            simulated_percent = 2
            start_monitor_time = time.time()
            
            while t.is_alive():
                elapsed = time.time() - start_monitor_time
                # Climb logic: faster at start, slower as it nears 95%
                if simulated_percent < 95:
                    # After 15 seconds, we want to be around 90%
                    increment = (95 - simulated_percent) / 30 
                    simulated_percent += max(0.2, increment)
                    
                    if progress_callback:
                        progress_callback(int(simulated_percent), 100, "downloading")
                
                time.sleep(0.3)

            t.join()
            
            if progress_callback:
                progress_callback(100, 100, "unzipping")

            # 4. Unzip if needed (Kaggle often downloads as .zip)
            expected_path = os.path.join(self.data_dir, self.filename)
            if os.path.exists(expected_zip):
                import zipfile
                with zipfile.ZipFile(expected_zip, 'r') as zip_ref:
                    zip_ref.extractall(self.data_dir)
                os.remove(expected_zip)
                
            if not os.path.exists(expected_path):
                # Sometimes it downloads the CSV directly without the .zip extension 
                # but the library usually appends .zip if it was zipped.
                if not os.path.exists(expected_path):
                    raise Exception(f"Failed to find downloaded file at {expected_path}")
            
            if progress_callback:
                progress_callback(100, 100, "download_complete")

            self._update_sync_meta("success")
            print("Kaggle sync complete.")
            return expected_path
            
        except Exception as e:
            self._update_sync_meta(f"error: {str(e)}")
            print(f"Sync failed: {e}")
            raise e

    def load_latest_data(self):
        """Loads the downloaded CSV into a DataFrame"""
        path = os.path.join(self.data_dir, self.filename)
        if os.path.exists(path):
            return pd.read_csv(path)
        return None
