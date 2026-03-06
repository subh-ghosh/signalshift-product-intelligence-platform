import os
import json
import time
from datetime import datetime, date
import pandas as pd
try:
    from kaggle.api.kaggle_api_extended import KaggleApi
except ImportError:
    KaggleApi = None

class DataSyncService:
    def __init__(self, data_dir="data/raw"):
        self.data_dir = data_dir
        self.dataset_id = "ashishkumarak/netflix-reviews-playstore-daily-updated"
        self.filename = "netflix_reviews.csv"
        self.sync_meta_path = "data/sync_metadata.json"
        
        # Ensure directories exist
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs("data/processed", exist_ok=True)
        
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

    def sync_from_kaggle(self):
        """Downloads the latest CSV from Kaggle"""
        if not self.api:
            raise Exception("Kaggle API not initialized. Check credentials.")
            
        print(f"Starting Kaggle sync for {self.dataset_id}...")
        
        try:
            # Download file
            self.api.dataset_download_file(
                self.dataset_id, 
                self.filename, 
                path=self.data_dir,
                force=True, # Always get the latest
                quiet=False
            )
            
            # Kaggle downloads it as a ZIP if it's large, but dataset_download_file 
            # with specific filename usually gets the CSV directly or unzips it if needed.
            # Let's check if it needs unzipping.
            expected_path = os.path.join(self.data_dir, self.filename)
            zip_path = expected_path + ".zip"
            
            if os.path.exists(zip_path):
                import zipfile
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(self.data_dir)
                os.remove(zip_path)
                
            if not os.path.exists(expected_path):
                raise Exception(f"Failed to find downloaded file at {expected_path}")
            
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
