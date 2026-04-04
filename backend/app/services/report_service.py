import ast
import os
import re
from datetime import datetime

import pandas as pd
from fpdf import FPDF

from app.services.ai_summary_service import ai_summary_service


class ReportService:
    def __init__(self, data_dir="data/processed"):
        self.data_dir = data_dir
        self.output_dir = "data/reports"
        os.makedirs(self.output_dir, exist_ok=True)

        self.palette = {
            "page_bg": (245, 246, 250),
            "shell_bg": (252, 252, 253),
            "surface": (255, 255, 255),
            "surface_soft": (244, 245, 248),
            "surface_muted": (238, 240, 244),
            "text_strong": (38, 44, 63),
            "text_main": (79, 86, 107),
            "text_soft": (114, 120, 140),
            "line": (221, 225, 234),
            "accent": (242, 106, 61),
            "accent_deep": (36, 43, 63),
            "accent_soft": (255, 241, 234),
            "blue": (75, 120, 180),
            "green": (49, 181, 126),
            "amber": (236, 167, 76),
            "red": (234, 91, 87),
        }

    def safe_text(self, text: str) -> str:
        if not text:
            return ""
        text = str(text)
        text = text.replace("\u2018", "'").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
        text = text.replace("\u2014", "--").replace("\u2013", "-").replace("\u2026", "...")
        text = text.replace("\u2b24", "*").replace("\u26a0", "Alert").replace("\u25b2", "^")
        text = text.replace("\u2191", "^").replace("\u2193", "v")
        return text.encode("latin-1", "ignore").decode("latin-1")

    def _load_csv(self, filename: str):
        path = os.path.join(self.data_dir, filename)
        if not os.path.exists(path):
            return None
        return pd.read_csv(path)

    def _load_reviews_df(self):
        for filename in ["uploaded_reviews.csv", "cleaned_reviews.csv"]:
            df = self._load_csv(filename)
            if df is not None and not df.empty:
                return df
        return None

    def _window_label(self, limit_months: int) -> str:
        return f"Last {limit_months} Months" if limit_months > 0 else "All Time"

    def _filter_reviews_window(self, reviews_df, limit_months: int):
        if reviews_df is None or reviews_df.empty:
            return pd.DataFrame(), pd.DataFrame()

        reviews_df = reviews_df.copy()
        if limit_months > 0 and "at" in reviews_df.columns:
            reviews_df["at"] = pd.to_datetime(reviews_df["at"], errors="coerce")
            now = pd.Timestamp.now()
            current_cutoff = now - pd.DateOffset(months=limit_months)
            previous_cutoff = now - pd.DateOffset(months=limit_months * 2)
            current_df = reviews_df[reviews_df["at"] >= current_cutoff].copy()
            previous_df = reviews_df[
                (reviews_df["at"] >= previous_cutoff) & (reviews_df["at"] < current_cutoff)
            ].copy()
            return current_df, previous_df

        return reviews_df.copy(), pd.DataFrame()

    def _filter_month_window(self, df, month_col: str, limit_months: int):
        if df is None or df.empty or limit_months <= 0 or month_col not in df.columns:
            return df
        all_months = sorted(df[month_col].dropna().astype(str).unique())
        if not all_months:
            return df
        target_months = all_months[-limit_months:]
        return df[df[month_col].astype(str).isin(target_months)].copy()

    def _parse_sample_reviews(self, raw_value):
        if raw_value is None:
            return []
        if isinstance(raw_value, list):
            values = raw_value
        else:
            try:
                values = ast.literal_eval(str(raw_value))
                if not isinstance(values, list):
                    values = [str(values)]
            except Exception:
                text = str(raw_value).strip().strip("[]")
                values = re.split(r"',\s*'|\",\s*\"|,\s*", text) if text else []
        cleaned = []
        for value in values:
            item = self.safe_text(str(value).strip(" '\"\n\t"))
            if item:
                cleaned.append(item)
        return cleaned

    def _strip_markdown(self, text: str) -> str:
        if not text:
            return ""
        cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
        cleaned = re.sub(r"\*(.*?)\*", r"\1", cleaned)
        cleaned = re.sub(r"^>\s?", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"^-\s?", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"\s{2,}", " ", cleaned)
        return self.safe_text(cleaned.strip())

    def _parse_summary(self, summary: str):
        cleaned = self.safe_text(summary or "")
        cleaned = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", "", cleaned)
        sections = []
        for block in re.split(r"\n-{3,}\n", cleaned):
            part = block.strip()
            if not part:
                continue
            lines = [line for line in part.splitlines() if line.strip()]
            heading = self._strip_markdown(re.sub(r"^###\s*", "", lines[0])) if lines else ""
            body = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
            sections.append(
                {
                    "heading": heading,
                    "body": body,
                    "plain": self._strip_markdown(body.replace("\n", " ")),
                }
            )

        focus = next((section for section in sections if section["heading"].startswith("Primary Focus")), sections[0] if sections else {})
        action = next((section for section in sections if section["heading"] == "Suggested Action"), {})
        health = next((section for section in sections if section["heading"] == "General App Health"), {})
        voice = next((section for section in sections if section["heading"] == "What Customers are Saying"), {})

        health_lines = [self._strip_markdown(line) for line in str(health.get("body", "")).splitlines() if line.strip()]
        focus_topic = str(focus.get("heading", "Executive Focus")).split(":", 1)[-1].strip() if focus else "Executive Focus"

        return {
            "focus_topic": focus_topic or "Executive Focus",
            "focus_summary": self._strip_markdown(re.sub(r"^Current Situation:\s*", "", str(focus.get("plain", "")), flags=re.IGNORECASE)),
            "action_summary": self._strip_markdown(re.sub(r"^(Action|Urgent|Standard):\s*", "", str(action.get("plain", "")), flags=re.IGNORECASE)),
            "status_line": next((line for line in health_lines if line.startswith("Status:")), "Status: Monitoring is active."),
            "watch_line": next((line for line in health_lines if line.startswith("Watch Out:")), ""),
            "category_lines": [
                line for line in health_lines
                if not line.startswith("Status:") and not line.startswith("Category Performance:") and not line.startswith("Watch Out:")
            ][:3],
            "voice_quote": self._strip_markdown(str(voice.get("body", ""))) or "No representative customer quote was available.",
        }

    def _compute_kpis(self, current_df, previous_df, ts_df, limit_months: int):
        def compute_metrics(df):
            total = len(df)
            avg_rating = round(float(df["score"].mean()), 2) if "score" in df.columns and total > 0 else None
            positive = int((df["sentiment"] == "positive").sum()) if "sentiment" in df.columns else 0
            positive_pct = round((positive / total) * 100, 1) if total > 0 else 0
            return total, avg_rating, positive_pct

        def raw_delta(current, previous):
            if previous is None or pd.isna(previous):
                return None
            return round(current - previous, 1) if isinstance(current, float) else current - previous

        def percent_delta(current, previous):
            if previous in (None, 0) or pd.isna(previous):
                return None
            return round(((current - previous) / previous) * 100, 1)

        total, avg_rating, positive_pct = compute_metrics(current_df)
        prev_total, prev_rating, prev_positive = compute_metrics(previous_df) if not previous_df.empty else (None, None, None)

        active_issues = 0
        prev_active_issues = None
        if ts_df is not None and not ts_df.empty:
            all_months = sorted(ts_df["month"].astype(str).unique())
            if limit_months > 0 and all_months:
                current_months = all_months[-limit_months:]
                previous_months = all_months[-(limit_months * 2):-limit_months] if len(all_months) >= limit_months * 2 else []
                active_issues = int(
                    ts_df[ts_df["month"].astype(str).isin(current_months)]
                    .groupby("issue_label")["mentions"]
                    .sum()
                    .gt(0)
                    .sum()
                )
                if previous_months:
                    prev_active_issues = int(
                        ts_df[ts_df["month"].astype(str).isin(previous_months)]
                        .groupby("issue_label")["mentions"]
                        .sum()
                        .gt(0)
                        .sum()
                    )
            else:
                active_issues = int(ts_df.groupby("issue_label")["mentions"].sum().gt(0).sum())

        return [
            {
                "label": "Total Feedback",
                "value": f"{total:,}",
                "sub": self._window_label(limit_months),
                "delta": percent_delta(total, prev_total),
                "delta_suffix": "%",
                "accent": "accent",
            },
            {
                "label": "Avg Rating",
                "value": f"{avg_rating}/5.0" if avg_rating is not None else "N/A",
                "sub": "Average score",
                "delta": raw_delta(avg_rating, prev_rating) if avg_rating is not None and prev_rating is not None else None,
                "delta_suffix": "",
                "accent": "amber",
            },
            {
                "label": "Customer Happiness",
                "value": f"{positive_pct}%",
                "sub": "Positive sentiment share",
                "delta": raw_delta(positive_pct, prev_positive) if prev_positive is not None else None,
                "delta_suffix": " pts",
                "accent": "green",
            },
            {
                "label": "Total Issues Found",
                "value": str(active_issues),
                "sub": "Distinct active issue clusters",
                "delta": raw_delta(active_issues, prev_active_issues) if prev_active_issues is not None else None,
                "delta_suffix": "",
                "accent": "blue",
            },
        ]

    def _build_alerts(self, ts_df, limit_months: int):
        if ts_df is None or ts_df.empty:
            return []

        metric_col = "severity_weighted_rate" if "severity_weighted_rate" in ts_df.columns else "normalized_rate" if "normalized_rate" in ts_df.columns else "mentions"
        ts_df = ts_df.copy()
        all_months = sorted(ts_df["month"].astype(str).unique())
        if len(all_months) < 2:
            return []

        current_months = all_months[-limit_months:] if limit_months > 0 else [all_months[-1]]
        previous_months = all_months[-(limit_months * 2):-limit_months] if limit_months > 0 and len(all_months) >= limit_months * 2 else [all_months[-2]]

        alerts = []
        for issue_label in sorted(ts_df["issue_label"].dropna().astype(str).unique()):
            issue_ts = ts_df[ts_df["issue_label"].astype(str) == issue_label].sort_values("month")
            current_volume = float(issue_ts[issue_ts["month"].astype(str).isin(current_months)]["mentions"].sum())
            previous_volume = float(issue_ts[issue_ts["month"].astype(str).isin(previous_months)]["mentions"].sum()) if previous_months else 0
            if current_volume <= 0:
                continue

            velocity_pct = 100.0 if previous_volume == 0 else round(((current_volume - previous_volume) / previous_volume) * 100, 1)
            values = issue_ts[metric_col].fillna(0).tolist()
            is_anomaly = False
            if len(values) >= 3:
                history = pd.Series(values[:-1], dtype="float64")
                threshold = history.mean() + (1.5 * history.std(ddof=0) if history.std(ddof=0) > 0 else 0)
                is_anomaly = values[-1] > threshold and values[-1] > 0.5

            if not is_anomaly and velocity_pct <= 10:
                continue

            severity = "CRITICAL" if (is_anomaly and velocity_pct > 40) else "HIGH" if (is_anomaly or velocity_pct > 25) else "WATCH"
            if is_anomaly and velocity_pct > 10:
                message = f"Statistically out-of-control with a +{round(velocity_pct)}% MoM spike."
            elif is_anomaly:
                message = "Statistically out-of-control versus baseline."
            else:
                message = f"Mentions increased by about {round(velocity_pct)}% compared with the previous window."

            alerts.append(
                {
                    "category": self.safe_text(issue_label),
                    "severity": severity,
                    "message": self.safe_text(message),
                    "velocity_pct": velocity_pct,
                }
            )

        severity_order = {"CRITICAL": 0, "HIGH": 1, "WATCH": 2}
        alerts.sort(key=lambda row: (severity_order.get(row["severity"], 3), -row["velocity_pct"]))
        return alerts[:4]

    def _build_aspect_summary(self, aspect_df, ts_df, limit_months: int):
        if aspect_df is None or aspect_df.empty:
            return []

        mapping = {
            "Performance/Technical": ["App Crash & Launch Failure", "Performance & Speed", "Bugs & Technical Errors"],
            "Content/Library": ["Content & Features", "Download & Offline", "Video & Streaming Playback"],
            "UI/UX Experience": ["UI & Navigation", "Notifications & Spam"],
            "Pricing/Subscription": ["Subscription & Billing", "Account & Login", "Privacy & Security"],
        }
        totals = aspect_df.groupby("aspect")["mentions"].sum().to_dict()
        aspect_rows = []

        all_months = sorted(ts_df["month"].astype(str).unique()) if ts_df is not None and not ts_df.empty and "month" in ts_df.columns else []
        current_months = all_months[-limit_months:] if limit_months > 0 and all_months else ([all_months[-1]] if all_months else [])
        previous_months = all_months[-(limit_months * 2):-limit_months] if limit_months > 0 and len(all_months) >= limit_months * 2 else []

        for aspect, mentions in sorted(totals.items(), key=lambda item: item[1], reverse=True)[:4]:
            momentum = 0.0
            priority = "Watch"
            if ts_df is not None and not ts_df.empty and current_months:
                labels = mapping.get(aspect, [])
                current_volume = float(
                    ts_df[
                        ts_df["issue_label"].astype(str).isin(labels)
                        & ts_df["month"].astype(str).isin(current_months)
                    ]["mentions"].sum()
                )
                previous_volume = float(
                    ts_df[
                        ts_df["issue_label"].astype(str).isin(labels)
                        & ts_df["month"].astype(str).isin(previous_months)
                    ]["mentions"].sum()
                ) if previous_months else 0
                if previous_volume > 0:
                    momentum = round(((current_volume - previous_volume) / previous_volume) * 100, 1)
            share = (mentions / max(sum(totals.values()), 1)) * 100
            if share >= 25 or momentum >= 20:
                priority = "Critical"
            elif share >= 14 or momentum > 0:
                priority = "Active"

            aspect_rows.append(
                {
                    "aspect": self.safe_text(aspect),
                    "mentions": int(mentions),
                    "momentum": momentum,
                    "priority": priority,
                }
            )
        return aspect_rows

    def _build_stability_summary(self, topic_df, ts_df):
        if topic_df is None or topic_df.empty or ts_df is None or ts_df.empty:
            return None

        severity_map = topic_df.set_index("label")["avg_severity"].to_dict() if "label" in topic_df.columns else {}
        stability_rows = []
        for month in sorted(ts_df["month"].astype(str).unique()):
            month_df = ts_df[ts_df["month"].astype(str) == month]
            total_volume = month_df["mentions"].sum()
            if total_volume <= 0:
                continue
            weighted_sum = 0.0
            for _, row in month_df.iterrows():
                weighted_sum += float(row["mentions"]) * float(severity_map.get(row.get("issue_label"), 2.0))
            score = weighted_sum / total_volume
            stability_rows.append({"month": month, "score": score})

        if not stability_rows:
            return None

        stability_df = pd.DataFrame(stability_rows)
        stability_df["rolling_mean"] = stability_df["score"].rolling(window=3, min_periods=1).mean()
        stability_df["rolling_std"] = stability_df["score"].rolling(window=3, min_periods=1).std().fillna(0)
        stability_df["upper_band"] = stability_df["rolling_mean"] + (1.5 * stability_df["rolling_std"])
        stability_df["lower_band"] = stability_df["rolling_mean"] - (1.5 * stability_df["rolling_std"])
        stability_df["is_volatile"] = (
            (stability_df["score"] > stability_df["upper_band"]) |
            (stability_df["score"] < stability_df["lower_band"])
        )

        latest = stability_df.iloc[-1]
        volatility_count = int(stability_df["is_volatile"].sum())
        return {
            "baseline": round(float(latest["score"]), 2),
            "volatility_count": volatility_count,
            "status": "High volatility detected" if bool(latest["is_volatile"]) else "Stable emotional range",
            "latest_month": self.safe_text(str(latest["month"])),
            "volatile_months": [self.safe_text(str(row["month"])) for _, row in stability_df[stability_df["is_volatile"]].iterrows()],
        }

    def _build_trending_summary(self, ts_df, limit_months: int):
        if ts_df is None or ts_df.empty:
            return []

        metric_col = "severity_weighted_rate" if "severity_weighted_rate" in ts_df.columns else "normalized_rate" if "normalized_rate" in ts_df.columns else "mentions"
        all_months = sorted(ts_df["month"].astype(str).unique())
        if len(all_months) < 2:
            return []

        first_month = all_months[-limit_months] if limit_months > 0 and len(all_months) >= limit_months else all_months[0]
        last_month = all_months[-1]
        rows = []
        for issue_label in sorted(ts_df["issue_label"].dropna().astype(str).unique()):
            issue_df = ts_df[ts_df["issue_label"].astype(str) == issue_label]
            total_mentions = issue_df["mentions"].sum()
            if total_mentions < 15:
                continue
            start_value = issue_df[issue_df["month"].astype(str) == first_month][metric_col].max()
            end_value = issue_df[issue_df["month"].astype(str) == last_month][metric_col].max()
            start_value = 0 if pd.isna(start_value) else float(start_value)
            end_value = 0 if pd.isna(end_value) else float(end_value)
            if start_value == 0 and end_value == 0:
                continue
            pct_change = 100.0 if start_value == 0 else round(((end_value - start_value) / start_value) * 100, 1)
            rows.append(
                {
                    "label": self.safe_text(issue_label),
                    "change_pct": pct_change,
                    "direction": "Rising" if pct_change > 0 else "Cooling",
                }
            )

        rows.sort(key=lambda row: abs(row["change_pct"]), reverse=True)
        return rows[:4]

    def _build_sentiment_breakdown(self, current_df, previous_df):
        if current_df is None or current_df.empty or "sentiment" not in current_df.columns:
            return None

        positive = int((current_df["sentiment"] == "positive").sum())
        negative = int((current_df["sentiment"] == "negative").sum())
        total = positive + negative
        positive_pct = round((positive / total) * 100, 1) if total > 0 else 0.0
        negative_pct = round((negative / total) * 100, 1) if total > 0 else 0.0

        momentum = 0.0
        if previous_df is not None and not previous_df.empty and "sentiment" in previous_df.columns:
            prev_positive = int((previous_df["sentiment"] == "positive").sum())
            prev_negative = int((previous_df["sentiment"] == "negative").sum())
            prev_total = prev_positive + prev_negative
            prev_positive_pct = round((prev_positive / prev_total) * 100, 1) if prev_total > 0 else 0.0
            momentum = round(positive_pct - prev_positive_pct, 1)

        return {
            "positive": positive,
            "negative": negative,
            "positive_pct": positive_pct,
            "negative_pct": negative_pct,
            "momentum": momentum,
        }

    def _build_ticker_items(self, reviews_df):
        if reviews_df is None or reviews_df.empty:
            return []

        df = reviews_df.copy()
        if "at" in df.columns:
            df["at"] = pd.to_datetime(df["at"], errors="coerce")
            df = df.sort_values("at", ascending=False)
        else:
            df = df.iloc[::-1]

        items = []
        for _, row in df.head(15).iterrows():
            text = self.safe_text(str(row.get("content", row.get("cleaned_content", ""))))
            if len(text) < 30:
                continue
            sentiment = self.safe_text(str(row.get("sentiment", "neutral")).upper())
            stamp = ""
            if pd.notna(row.get("at")):
                try:
                    stamp = pd.to_datetime(row.get("at")).strftime("%b %d")
                except Exception:
                    stamp = ""
            items.append({"sentiment": sentiment, "stamp": stamp, "text": text[:84]})
            if len(items) == 4:
                break
        return items

    def _ensure_space(self, pdf: FPDF, required_height: float):
        if pdf.get_y() + required_height > 272:
            pdf.add_page()
            self._draw_page_shell(pdf)

    def _set_fill(self, pdf: FPDF, key: str):
        pdf.set_fill_color(*self.palette[key])

    def _set_text(self, pdf: FPDF, key: str):
        pdf.set_text_color(*self.palette[key])

    def _set_draw(self, pdf: FPDF, key: str):
        pdf.set_draw_color(*self.palette[key])

    def _fit_text(self, pdf: FPDF, text: str, max_width: float, max_lines: int = 2):
        safe = self.safe_text(text)
        if not safe:
            return ""

        words = safe.split()
        if not words:
            return ""

        lines = []
        current = ""
        for word in words:
            trial = word if not current else f"{current} {word}"
            if pdf.get_string_width(trial) <= max_width:
                current = trial
                continue

            if current:
                lines.append(current)
            else:
                clipped = word
                while clipped and pdf.get_string_width(f"{clipped}...") > max_width:
                    clipped = clipped[:-1]
                lines.append(f"{clipped}..." if clipped and clipped != word else word)
            current = word if current else ""

            if len(lines) >= max_lines:
                break

        if len(lines) < max_lines and current:
            lines.append(current)

        remaining_words = " ".join(words)
        used_words = " ".join(lines)
        if len(lines) > max_lines:
            lines = lines[:max_lines]
        elif used_words.strip() != remaining_words.strip():
            last = lines[max_lines - 1] if len(lines) >= max_lines else lines[-1]
            trimmed = last.rstrip(". ")
            while trimmed and pdf.get_string_width(f"{trimmed}...") > max_width:
                trimmed = trimmed[:-1]
            if trimmed:
                if len(lines) >= max_lines:
                    lines[max_lines - 1] = f"{trimmed}..."
                else:
                    lines[-1] = f"{trimmed}..."

        return "\n".join(lines[:max_lines])

    def _draw_page_shell(self, pdf: FPDF):
        pdf.set_auto_page_break(False)
        pdf.set_margins(14, 14, 14)
        self._set_fill(pdf, "page_bg")
        pdf.rect(0, 0, 210, 297, "F")
        self._set_fill(pdf, "shell_bg")
        pdf.rect(7, 7, 196, 283, "F")
        self._set_draw(pdf, "line")
        pdf.rect(7, 7, 196, 283)
        pdf.set_xy(14, 14)

    def _draw_tag(self, pdf: FPDF, x: float, y: float, text: str, fill_key="accent_soft", text_key="accent"):
        pdf.set_font("Helvetica", "B", 7)
        width = max(24, min(58, pdf.get_string_width(text) + 8))
        self._set_fill(pdf, fill_key)
        pdf.rect(x, y, width, 7, "F")
        pdf.set_xy(x, y + 1.8)
        self._set_text(pdf, text_key)
        pdf.cell(width, 3, self.safe_text(text.upper()), align="C")
        return width

    def _draw_card(
        self,
        pdf: FPDF,
        x: float,
        y: float,
        w: float,
        h: float,
        title: str = "",
        subtitle: str = "",
        fill_key="surface",
        subtitle_lines: int = 3,
    ):
        self._set_fill(pdf, fill_key)
        pdf.rect(x, y, w, h, "F")
        self._set_draw(pdf, "line")
        pdf.rect(x, y, w, h)
        content_y = y + 4
        if title:
            pdf.set_xy(x + 4, content_y)
            pdf.set_font("Helvetica", "B", 12)
            self._set_text(pdf, "text_strong")
            pdf.cell(w - 8, 5, self._fit_text(pdf, title, w - 8, 1))
            content_y += 6
        if subtitle:
            pdf.set_xy(x + 4, content_y)
            pdf.set_font("Helvetica", "", 8)
            self._set_text(pdf, "text_soft")
            pdf.multi_cell(w - 8, 4, self._fit_text(pdf, subtitle, w - 8, subtitle_lines))
            content_y = pdf.get_y()
        return content_y + 2

    def _draw_section_header(self, pdf: FPDF, eyebrow: str, title: str, subtitle: str = ""):
        self._set_text(pdf, "accent")
        pdf.set_font("Helvetica", "B", 8)
        pdf.cell(0, 4, self.safe_text(eyebrow.upper()), ln=True)
        pdf.set_font("Helvetica", "B", 18)
        self._set_text(pdf, "text_strong")
        pdf.cell(0, 9, self.safe_text(title), ln=True)
        if subtitle:
            pdf.set_font("Helvetica", "", 9)
            self._set_text(pdf, "text_soft")
            pdf.multi_cell(0, 4.8, self.safe_text(subtitle))
        pdf.ln(3)

    def _draw_hero(self, pdf: FPDF, window_label: str, generated_at: str, ticker_items):
        x, y, w, h = 14, 14, 182, 34
        self._set_fill(pdf, "accent_deep")
        pdf.rect(x, y, w, h, "F")
        self._set_fill(pdf, "accent")
        pdf.rect(x + 118, y, 64, h, "F")

        pdf.set_xy(x + 6, y + 6)
        self._draw_tag(pdf, x + 6, y + 4, "Executive Workspace", fill_key="surface_soft", text_key="accent_deep")
        pdf.set_xy(x + 6, y + 14)
        pdf.set_font("Helvetica", "B", 22)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(105, 8, "SignalShift Insights")
        pdf.set_xy(x + 6, y + 23)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(102, 5, self.safe_text(f"Dashboard report | {window_label} | Generated {generated_at}"))

        pdf.set_xy(x + 123, y + 7)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(50, 5, "LIVE FEEDBACK")
        pdf.set_xy(x + 123, y + 14)
        pdf.set_font("Helvetica", "", 8)
        ticker_line = " | ".join(
            [
                f"{item['sentiment'][:4]} {item['stamp']}: {item['text'][:18]}..."
                for item in ticker_items[:3]
            ]
        ) or "No recent review ticker available."
        pdf.multi_cell(52, 4.1, self.safe_text(ticker_line))

    def _draw_kpis(self, pdf: FPDF, kpis):
        x_positions = [14, 60.5, 107, 153.5]
        y = pdf.get_y()
        card_width = 42.5
        card_height = 23
        accent_map = {
            "accent": "accent",
            "amber": "amber",
            "green": "green",
            "blue": "blue",
        }

        for x, item in zip(x_positions, kpis):
            self._draw_card(pdf, x, y, card_width, card_height)
            color_key = accent_map.get(item["accent"], "accent")
            self._set_fill(pdf, color_key)
            pdf.rect(x + 3, y + 3, 8, 8, "F")
            pdf.set_xy(x + 14, y + 4)
            pdf.set_font("Helvetica", "B", 7.5)
            self._set_text(pdf, "text_soft")
            pdf.cell(card_width - 17, 4, self.safe_text(item["label"].upper()))

            pdf.set_xy(x + 3, y + 11)
            pdf.set_font("Helvetica", "B", 15)
            self._set_text(pdf, "text_strong")
            pdf.cell(card_width - 6, 6, self.safe_text(item["value"]))

            pdf.set_xy(x + 3, y + 18)
            pdf.set_font("Helvetica", "", 7.5)
            self._set_text(pdf, "text_soft")
            pdf.cell(25, 3, self.safe_text(item["sub"]))

            if item["delta"] is not None:
                delta = item["delta"]
                direction = "+" if delta > 0 else "-"
                delta_text = f"{direction}{abs(delta)}{item['delta_suffix']}"
                self._set_text(pdf, "green" if delta > 0 else "red")
                pdf.set_xy(x + 26, y + 18)
                pdf.cell(13, 3, self.safe_text(delta_text), align="R")

        pdf.set_y(y + card_height + 6)

    def _draw_summary(self, pdf: FPDF, summary_model):
        y = pdf.get_y()
        self._draw_card(pdf, 14, y, 114, 48, title=summary_model["focus_topic"], subtitle=summary_model["focus_summary"], subtitle_lines=6)
        self._draw_tag(pdf, 103, y + 4, "Analysis Overview")

        self._draw_card(pdf, 132, y, 64, 23, title="Recommended next step", subtitle=summary_model["action_summary"], fill_key="accent_soft", subtitle_lines=3)
        self._draw_card(pdf, 132, y + 25, 64, 23, title="Current operating context", subtitle=summary_model["status_line"], fill_key="surface_soft", subtitle_lines=1)

        pdf.set_y(y + 52)
        self._draw_card(pdf, 14, pdf.get_y(), 182, 20, title="Representative feedback", subtitle=summary_model["voice_quote"], fill_key="surface_soft", subtitle_lines=2)
        pdf.set_y(y + 75)

    def _draw_problem_landscape(self, pdf: FPDF, alerts, top_issues, aspects):
        self._ensure_space(pdf, 74)
        self._draw_section_header(pdf, "Problem Landscape", "Problem Landscape", "Top Issues, Alerts, and Aspect Map.")
        y = pdf.get_y()
        inner_y = self._draw_card(pdf, 14, y, 90, 55, title="Top Issues", subtitle="Top validated issues in the active dashboard window.", subtitle_lines=1)
        for index, issue in enumerate(top_issues[:3], start=1):
            pdf.set_xy(18, inner_y)
            pdf.set_font("Helvetica", "B", 10)
            self._set_text(pdf, "text_strong")
            pdf.cell(70, 5, self._fit_text(pdf, f"{index:02d} {issue['label']}", 70, 1))
            pdf.set_xy(18, inner_y + 5)
            pdf.set_font("Helvetica", "", 8)
            self._set_text(pdf, "text_soft")
            pdf.multi_cell(
                80,
                4,
                self._fit_text(pdf, f"{issue['mentions']:,} mentions | severity {issue['severity']}/5.0 | {issue['evidence']}", 80, 2)
            )
            inner_y = pdf.get_y() + 2

        alert_y = self._draw_card(pdf, 108, y, 88, 27, title="Alerts", subtitle="Same urgency ranking as the dashboard alerts panel.", subtitle_lines=1)
        for alert in alerts[:1]:
            tone = "accent" if alert["severity"] == "CRITICAL" else "amber" if alert["severity"] == "HIGH" else "blue"
            self._draw_tag(pdf, 112, alert_y, alert["severity"], fill_key="surface_soft", text_key=tone)
            pdf.set_xy(139, alert_y + 1)
            pdf.set_font("Helvetica", "B", 9)
            self._set_text(pdf, "text_strong")
            pdf.cell(52, 4, self._fit_text(pdf, alert["category"], 52, 1))
            pdf.set_xy(112, alert_y + 8)
            pdf.set_font("Helvetica", "", 7.5)
            self._set_text(pdf, "text_soft")
            pdf.multi_cell(78, 3.8, self._fit_text(pdf, alert["message"], 78, 2))
            alert_y = pdf.get_y() + 1

        aspect_y = self._draw_card(pdf, 108, y + 30, 88, 25, title="Aspect Map", subtitle="Business areas drawing the most conversation.", subtitle_lines=1)
        for aspect in aspects[:3]:
            priority_key = "accent" if aspect["priority"] == "Critical" else "amber" if aspect["priority"] == "Active" else "blue"
            pdf.set_xy(112, aspect_y)
            pdf.set_font("Helvetica", "B", 8.5)
            self._set_text(pdf, "text_strong")
            pdf.cell(40, 4, self._fit_text(pdf, aspect["aspect"], 40, 1))
            self._set_text(pdf, priority_key)
            pdf.cell(16, 4, self.safe_text(aspect["priority"]), align="R")
            pdf.set_xy(112, aspect_y + 4)
            self._set_text(pdf, "text_soft")
            pdf.set_font("Helvetica", "", 7.5)
            momentum_prefix = "+" if aspect["momentum"] > 0 else ""
            pdf.cell(70, 3.8, self.safe_text(f"{aspect['mentions']} mentions | momentum {momentum_prefix}{aspect['momentum']}%"))
            aspect_y += 7.5

        pdf.set_y(y + 61)

    def _draw_health_and_signals(self, pdf: FPDF, stability, trending, quality_df):
        self._ensure_space(pdf, 56)
        self._draw_section_header(pdf, "Sentiment Health", "Sentiment Health", "Sentiment Health and Signals & Shifts.")
        y = pdf.get_y()

        stability_subtitle = "No stability data available."
        if stability:
            stability_subtitle = (
                f"Baseline {stability['baseline']}/5.0 | {stability['status']} | "
                f"{stability['volatility_count']} volatility events detected in the sampled history."
            )
        self._draw_card(pdf, 14, y, 88, 34, title="Sentiment Health", subtitle=stability_subtitle, subtitle_lines=3)

        quality_subtitle = "Model quality metrics were not available."
        if quality_df is not None and not quality_df.empty:
            row = quality_df.iloc[0]
            quality_subtitle = (
                f"Silhouette score {round(float(row.get('value', 0)), 4)} | "
                f"{int(row.get('n_categories', 0))} active categories | "
                f"confidence {row.get('threshold_confidence', 0.3)}"
            )
        trend_y = self._draw_card(pdf, 106, y, 90, 34, title="Signals & Shifts", subtitle=quality_subtitle, fill_key="surface_soft", subtitle_lines=2)
        for row in trending[:3]:
            color_key = "accent" if row["direction"] == "Rising" else "green"
            pdf.set_xy(110, trend_y)
            pdf.set_font("Helvetica", "B", 8.5)
            self._set_text(pdf, "text_strong")
            pdf.cell(46, 4, self._fit_text(pdf, row["label"], 46, 1))
            self._set_text(pdf, color_key)
            pdf.cell(30, 4, self.safe_text(f"{row['direction']} {abs(round(row['change_pct']))}%"), align="R")
            trend_y += 6.5

        pdf.set_y(y + 38)

    def _draw_watchlists(self, pdf: FPDF, emerging_df, drift_df):
        self._ensure_space(pdf, 72)
        self._draw_section_header(pdf, "Watch Lists", "Watch and New Issues", "Watch and New Issues.")
        y = pdf.get_y()
        item_y = self._draw_card(pdf, 14, y, 88, 48, title="Watch", subtitle="New clusters gaining enough signal to track.", subtitle_lines=1)
        drift_y = self._draw_card(pdf, 106, y, 90, 48, title="New Issues", subtitle="Categories whose language is shifting fast enough to warrant review.", subtitle_lines=1)

        emerging_rows = []
        if emerging_df is not None and not emerging_df.empty:
            flagged = emerging_df[emerging_df["is_flagged"] == True].sort_values("estimated_volume", ascending=False).head(3)
            for _, row in flagged.iterrows():
                emerging_rows.append(
                    {
                        "label": self.safe_text(str(row.get("label", f"Cluster {row.get('cluster_id', '')}")).replace(" (Proto)", "")),
                        "volume": int(row.get("estimated_volume", 0)),
                        "momentum": round(float(row.get("momentum_pct", 0)), 1),
                    }
                )

        drift_rows = []
        if drift_df is not None and not drift_df.empty:
            drift_df = drift_df.copy()
            grouped = (
                drift_df.groupby("category")
                .agg({"drift_score": "mean", "shifting_terms": "last"})
                .reset_index()
                .sort_values("drift_score", ascending=False)
                .head(3)
            )
            for _, row in grouped.iterrows():
                drift_rows.append(
                    {
                        "category": self.safe_text(row["category"]),
                        "score": round(float(row["drift_score"]), 2),
                        "terms": self.safe_text(str(row.get("shifting_terms", "stable"))),
                    }
                )

        if emerging_rows:
            for row in emerging_rows:
                pdf.set_xy(18, item_y)
                pdf.set_font("Helvetica", "B", 8.5)
                self._set_text(pdf, "text_strong")
                pdf.cell(55, 4, self._fit_text(pdf, row["label"], 55, 1))
                self._set_text(pdf, "accent" if row["momentum"] > 0 else "blue")
                momentum_prefix = "+" if row["momentum"] > 0 else ""
                pdf.cell(20, 4, self.safe_text(f"{momentum_prefix}{row['momentum']}%"), align="R")
                pdf.set_xy(18, item_y + 4)
                self._set_text(pdf, "text_soft")
                pdf.set_font("Helvetica", "", 7.5)
                pdf.cell(65, 3.8, self.safe_text(f"{row['volume']:,} reviews estimated"))
                item_y += 10
        else:
            pdf.set_xy(18, item_y)
            pdf.set_font("Helvetica", "", 8)
            self._set_text(pdf, "text_soft")
            pdf.multi_cell(76, 4, "No newly surfacing complaint clusters were strong enough to flag in this window.")

        if drift_rows:
            for row in drift_rows:
                pdf.set_xy(110, drift_y)
                pdf.set_font("Helvetica", "B", 8.5)
                self._set_text(pdf, "text_strong")
                pdf.cell(48, 4, self._fit_text(pdf, row["category"], 48, 1))
                self._set_text(pdf, "accent" if row["score"] > 0.18 else "amber" if row["score"] > 0.14 else "blue")
                pdf.cell(18, 4, self.safe_text(f"{row['score']:.2f}"), align="R")
                pdf.set_xy(110, drift_y + 4)
                self._set_text(pdf, "text_soft")
                pdf.set_font("Helvetica", "", 7.5)
                pdf.multi_cell(76, 3.8, self._fit_text(pdf, f"Now showing up as: {row['terms']}", 76, 2))
                drift_y += 10
        else:
            pdf.set_xy(110, drift_y)
            pdf.set_font("Helvetica", "", 8)
            self._set_text(pdf, "text_soft")
            pdf.multi_cell(78, 4, "Complaint language is stable right now, so no hidden issue shifts are standing out.")

        pdf.set_y(y + 52)

    def _draw_detail_list(self, pdf: FPDF, x: float, y: float, w: float, title: str, rows, row_renderer):
        self._draw_card(pdf, x, y, w, 10, title=title, subtitle_lines=0)
        current_y = y + 12
        for row in rows:
            current_y = row_renderer(pdf, x + 4, current_y, w - 8, row)
            current_y += 2
        return current_y

    def _draw_dashboard_detail_pages(self, pdf: FPDF, ticker_items, top_issues, alerts, aspects, sentiment_breakdown, stability, trending, emerging_rows, drift_rows):
        pdf.add_page()
        self._draw_page_shell(pdf)
        self._draw_section_header(pdf, "Dashboard Detail", "Live Feedback and Top Issues", "Expanded dashboard coverage with consistent spacing.")
        y = pdf.get_y()

        ticker_y = self._draw_card(pdf, 14, y, 182, 28, title="Live Feedback", subtitle="Recent items from the ticker panel.", subtitle_lines=1)
        for item in ticker_items[:4]:
            pdf.set_xy(18, ticker_y)
            pdf.set_font("Helvetica", "B", 7.5)
            self._set_text(pdf, "accent" if item["sentiment"].startswith("NEG") else "green" if item["sentiment"].startswith("POS") else "blue")
            pdf.cell(24, 3.8, self._fit_text(pdf, f"{item['sentiment']} {item['stamp']}", 24, 1))
            pdf.set_xy(43, ticker_y)
            pdf.set_font("Helvetica", "", 7.5)
            self._set_text(pdf, "text_soft")
            pdf.cell(145, 3.8, self._fit_text(pdf, item["text"], 145, 1))
            ticker_y += 5.8

        y += 34
        issue_y = self._draw_card(pdf, 14, y, 182, 138, title="Top Issues", subtitle="Expanded view of the dashboard issue list.", subtitle_lines=1)
        for issue in top_issues[:6]:
            pdf.set_xy(18, issue_y)
            pdf.set_font("Helvetica", "B", 9)
            self._set_text(pdf, "text_strong")
            pdf.cell(118, 4.2, self._fit_text(pdf, issue["label"], 118, 1))
            pdf.set_xy(150, issue_y)
            self._set_text(pdf, "accent_deep")
            pdf.cell(40, 4.2, self._fit_text(pdf, f"{issue['mentions']:,} mentions", 40, 1), align="R")
            pdf.set_xy(18, issue_y + 4)
            pdf.set_font("Helvetica", "", 7.2)
            self._set_text(pdf, "text_soft")
            pdf.multi_cell(172, 3.8, self._fit_text(pdf, f"Severity {issue['severity']}/5.0 | {issue['evidence']}", 172, 2))
            issue_y = pdf.get_y() + 4

        pdf.add_page()
        self._draw_page_shell(pdf)
        self._draw_section_header(pdf, "Dashboard Detail", "Alerts and Aspect Map", "Expanded dashboard coverage with consistent spacing.")
        y = pdf.get_y()

        alert_y = self._draw_card(pdf, 14, y, 88, 96, title="Alerts", subtitle="Expanded alert coverage from the dashboard.", subtitle_lines=1)
        for alert in alerts[:5]:
            pdf.set_xy(18, alert_y)
            pdf.set_font("Helvetica", "B", 7.5)
            tone = "accent" if alert["severity"] == "CRITICAL" else "amber" if alert["severity"] == "HIGH" else "blue"
            self._set_text(pdf, tone)
            pdf.cell(18, 3.8, self._fit_text(pdf, alert["severity"], 18, 1))
            pdf.set_xy(38, alert_y)
            pdf.set_font("Helvetica", "B", 8)
            self._set_text(pdf, "text_strong")
            pdf.cell(58, 3.8, self._fit_text(pdf, alert["category"], 58, 1))
            pdf.set_xy(18, alert_y + 4)
            pdf.set_font("Helvetica", "", 7.2)
            self._set_text(pdf, "text_soft")
            pdf.multi_cell(78, 3.5, self._fit_text(pdf, alert["message"], 78, 2))
            alert_y = pdf.get_y() + 3

        aspect_y = self._draw_card(pdf, 108, y, 88, 96, title="Aspect Map", subtitle="Expanded aspect panel coverage.", subtitle_lines=1)
        for aspect in aspects[:4]:
            pdf.set_xy(112, aspect_y)
            pdf.set_font("Helvetica", "B", 8.6)
            self._set_text(pdf, "text_strong")
            pdf.cell(46, 4.2, self._fit_text(pdf, aspect["aspect"], 46, 1))
            tone = "accent" if aspect["priority"] == "Critical" else "amber" if aspect["priority"] == "Active" else "blue"
            self._set_text(pdf, tone)
            pdf.cell(18, 4.2, self._fit_text(pdf, aspect["priority"], 18, 1), align="R")
            pdf.set_xy(112, aspect_y + 4.4)
            self._set_text(pdf, "text_soft")
            pdf.set_font("Helvetica", "", 7.2)
            pdf.cell(76, 3.5, self._fit_text(pdf, f"{aspect['mentions']} mentions | momentum {aspect['momentum']}%", 76, 1))
            aspect_y += 10

        next_y = y + 102
        sentiment_subtitle = "No sentiment data available."
        if sentiment_breakdown:
            sentiment_subtitle = (
                f"{sentiment_breakdown['positive_pct']}% positive | {sentiment_breakdown['negative_pct']}% negative | "
                f"momentum {sentiment_breakdown['momentum']} pts"
            )
        self._draw_card(pdf, 14, next_y, 88, 28, title="Sentiment Health", subtitle=sentiment_subtitle, subtitle_lines=3)

        stability_subtitle = "No stability data available."
        if stability:
            volatile_text = ", ".join(stability["volatile_months"][:3]) if stability["volatile_months"] else "none"
            stability_subtitle = (
                f"Baseline {stability['baseline']}/5.0 | latest {stability['latest_month']} | "
                f"volatile months: {volatile_text}"
            )
        self._draw_card(pdf, 108, next_y, 88, 28, title="Stability", subtitle=stability_subtitle, subtitle_lines=3)

        pdf.add_page()
        self._draw_page_shell(pdf)
        self._draw_section_header(pdf, "Dashboard Detail", "Signals, Watch, and New Issues", "Expanded dashboard coverage with consistent spacing.")
        y = pdf.get_y()

        trend_y = self._draw_card(pdf, 14, y, 182, 44, title="Signals & Shifts", subtitle="Trending topics from the dashboard timeline.", subtitle_lines=1)
        for row in trending[:4]:
            pdf.set_xy(18, trend_y)
            pdf.set_font("Helvetica", "B", 8.8)
            self._set_text(pdf, "text_strong")
            pdf.cell(116, 4.2, self._fit_text(pdf, row["label"], 116, 1))
            tone = "accent" if row["direction"] == "Rising" else "green"
            self._set_text(pdf, tone)
            pdf.cell(40, 4.2, self._fit_text(pdf, f"{row['direction']} {abs(round(row['change_pct']))}%", 40, 1), align="R")
            trend_y += 6.5

        emerging_y = self._draw_card(pdf, 14, y + 50, 88, 104, title="Watch", subtitle="Expanded emerging issues panel.", subtitle_lines=1)
        for row in emerging_rows[:5]:
            pdf.set_xy(18, emerging_y)
            pdf.set_font("Helvetica", "B", 8.5)
            self._set_text(pdf, "text_strong")
            pdf.cell(54, 4, self._fit_text(pdf, row["label"], 54, 1))
            self._set_text(pdf, "accent" if row["momentum"] > 0 else "blue")
            pdf.cell(18, 4, self._fit_text(pdf, f"{row['momentum']}%", 18, 1), align="R")
            pdf.set_xy(18, emerging_y + 4)
            self._set_text(pdf, "text_soft")
            pdf.set_font("Helvetica", "", 7.2)
            pdf.multi_cell(74, 3.4, self._fit_text(pdf, f"{row['volume']:,} reviews estimated", 74, 1))
            emerging_y = pdf.get_y() + 3

        drift_y = self._draw_card(pdf, 108, y + 50, 88, 104, title="New Issues", subtitle="Expanded semantic drift panel.", subtitle_lines=1)
        for row in drift_rows[:5]:
            pdf.set_xy(112, drift_y)
            pdf.set_font("Helvetica", "B", 8.5)
            self._set_text(pdf, "text_strong")
            pdf.cell(48, 4, self._fit_text(pdf, row["category"], 48, 1))
            self._set_text(pdf, "accent" if row["score"] > 0.18 else "amber" if row["score"] > 0.14 else "blue")
            pdf.cell(18, 4, self._fit_text(pdf, f"{row['score']:.2f}", 18, 1), align="R")
            pdf.set_xy(112, drift_y + 4)
            self._set_text(pdf, "text_soft")
            pdf.set_font("Helvetica", "", 7.2)
            pdf.multi_cell(78, 3.4, self._fit_text(pdf, f"Terms: {row['terms']}", 78, 2))
            drift_y = pdf.get_y() + 3

    def generate_pdf_report(self, limit_months: int = 0):
        try:
            aspect_df = self._load_csv("aspect_analysis.csv")
            topic_df = self._load_csv("topic_analysis.csv")
            ts_df = self._load_csv("topic_timeseries.csv")
            emerging_df = self._load_csv("emerging_issues.csv")
            drift_df = self._load_csv("semantic_drift.csv")
            quality_df = self._load_csv("classification_quality.csv")
            reviews_df = self._load_reviews_df()

            if topic_df is None or topic_df.empty:
                return None

            current_reviews_df, previous_reviews_df = self._filter_reviews_window(reviews_df, limit_months)
            current_ts_df = self._filter_month_window(ts_df, "month", limit_months) if ts_df is not None else None
            current_drift_df = self._filter_month_window(drift_df, "month_from", limit_months) if drift_df is not None else None

            if current_ts_df is not None and not current_ts_df.empty and "label" in topic_df.columns:
                windowed_mentions = current_ts_df.groupby("issue_label")["mentions"].sum().to_dict()
                topic_df = topic_df.copy()
                topic_df["mentions"] = topic_df["label"].map(windowed_mentions).fillna(0).astype(int)
                topic_df = topic_df[topic_df["mentions"] > 0]

            if topic_df.empty:
                return None

            topic_df = topic_df.sort_values(["mentions", "avg_severity"], ascending=[False, False])
            window_label = self._window_label(limit_months)
            generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

            summary_markdown = ai_summary_service.generate_executive_summary(limit_months=limit_months)
            summary_model = self._parse_summary(summary_markdown)
            kpis = self._compute_kpis(current_reviews_df, previous_reviews_df, ts_df, limit_months)
            alerts = self._build_alerts(ts_df, limit_months)
            aspects = self._build_aspect_summary(aspect_df, ts_df, limit_months)
            stability = self._build_stability_summary(topic_df, current_ts_df if current_ts_df is not None else ts_df)
            trending = self._build_trending_summary(ts_df, limit_months)
            ticker_items = self._build_ticker_items(current_reviews_df if not current_reviews_df.empty else reviews_df)

            top_issues = []
            for _, row in topic_df.head(10).iterrows():
                samples = self._parse_sample_reviews(row.get("sample_reviews"))
                top_issues.append(
                    {
                        "label": self.safe_text(str(row.get("label", row.get("keywords", "Unknown")))),
                        "mentions": int(row.get("mentions", 0)),
                        "severity": round(float(row.get("avg_severity", 0)), 1),
                        "evidence": samples[0] if samples else "No evidence snippet available.",
                    }
                )

            emerging_rows = []
            if emerging_df is not None and not emerging_df.empty:
                flagged = emerging_df[emerging_df["is_flagged"] == True].sort_values("estimated_volume", ascending=False).head(6)
                for _, row in flagged.iterrows():
                    emerging_rows.append(
                        {
                            "label": self.safe_text(str(row.get("label", f"Cluster {row.get('cluster_id', '')}")).replace(" (Proto)", "")),
                            "volume": int(row.get("estimated_volume", 0)),
                            "momentum": round(float(row.get("momentum_pct", 0)), 1),
                        }
                    )

            drift_rows = []
            source_drift_df = current_drift_df if current_drift_df is not None else drift_df
            if source_drift_df is not None and not source_drift_df.empty:
                grouped = (
                    source_drift_df.groupby("category")
                    .agg({"drift_score": "mean", "shifting_terms": "last"})
                    .reset_index()
                    .sort_values("drift_score", ascending=False)
                    .head(6)
                )
                for _, row in grouped.iterrows():
                    drift_rows.append(
                        {
                            "category": self.safe_text(str(row["category"])),
                            "score": round(float(row["drift_score"]), 2),
                            "terms": self.safe_text(str(row.get("shifting_terms", "stable"))),
                        }
                    )

            sentiment_breakdown = self._build_sentiment_breakdown(current_reviews_df, previous_reviews_df)

            pdf = FPDF()
            pdf.add_page()
            self._draw_page_shell(pdf)

            self._draw_hero(pdf, window_label, generated_at, ticker_items)
            pdf.set_y(54)
            self._draw_kpis(pdf, kpis)
            self._draw_summary(pdf, summary_model)
            self._draw_problem_landscape(pdf, alerts, top_issues, aspects)
            self._draw_health_and_signals(pdf, stability, trending, quality_df)
            self._draw_watchlists(pdf, emerging_df, current_drift_df if current_drift_df is not None else drift_df)
            self._draw_dashboard_detail_pages(
                pdf,
                ticker_items,
                top_issues,
                alerts,
                aspects,
                sentiment_breakdown,
                stability,
                trending,
                emerging_rows,
                drift_rows,
            )

            pdf.set_y(-16)
            pdf.set_font("Helvetica", "", 7.5)
            self._set_text(pdf, "text_soft")
            pdf.cell(
                0,
                6,
                self.safe_text(f"SignalShift dashboard report | {window_label} | Generated {generated_at}"),
                align="C",
            )

            report_path = os.path.join(self.output_dir, f"signalshift_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
            pdf.output(report_path)
            return report_path
        except Exception as e:
            print(f"Error generating PDF: {e}")
            return None
