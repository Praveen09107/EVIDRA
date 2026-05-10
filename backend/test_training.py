import sys
import os
import logging
import asyncio

# Setup basic logging to see the output
logging.basicConfig(level=logging.INFO, format='%(name)s - %(message)s')

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.ml.tod_agent import _get_tod_model
from agents.ml.timeline_anomaly import _get_timeline_model
from agents.ml.financial_analyzer import _get_financial_model

def run_tests():
    print("========================================")
    print("1. Training TOD Ensemble (Random Forest + GBM)")
    print("========================================")
    tod_model = _get_tod_model()
    print("\nTOD Feature Importance:")
    for feat, imp in tod_model.feature_importance().items():
        if imp > 0.05:
            print(f"  - {feat}: {imp:.4f}")

    print("\n========================================")
    print("2. Training Timeline BiLSTM Autoencoder")
    print("========================================")
    timeline_model = _get_timeline_model()

    print("\n========================================")
    print("3. Training Financial BiLSTM Autoencoder")
    print("========================================")
    financial_model = _get_financial_model()

if __name__ == "__main__":
    run_tests()
