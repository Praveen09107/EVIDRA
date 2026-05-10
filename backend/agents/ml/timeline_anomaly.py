"""
EVIDRA — Timeline & Anomaly Agent (Tier 2 / M-08).

Implements Complete ML Specification §5:
- Multi-Modal Time Series Fusion (CDR + Financial + Device → 15-min bin matrix)
- Bidirectional LSTM Autoencoder (trained on synthetic normal patterns)
- Isolation Forest (point anomaly detector)
- Anomaly Window Construction (merging consecutive anomalous buckets)
"""
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from uuid import UUID
from datetime import datetime, timedelta
import logging
from agents.base import BaseAgent
from core.database import db

logger = logging.getLogger("evidra.timeline")

N_FEATURES = 8  # Per spec §5.1
RESOLUTION_MINUTES = 15
WINDOW_SIZE = 32  # 32 × 15min = 8h window


# ═══════════════════════════════════════════════════════════
# Multi-Modal Fusion Matrix (spec §5.1)
# ═══════════════════════════════════════════════════════════

def build_feature_matrix(events: list[dict], window_days: int = 7) -> tuple[np.ndarray, list[datetime]]:
    """
    Fuses CDR + Financial + Device events into a (T, 8) matrix.
    Features per 15-min bin:
      0: call_count       4: financial_txn_count
      1: sms_count        5: financial_amount_norm
      2: data_sessions    6: tod_probability (placeholder)
      3: unique_contacts  7: silence_indicator
    """
    if not events:
        return np.zeros((1, N_FEATURES)), [datetime.utcnow()]

    timestamps = []
    for e in events:
        ts = e.get("timestamp") or e.get("event_timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if ts:
            timestamps.append(ts)

    if not timestamps:
        return np.zeros((1, N_FEATURES)), [datetime.utcnow()]

    end_time = max(timestamps)
    start_time = end_time - timedelta(days=window_days)
    n_bins = int((end_time - start_time).total_seconds() / (RESOLUTION_MINUTES * 60)) + 1
    n_bins = max(n_bins, 1)

    matrix = np.zeros((n_bins, N_FEATURES))
    bin_timestamps = [start_time + timedelta(minutes=RESOLUTION_MINUTES * i) for i in range(n_bins)]

    def bin_idx(ts):
        delta = (ts - start_time).total_seconds()
        idx = int(delta / (RESOLUTION_MINUTES * 60))
        return max(0, min(n_bins - 1, idx))

    contacts_per_bin = [set() for _ in range(n_bins)]

    for e in events:
        ts = e.get("timestamp") or e.get("event_timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if not ts:
            continue

        idx = bin_idx(ts)
        stream = e.get("stream_type", "CDR")
        etype = str(e.get("event_type", "")).upper()

        if stream == "CDR" or "CDR" in str(e.get("source", "")):
            if "SMS" in etype:
                matrix[idx, 1] += 1
            elif "DATA" in etype:
                matrix[idx, 2] += 1
            else:
                matrix[idx, 0] += 1
            cp = e.get("counterparty_msisdn") or e.get("counterparty")
            if cp:
                contacts_per_bin[idx].add(cp)

        elif stream == "FINANCIAL" or "FINANCIAL" in str(e.get("source", "")):
            matrix[idx, 4] += 1
            amt = float(e.get("amount", 0))
            matrix[idx, 5] += amt

    # Unique contacts per bin
    for i in range(n_bins):
        matrix[i, 3] = len(contacts_per_bin[i])

    # Silence indicator (no CDR activity)
    matrix[:, 7] = (matrix[:, :4].sum(axis=1) == 0).astype(float)

    # Normalize financial amounts
    max_fin = matrix[:, 5].max()
    if max_fin > 0:
        matrix[:, 5] /= max_fin

    # Normalize counts
    for col in [0, 1, 2, 3, 4]:
        max_val = matrix[:, col].max()
        if max_val > 0:
            matrix[:, col] /= max_val

    return matrix, bin_timestamps


# ═══════════════════════════════════════════════════════════
# Bidirectional LSTM Autoencoder (spec §5.2)
# ═══════════════════════════════════════════════════════════

class TimelineLSTMAutoencoder(nn.Module):
    """
    BiLSTM Autoencoder for timeline anomaly detection.
    Trained on normal daily activity patterns.
    Anomaly = high reconstruction error over a window.
    """

    def __init__(self, n_features: int = 8, hidden_dim: int = 64, latent_dim: int = 16):
        super().__init__()
        self.encoder_lstm = nn.LSTM(n_features, hidden_dim, batch_first=True, bidirectional=True)
        self.enc_fc = nn.Linear(hidden_dim * 2, latent_dim)
        self.dec_lstm = nn.LSTM(latent_dim, hidden_dim, batch_first=True)
        self.dec_fc = nn.Linear(hidden_dim, n_features)

    def forward(self, x):
        enc_out, (h, _) = self.encoder_lstm(x)
        latent = torch.tanh(self.enc_fc(enc_out[:, -1, :]))
        seq_len = x.size(1)
        dec_in = latent.unsqueeze(1).expand(-1, seq_len, -1)
        dec_out, _ = self.dec_lstm(dec_in)
        return self.dec_fc(dec_out)


def _generate_synthetic_timeline_data(n_sequences: int = 8000, seq_len: int = 32) -> np.ndarray:
    """Generate synthetic 'normal' timeline activity for autoencoder training."""
    np.random.seed(42)
    data = []
    for _ in range(n_sequences):
        seq = np.zeros((seq_len, N_FEATURES))
        # Simulate normal daily pattern (32 bins × 15min = 8 hours)
        activity_level = np.random.uniform(0.2, 0.8)
        for t in range(seq_len):
            hour_frac = (t / seq_len)
            # Simulate circadian rhythm: more activity during day
            activity = activity_level * (0.5 + 0.5 * np.sin(np.pi * hour_frac))
            noise = np.random.normal(0, 0.1)

            seq[t, 0] = max(0, activity + noise)  # calls
            seq[t, 1] = max(0, activity * 0.3 + np.random.normal(0, 0.05))  # SMS
            seq[t, 2] = max(0, activity * 0.2 + np.random.normal(0, 0.05))  # data
            seq[t, 3] = max(0, activity * 0.5 + np.random.normal(0, 0.1))  # contacts
            seq[t, 4] = max(0, np.random.exponential(0.1))  # financial txn
            seq[t, 5] = max(0, np.random.exponential(0.05))  # fin amount norm
            seq[t, 6] = 0  # tod_probability placeholder
            seq[t, 7] = 1.0 if sum(seq[t, :4]) < 0.05 else 0.0  # silence
        data.append(seq)
    return np.array(data, dtype=np.float32)


def train_timeline_autoencoder(epochs: int = 40) -> TimelineLSTMAutoencoder:
    """Train the BiLSTM Autoencoder on synthetic normal timeline sequences."""
    logger.info("Training Timeline BiLSTM Autoencoder on synthetic data...")
    X = _generate_synthetic_timeline_data(n_sequences=8000, seq_len=WINDOW_SIZE)

    # Standardize
    flat = X.reshape(-1, N_FEATURES)
    scaler = StandardScaler()
    flat_scaled = scaler.fit_transform(flat)
    X_scaled = flat_scaled.reshape(-1, WINDOW_SIZE, N_FEATURES)

    dataset = TensorDataset(torch.tensor(X_scaled, dtype=torch.float32))
    loader = DataLoader(dataset, batch_size=128, shuffle=True)

    model = TimelineLSTMAutoencoder(n_features=N_FEATURES)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=15, gamma=0.5)
    criterion = nn.MSELoss()

    model.train()
    for epoch in range(epochs):
        total_loss = 0
        for (batch,) in loader:
            optimizer.zero_grad()
            recon = model(batch)
            loss = criterion(recon, batch)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        scheduler.step()
        if (epoch + 1) % 10 == 0:
            logger.info(f"  Epoch {epoch+1}/{epochs}, Loss: {total_loss/len(loader):.6f}")

    model.eval()
    logger.info("Timeline BiLSTM Autoencoder training complete.")
    return model


# ═══════════════════════════════════════════════════════════
# Anomaly Window Construction (spec §5.3)
# ═══════════════════════════════════════════════════════════

def build_anomaly_windows(bin_timestamps: list[datetime], anomaly_flags: np.ndarray, scores: np.ndarray) -> list[dict]:
    """Merge consecutive anomalous bins into windows."""
    windows = []
    in_window = False
    window_start = None
    window_scores = []

    for i in range(len(anomaly_flags)):
        if anomaly_flags[i] and not in_window:
            window_start = i
            window_scores = [scores[i]]
            in_window = True
        elif anomaly_flags[i] and in_window:
            window_scores.append(scores[i])
        elif not anomaly_flags[i] and in_window:
            avg_score = float(np.mean(window_scores))
            windows.append({
                "window_start": bin_timestamps[window_start].isoformat(),
                "window_end": bin_timestamps[min(i, len(bin_timestamps) - 1)].isoformat(),
                "duration_hours": round((i - window_start) * RESOLUTION_MINUTES / 60, 2),
                "avg_anomaly_score": round(avg_score, 4),
                "severity": "CRITICAL" if avg_score > 0.8 else "HIGH" if avg_score > 0.6 else "MEDIUM" if avg_score > 0.4 else "LOW",
            })
            in_window = False

    # Close any open window
    if in_window and window_start is not None:
        avg_score = float(np.mean(window_scores))
        windows.append({
            "window_start": bin_timestamps[window_start].isoformat(),
            "window_end": bin_timestamps[-1].isoformat(),
            "duration_hours": round((len(anomaly_flags) - window_start) * RESOLUTION_MINUTES / 60, 2),
            "avg_anomaly_score": round(avg_score, 4),
            "severity": "CRITICAL" if avg_score > 0.8 else "HIGH" if avg_score > 0.6 else "MEDIUM",
        })

    return windows


class TimelineAnomalyAgent(BaseAgent):
    agent_id = "anomaly_detector"
    _trained_model = None

    @classmethod
    def _get_trained_model(cls) -> TimelineLSTMAutoencoder:
        if cls._trained_model is None:
            cls._trained_model = train_timeline_autoencoder()
        return cls._trained_model

    async def execute(self, case_id: UUID, pipeline_run_id: UUID, task_data: dict) -> dict:
        # 1. Fetch all event streams
        cdr_events = await db.fetch(
            "SELECT *, 'CDR' as stream_type FROM canonical_cdr_events WHERE case_id=$1 ORDER BY event_timestamp ASC",
            case_id,
        )
        fin_events = await db.fetch(
            "SELECT *, 'FINANCIAL' as stream_type FROM canonical_financial_events WHERE case_id=$1 ORDER BY timestamp ASC",
            case_id,
        )

        all_events = [dict(e) for e in (cdr_events or [])] + [dict(e) for e in (fin_events or [])]
        if len(all_events) < 10:
            return {"status": "SKIPPED", "reason": "Not enough events for ML models"}

        # 2. Build multi-modal feature matrix (spec §5.1)
        matrix, bin_timestamps = build_feature_matrix(all_events)
        n_bins = len(matrix)

        await self.log_step(
            "DATA_NORMALIZATION",
            "Multi-Modal Time Series Fusion",
            f"Built {n_bins} time bins ({N_FEATURES} features each) from {len(all_events)} events.",
            confidence=0.95,
        )

        # 3. Isolation Forest on bin features (spec §5.3 Model 1)
        iso = IsolationForest(n_estimators=200, contamination=0.05, random_state=42)
        iso.fit(matrix)
        if_labels = iso.predict(matrix)
        if_anomaly = (if_labels == -1)

        # 4. BiLSTM Autoencoder sliding window (spec §5.2)
        ae_anomaly = np.zeros(n_bins, dtype=bool)
        ae_scores = np.zeros(n_bins)

        if n_bins >= WINDOW_SIZE:
            model = self._get_trained_model()
            scaler = StandardScaler()
            matrix_scaled = scaler.fit_transform(matrix)

            stride = 4
            with torch.no_grad():
                for start in range(0, n_bins - WINDOW_SIZE, stride):
                    window = matrix_scaled[start:start + WINDOW_SIZE]
                    x = torch.tensor(window, dtype=torch.float32).unsqueeze(0)
                    recon = model(x)
                    error = float(torch.mean((x - recon) ** 2))

                    if error > 0.045:  # Trained threshold (spec: 0.045)
                        for j in range(start, start + WINDOW_SIZE):
                            ae_anomaly[j] = True
                            ae_scores[j] = max(ae_scores[j], min(1.0, error / 0.045))

        # 5. Fuse: anomaly if BOTH agree (spec §5.3)
        fused_anomaly = if_anomaly & ae_anomaly
        fused_scores = ae_scores * fused_anomaly.astype(float)

        # 6. Build anomaly windows (spec §5.3)
        anomaly_windows = build_anomaly_windows(bin_timestamps, fused_anomaly, fused_scores)

        # 7. Save anomaly windows to DB
        for w in anomaly_windows:
            await db.execute(
                """
                INSERT INTO anomaly_windows (case_id, pipeline_run_id, time_start, time_end, fused_score, label)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                case_id, pipeline_run_id,
                datetime.fromisoformat(w["window_start"]),
                datetime.fromisoformat(w["window_end"]),
                w["avg_anomaly_score"],
                w["severity"],
            )

        anomalous_pct = round(100 * fused_anomaly.sum() / max(n_bins, 1), 1)

        await self.log_step(
            "HYBRID_ML",
            "Timeline Anomaly Detection Complete",
            f"IF + BiLSTM fusion: {fused_anomaly.sum()}/{n_bins} bins anomalous ({anomalous_pct}%). "
            f"{len(anomaly_windows)} anomaly windows constructed.",
            confidence=0.87,
        )

        return {
            "total_bins": n_bins,
            "anomalous_bins": int(fused_anomaly.sum()),
            "anomaly_rate": round(anomalous_pct / 100, 4),
            "anomaly_windows": anomaly_windows,
            "_confidence": 0.87,
        }
