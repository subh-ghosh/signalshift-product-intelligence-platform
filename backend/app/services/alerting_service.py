import os
import json
import pandas as pd
from datetime import datetime

from .paths import processed_data_dir


class AlertingService:
    def __init__(self, data_dir=None):
        if data_dir is None:
            data_dir = processed_data_dir()
        self.data_dir = data_dir
        self.alert_registry = os.path.join(self.data_dir, "alerts.json")
        # Default thresholds
        self.thresholds = {
            "aspect_critical": 25.0,  # Any aspect > 25% of total mentions
            "sentiment_negative": 30.0 # Not used yet but available
        }

    def check_thresholds(self):
        try:
            aspect_df = pd.read_csv(os.path.join(self.data_dir, "aspect_analysis.csv"))
            total_mentions = aspect_df["mentions"].sum()
            
            alerts = []
            
            if total_mentions == 0:
                self._save_alerts([])
                return []

            for _, row in aspect_df.iterrows():
                percentage = (row["mentions"] / total_mentions) * 100
                if percentage >= self.thresholds["aspect_critical"]:
                    alerts.append({
                        "id": f"alert_{int(datetime.now().timestamp())}_{row['aspect']}",
                        "type": "aspect_spike",
                        "category": row["aspect"],
                        "message": f"Critical spike detected in {row['aspect']} ({percentage:.1f}% of complaints).",
                        "severity": "high",
                        "timestamp": datetime.now().isoformat()
                    })
            
            self._save_alerts(alerts)
            return alerts
            
        except Exception as e:
            print(f"Error in AlertingService: {e}")
            return []

    def _save_alerts(self, alerts):
        with open(self.alert_registry, "w") as f:
            json.dump({"alerts": alerts, "last_check": datetime.now().isoformat()}, f, indent=4)

    def get_active_alerts(self):
        if not os.path.exists(self.alert_registry):
            return []
        with open(self.alert_registry, "r") as f:
            data = json.load(f)
            return data.get("alerts", [])
