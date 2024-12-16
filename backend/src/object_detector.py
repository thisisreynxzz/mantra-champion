# src/object_detector.py
from ultralytics import YOLO
import cv2
import numpy as np
from typing import List, Dict, Any

class ObjectDetector:
    def __init__(self):
        self.standard_model = YOLO('yolov8n.pt')
        self.custom_model = YOLO('./models/yolov8-finetuned-bmth.pt')
        
        self.REFERENCE_SIZES = {
            'person': 1700,
            'car': 4500,
            'bottle': 230,
            'laptop': 350,
            'cell phone': 150,
            'chair': 800,
            'book': 240,
            'cup': 95,
            'pothole': 1000,
            'transjakarta_bus': 12000,
            'halte': 15000,
        }
        self.FOCAL_LENGTH = 600
        self.CONF_THRESHOLD = 0.25

    def calculate_distance(self, label: str, w: float, h: float) -> float:
        """Calculate approximate distance to object based on its size in pixels."""
        if label.lower() in self.REFERENCE_SIZES:
            ref_size = self.REFERENCE_SIZES[label.lower()]
            if label.lower() in ['person', 'bottle', 'cup']:
                return (ref_size * self.FOCAL_LENGTH) / h / 10
            else:
                return (ref_size * self.FOCAL_LENGTH) / w / 10
        return 0.0

    def process_frame(self, frame) -> List[Dict[str, Any]]:
        if frame is None:
            return []
            
        # Convert to RGB if needed
        if len(frame.shape) == 2:  # Grayscale
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
        elif frame.shape[2] == 4:  # RGBA
            frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2RGB)

        # Run detection with both models
        standard_results = self.standard_model(frame)
        custom_results = self.custom_model(frame)
        
        all_detections = []
        
        # Process standard detections
        for r in standard_results:
            for box in r.boxes:
                conf = float(box.conf[0])
                if conf < self.CONF_THRESHOLD:
                    continue
                    
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                w = x2 - x1
                h = y2 - y1
                cls = int(box.cls[0])
                label = r.names[cls]
                
                distance = self.calculate_distance(label, w, h)
                
                all_detections.append({
                    'box': [int(x1), int(y1), int(x2), int(y2)],
                    'label': label,
                    'confidence': conf,
                    'distance': distance,
                    'source': 'standard'
                })
                
        # Process custom detections
        for r in custom_results:
            for box in r.boxes:
                conf = float(box.conf[0])
                if conf < self.CONF_THRESHOLD:
                    continue
                    
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                w = x2 - x1
                h = y2 - y1
                cls = int(box.cls[0])
                label = r.names[cls]
                
                distance = self.calculate_distance(label, w, h)
                
                all_detections.append({
                    'box': [int(x1), int(y1), int(x2), int(y2)],
                    'label': label,
                    'confidence': conf,
                    'distance': distance,
                    'source': 'custom'
                })
        
        return all_detections