# src/intent_classifier.py
import tensorflow as tf
import pickle
from typing import Dict, Any

class IntentClassifier:
    def __init__(self, model_path_prefix: str):
        self.model = tf.keras.models.load_model(f'{model_path_prefix}_model.h5')
        
        with open(f'{model_path_prefix}_vectorizer.pkl', 'rb') as f:
            self.vectorizer = pickle.load(f)
        
        with open(f'{model_path_prefix}_label_encoder.pkl', 'rb') as f:
            self.label_encoder = pickle.load(f)

    def predict(self, text: str) -> Dict[str, Any]:
        X = self.vectorizer.transform([text]).toarray()
        probs = self.model.predict(X)[0]
        pred_class = int(tf.argmax(probs))
        confidence = float(probs[pred_class])
        predicted_intent = self.label_encoder.inverse_transform([pred_class])[0]
        
        return {
            "type": predicted_intent,
            "confidence": confidence
        }