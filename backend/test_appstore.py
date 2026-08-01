from app.services.data_sync_service import DataSyncService
service = DataSyncService()
def cb(pct, tot, status, eta=0):
    print(f"[{status}] {pct}% - ETA: {eta}s")
df = service.scrape_app_store(progress_callback=cb)
print("DF length:", len(df))
