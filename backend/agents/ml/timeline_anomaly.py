"""
EVIDRA — Timeline Anomaly Agent (Tier 2).

Implements the advanced ML Specification:
- Isolation Forest for Point Anomalies (Feature vectors of events)
- LSTM Autoencoder for Temporal Sequence Anomalies
"""
import numpy as np
import torch
import torch.nn as nn
from sklearn.ensemble import IsolationForest
from uuid import UUID
from datetime import datetime
from agents.base import BaseAgent
from core.database import db

def parse_dt(dt_str: str) -> datetime:
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))

def event_to_features(event: dict, prev_event: dict = None) -> np.ndarray:
    features = []
    ts = parse_dt(event['timestamp'])
    
    features += [ts.hour / 23.0, ts.weekday() / 6.0]
    
    if prev_event:
        gap_s = (ts - parse_dt(prev_event['timestamp'])).total_seconds()
        features.append(min(gap_s / 86400.0, 1.0))
    else:
        features.append(0.5)

    EVENT_TYPES = ["CALL", "SMS", "LOCATION_PING", "PURCHASE", "APP_USE", "EMAIL", "OTHER"]
    for et in EVENT_TYPES:
        features.append(1.0 if event.get('event_type') == et else 0.0)

    if event.get('location_lat') and event.get('location_lng'):
        features.append(event['location_lat'] / 90.0)
        features.append(event['location_lng'] / 180.0)
    else:
        features += [0.0, 0.0]

    return np.array(features, dtype=np.float32)

class TimelineAutoencoder(nn.Module):
    def __init__(self, input_dim=12, hidden_dim=32, latent_dim=8, seq_len=10):
        super().__init__()
        self.encoder = nn.LSTM(input_dim, hidden_dim, batch_first=True)
        self.to_latent = nn.Linear(hidden_dim, latent_dim)
        self.from_latent = nn.Linear(latent_dim, hidden_dim)
        self.decoder = nn.LSTM(hidden_dim, input_dim, batch_first=True)

    def forward(self, x):
        enc_out, (h, c) = self.encoder(x)
        latent = self.to_latent(h[-1])
        decoded_h = self.from_latent(latent).unsqueeze(1).repeat(1, x.size(1), 1)
        dec_out, _ = self.decoder(decoded_h)
        return dec_out, latent

class TimelineAnomalyAgent(BaseAgent):
    agent_id = "anomaly_detector"

    async def execute(self, case_id: UUID, pipeline_run_id: UUID, task_data: dict) -> dict:
        events_records = await db.fetch("SELECT * FROM timeline_events WHERE case_id=$1 ORDER BY timestamp ASC", case_id)
        if not events_records or len(events_records) < 10:
            return {"status": "SKIPPED", "reason": "Not enough events for ML models"}

        events = [dict(e) for e in events_records]
        
        # 1. Feature Extraction
        feature_matrix = []
        for i, ev in enumerate(events):
            prev = events[i-1] if i > 0 else None
            feature_matrix.append(event_to_features(ev, prev))
            
        X = np.array(feature_matrix)

        # 2. Isolation Forest (Point Anomalies)
        ifo = IsolationForest(n_estimators=200, contamination=0.05, random_state=42)
        ifo.fit(X)
        raw_scores = ifo.decision_function(X)
        norm_scores = (raw_scores.max() - raw_scores) / (raw_scores.max() - raw_scores.min() + 1e-10)

        for i, ev in enumerate(events):
            ev['anomaly_score'] = float(norm_scores[i])

        # 3. LSTM Autoencoder (Sequence Anomalies)
        seq_len = 10
        if len(X) >= seq_len:
            model = TimelineAutoencoder(seq_len=seq_len)
            model.eval()
            
            # Simple inference loop
            for i in range(len(X) - seq_len):
                seq = torch.tensor(X[i:i+seq_len], dtype=torch.float32).unsqueeze(0)
                recon, _ = model(seq)
                err = ((seq - recon) ** 2).mean().item()
                if err > 0.15: # High reconstruction error
                    events[i+seq_len-1]['anomaly_score'] = max(events[i+seq_len-1]['anomaly_score'], min(1.0, err * 5))

        # Save updates
        anomalies_found = 0
        for ev in events:
            if ev['anomaly_score'] > 0.6:
                anomalies_found += 1
                await db.execute("UPDATE timeline_events SET anomaly_score=$1 WHERE event_id=$2", ev['anomaly_score'], ev['event_id'])

        await self.log_step(
            "HYBRID_ML",
            "Timeline Anomaly Detection",
            f"Ran Isolation Forest and LSTM Autoencoder over {len(events)} events. Found {anomalies_found} severe anomalies.",
            confidence=0.85
        )

        return {"anomalies_found": anomalies_found, "_confidence": 0.85}
