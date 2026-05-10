import sys
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(name)s - %(message)s')

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import just the TOD model to avoid asyncpg dependencies
from agents.ml.tod_agent import TodMLModel

def run_tests():
    print("========================================")
    print("Training TOD Ensemble (Random Forest + GBM)")
    print("========================================")
    model = TodMLModel()
    model.train_synthetic(n_cases=10000)
    
    print("\nTOD Feature Importance:")
    for feat, imp in model.feature_importance().items():
        if imp > 0.05:
            print(f"  - {feat}: {imp:.4f}")

if __name__ == "__main__":
    run_tests()
