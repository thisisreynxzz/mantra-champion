# src/mantra.py
from typing import Optional, Dict, Any
import numpy as np
import cv2
from .audio_processor import AudioProcessor
from .speech_processor import SpeechProcessor
from .object_detector import ObjectDetector
from .intent_classifier import IntentClassifier

class MANTRA:
    def __init__(self):
        self.intent_classifier = IntentClassifier('./models/intent_classifier')
        self.object_detector = ObjectDetector()
        self.speech_processor = SpeechProcessor(self.intent_classifier)
        self.audio_processor = AudioProcessor(
            self.speech_processor, 
            self._handle_speech_result
        )
        
        self.current_mode = "welcome"  # welcome, direction, surroundings, service
        self.current_destination = None
        self.is_listening = False
        self._callback = None

    def set_ui_callback(self, callback):
        self._callback = callback

    def _handle_speech_result(self, result: Dict[str, Any]):
        if self._callback:
            self._callback(result)

    def start_listening(self):
        self.is_listening = True
        self.audio_processor.start()

    def stop_listening(self):
        self.is_listening = False
        self.audio_processor.stop()

    def update_display(self, frame):
        if self.current_mode == "surroundings":
            detections = self.object_detector.process_frame(frame)
            # Draw detections on frame
            for det in detections:
                box = det['box']
                label = f"{det['label']} {det['confidence']:.2f}"
                cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), (0, 255, 0), 2)
                cv2.putText(frame, label, (box[0], box[1] - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        return frame

    def process_audio(self, audio_chunk):
        if self.is_listening:
            self.audio_processor.add_audio(audio_chunk)