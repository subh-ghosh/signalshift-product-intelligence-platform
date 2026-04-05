import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from app.services.data_sync_service import DataSyncService

def progress(p, t, s):
    print(f"Progress: {p}/{t} - {s}")

sync = DataSyncService()
try:
    path = sync.sync_from_kaggle(progress_callback=progress)
    print(f"Sync SUCCESS! File at: {path}")
except Exception as e:
    print(f"Sync FAILED: {e}")
