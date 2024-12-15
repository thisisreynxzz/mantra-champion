from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import cv2
import numpy as np
import base64
from ultralytics import YOLO
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ObjectDetector:
    def __init__(self):
        # Load both models
        self.standard_model = YOLO('./yolov8n.pt')
        self.custom_model = YOLO('./yolov8-finetuned-bmth.pt')  # Your fine-tuned model
        
        # Reference sizes for distance calculation
        self.REFERENCE_SIZES = {
            'person': 1700,
            'car': 4500,
            'bottle': 230,
            'laptop': 350,
            'cell phone': 150,
            'chair': 800,
            'book': 240,
            'cup': 95,
            # Add reference sizes for your custom objects if needed
            'pothole': 1000,  # Example value, adjust based on actual size
            'transjakarta_bus': 12000,  # Example value
            'halte': 15000,  # Example value
        }
        self.FOCAL_LENGTH = 600

        # Define confidence thresholds
        self.CONF_THRESHOLD = 0.25
        
        # Create combined class names
        self.class_names = {
            **self.standard_model.names,  # Standard YOLO classes
            **self.custom_model.names     # Your custom classes
        }

    def calculate_distance(self, label, w, h):
        """Calculate distance based on object dimensions"""
        if label.lower() in self.REFERENCE_SIZES:
            ref_size = self.REFERENCE_SIZES[label.lower()]
            if label.lower() in ['person', 'bottle', 'cup']:
                return (ref_size * self.FOCAL_LENGTH) / h / 10
            else:
                return (ref_size * self.FOCAL_LENGTH) / w / 10
        return None

    def process_detections(self, results, is_custom_model=False):
        """Process detection results from a single model"""
        detections = []
        
        for r in results:
            boxes = r.boxes
            for box in boxes:
                conf = float(box.conf[0])
                
                # Skip low confidence detections
                if conf < self.CONF_THRESHOLD:
                    continue
                
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                w = x2 - x1
                h = y2 - y1
                
                cls = int(box.cls[0])
                label = r.names[cls]
                
                # Calculate distance if reference size exists
                distance = self.calculate_distance(label, w, h)
                
                detections.append({
                    'box': [int(x1), int(y1), int(x2), int(y2)],
                    'label': label,
                    'confidence': conf,
                    'distance': distance,
                    'source': 'custom' if is_custom_model else 'standard'
                })
        
        return detections

    def process_frame(self, frame_data):
        # Decode base64 image
        img_bytes = base64.b64decode(frame_data.split(',')[1])
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Run detection with both models
        standard_results = self.standard_model(frame)
        custom_results = self.custom_model(frame)
        
        # Process detections from both models
        standard_detections = self.process_detections(standard_results, False)
        custom_detections = self.process_detections(custom_results, True)
        
        # Combine detections
        all_detections = standard_detections + custom_detections
        
        # Optional: Remove overlapping detections
        filtered_detections = self.remove_overlapping_detections(all_detections)
        
        return filtered_detections

    def remove_overlapping_detections(self, detections, iou_threshold=0.5):
        """Remove overlapping detections with lower confidence"""
        if not detections:
            return []

        # Sort detections by confidence
        detections = sorted(detections, key=lambda x: x['confidence'], reverse=True)
        kept_detections = []

        for detection in detections:
            should_keep = True
            box1 = detection['box']

            for kept in kept_detections:
                box2 = kept['box']
                iou = self.calculate_iou(box1, box2)

                if iou > iou_threshold:
                    should_keep = False
                    break

            if should_keep:
                kept_detections.append(detection)

        return kept_detections

    def calculate_iou(self, box1, box2):
        """Calculate Intersection over Union between two boxes"""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])

        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0

detector = ObjectDetector()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            frame_data = await websocket.receive_text()
            detections = detector.process_frame(frame_data)
            await websocket.send_json(detections)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)