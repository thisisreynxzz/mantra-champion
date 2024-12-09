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
        self.model = YOLO('yolov8n.pt')
        self.REFERENCE_SIZES = {
            'person': 1700,
            'car': 4500,
            'bottle': 230,
            'laptop': 350,
            'cell phone': 150,
            'chair': 800,
            'book': 240,
            'cup': 95
        }
        self.FOCAL_LENGTH = 600

    def process_frame(self, frame_data):
        # Decode base64 image
        img_bytes = base64.b64decode(frame_data.split(',')[1])
        nparr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Run detection
        results = self.model(frame)
        detections = []

        for r in results:
            boxes = r.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                w = x2 - x1
                h = y2 - y1
                
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                label = r.names[cls]

                distance = None
                if label.lower() in self.REFERENCE_SIZES:
                    ref_size = self.REFERENCE_SIZES[label.lower()]
                    if label.lower() in ['person', 'bottle', 'cup']:
                        distance = (ref_size * self.FOCAL_LENGTH) / h
                    else:
                        distance = (ref_size * self.FOCAL_LENGTH) / w

                detections.append({
                    'box': [int(x1), int(y1), int(x2), int(y2)],
                    'label': label,
                    'confidence': conf,
                    'distance': distance
                })

        return detections

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
    uvicorn.run(app, host="0.0.0.0", port=8000)