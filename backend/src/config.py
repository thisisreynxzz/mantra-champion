# config.py
import os

# Path to your Google Cloud service account JSON file
SA_JSON_FILE_PATH = './bmth-sa-key.json'

# Model paths
MODEL_PATH = './models/intent_classifier'

# Speech recognition settings
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms chunks

# Object detection settings
DETECTION_CONFIDENCE_THRESHOLD = 0.25