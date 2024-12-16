# src/audio_processor.py
import queue
import threading
from google.cloud import speech
from typing import Callable, Any

class AudioProcessor:
    def __init__(self, speech_processor, callback: Callable[[dict], Any]):
        self.speech_processor = speech_processor
        self.callback = callback
        self.audio_queue = queue.Queue()
        self.is_running = False
        self.thread = None

    def start(self):
        if self.thread is not None:
            return
            
        self.is_running = True
        self.thread = threading.Thread(target=self._process_audio_stream)
        self.thread.start()

    def stop(self):
        self.is_running = False
        if self.thread is not None:
            self.thread.join()
            self.thread = None

    def _process_audio_stream(self):
        streaming_config = speech.StreamingRecognitionConfig(
            config=self.speech_processor.get_speech_config(),
            interim_results=True
        )

        while self.is_running:
            try:
                # Process audio chunks from queue
                audio_generator = self._audio_generator()
                requests = (
                    speech.StreamingRecognizeRequest(audio_content=content)
                    for content in audio_generator
                )

                responses = self.speech_processor.client.streaming_recognize(
                    streaming_config, requests
                )

                for response in responses:
                    if not self.is_running:
                        break

                    if not response.results:
                        continue

                    result = response.results[0]
                    if not result.alternatives:
                        continue

                    transcript = result.alternatives[0].transcript

                    if result.is_final:
                        # Process final transcript
                        intent_result = self.speech_processor.intent_classifier.predict(transcript)
                        # Extract entities and generate response
                        # Call callback with results
                        self.callback({
                            "transcript": transcript,
                            "intent": intent_result,
                            "is_final": True,
                            "confidence": result.alternatives[0].confidence
                        })
                    else:
                        # Send interim results
                        self.callback({
                            "transcript": transcript,
                            "is_final": False
                        })

            except Exception as e:
                print(f"Error in audio processing: {e}")
                continue

    def _audio_generator(self):
        while self.is_running:
            try:
                chunk = self.audio_queue.get(timeout=1)
                yield chunk
            except queue.Empty:
                continue

    def add_audio(self, audio_chunk):
        if self.is_running:
            self.audio_queue.put(audio_chunk)