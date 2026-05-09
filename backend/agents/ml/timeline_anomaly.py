"""
EVIDRA — Timeline Anomaly Detection (Tier 3).

Fuses CDR, Financial, and other temporal data to detect behavioral anomalies
using an Isolation Forest (Scikit-Learn).
"""
import pandas as pd
from uuid import UUID
from sklearn.ensemble import IsolationForest
from agents.base import BaseAgent
from core.database import db

class TimelineAnomalyAgent(BaseAgent):
    agent_id = "timeline_anomaly"

    async def execute(self, case_id: UUID, pipeline_run_id: UUID, task_data: dict) -> dict:
        """Run Isolation Forest over temporal metadata to find anomaly windows."""
        
        # 1. Fetch all unified timeline events (this table will be populated by fusion agents,
        # but for now we aggregate directly from canonical tables).
        
        cdr_events = await db.fetch(
            "SELECT event_timestamp as ts, 'CDR' as source FROM canonical_cdr_events WHERE case_id=$1", 
            case_id
        )
        fin_events = await db.fetch(
            "SELECT timestamp as ts, 'FINANCIAL' as source FROM canonical_financial_events WHERE case_id=$1", 
            case_id
        )
        
        all_events = [dict(e) for e in cdr_events] + [dict(e) for e in fin_events]
        if len(all_events) < 10:
            return {"status": "SKIPPED", "reason": "Not enough events for statistical anomaly detection (<10)"}

        # 2. Feature Engineering
        df = pd.DataFrame(all_events)
        df['ts'] = pd.to_datetime(df['ts'])
        df = df.sort_values('ts')
        
        # Group into 4-hour windows
        df = df.set_index('ts')
        resampled = df.groupby('source').resample('4h').size().unstack(level=0, fill_value=0)
        
        # Ensure columns exist even if empty
        if 'CDR' not in resampled.columns: resampled['CDR'] = 0
        if 'FINANCIAL' not in resampled.columns: resampled['FINANCIAL'] = 0
        
        # Activity Delta (change from previous window)
        resampled['cdr_delta'] = resampled['CDR'].diff().fillna(0)
        
        features = resampled[['CDR', 'FINANCIAL', 'cdr_delta']].values

        # 3. Isolation Forest Inference
        clf = IsolationForest(contamination=0.1, random_state=42)
        preds = clf.fit_predict(features) # -1 is anomaly, 1 is normal
        scores = clf.decision_function(features) # Lower is more anomalous
        
        resampled['anomaly'] = preds
        resampled['score'] = scores
        
        # 4. Extract anomalous windows
        anomalies = resampled[resampled['anomaly'] == -1]
        
        detected_windows = []
        for idx, row in anomalies.iterrows():
            window_start = idx
            window_end = idx + pd.Timedelta(hours=4)
            score = float(row['score'])
            
            # Normalize score 0-1 (higher is more anomalous)
            norm_score = max(0.0, min(1.0, abs(score) * 2))
            
            detected_windows.append({
                "time_start": window_start.isoformat(),
                "time_end": window_end.isoformat(),
                "fused_score": round(norm_score, 3),
                "label": "CRITICAL" if norm_score > 0.8 else "INTERESTING"
            })
            
            # Insert to anomaly_windows table
            await db.execute(
                """
                INSERT INTO anomaly_windows (case_id, pipeline_run_id, time_start, time_end, fused_score, label)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                case_id, pipeline_run_id, window_start, window_end, norm_score,
                "CRITICAL" if norm_score > 0.8 else "INTERESTING"
            )

        await self.log_step(
            "ML_INFERENCE",
            "Executed Isolation Forest",
            f"Analyzed {len(resampled)} time windows. Detected {len(detected_windows)} anomalies.",
            confidence=0.8
        )

        return {
            "windows_analyzed": len(resampled),
            "anomalies_detected": len(detected_windows),
            "anomaly_data": detected_windows,
            "_confidence": 0.8
        }
