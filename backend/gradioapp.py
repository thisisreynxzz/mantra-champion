import gradio as gr
import numpy as np
import cv2
from src.mantra import MANTRA
import queue
import threading
import json
from config import RATE, CHUNK
import pyaudio
import wave
import time
import os

class AudioHandler:
    def __init__(self, mantra):
        self.mantra = mantra
        self.audio_queue = queue.Queue()
        self.is_recording = False
        self.audio = pyaudio.PyAudio()
        
    def start_recording(self):
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            stream_callback=self._audio_callback
        )
        self.is_recording = True
        self.stream.start_stream()
        
    def stop_recording(self):
        if hasattr(self, 'stream'):
            self.is_recording = False
            self.stream.stop_stream()
            self.stream.close()
            
    def _audio_callback(self, in_data, frame_count, time_info, status):
        if self.is_recording:
            self.mantra.process_audio(in_data)
        return (in_data, pyaudio.paContinue)

def create_ui():
    # Initialize MANTRA and audio handler
    mantra = MANTRA()
    audio_handler = AudioHandler(mantra)

    with gr.Blocks() as demo:
        # State management
        is_listening = gr.State(False)
        current_mode = gr.State("welcome")
        current_destination = gr.State(None)

        with gr.Row():
            with gr.Column(scale=2):
                # Mode and status display
                mode_label = gr.Label(
                    value="Current Mode: Welcome",
                    label="Status"
                )
                
                # Main display area (Camera/Map/Service info)
                camera = gr.Image(
                    label="Camera Feed",
                    sources=["webcam"],
                    streaming=True,
                    show_label=True,
                    visible=False
                )

                map_frame = gr.HTML(
                    visible=False
                )
                
                open_maps_btn = gr.Button(
                    "Open in Google Maps",
                    visible=False
                )

                service_info = gr.Markdown(
                    "Service recommendations will appear here.",
                    visible=False
                )

                # Agent response area
                agent_response = gr.Markdown()
                transcript_box = gr.Textbox(
                    label="Transcript",
                    placeholder="Waiting for speech...",
                    interactive=False
                )

                # Voice control
                listen_btn = gr.Button(
                    "Start Listening",
                    variant="primary"
                )

        def on_listen_button(listening_state):
            """Handle listen button click"""
            new_state = not listening_state
            
            if new_state:
                audio_handler.start_recording()
                mantra.start_listening()
                return "Stop Listening", True
            else:
                audio_handler.stop_recording()
                mantra.stop_listening()
                return "Start Listening", False

        def process_frame(frame, mode):
            """Process camera frame based on current mode"""
            if mode == "surroundings" and frame is not None:
                return mantra.update_display(frame)
            return frame

        def update_map(destination):
            """Update map iframe when destination changes"""
            if destination:
                map_html = f'''
                <iframe
                    width="100%"
                    height="450"
                    style="border:0"
                    loading="lazy"
                    allowfullscreen
                    src="https://www.google.com/maps/embed/v1/directions?key={os.getenv('GOOGLE_MAPS_API_KEY')}&destination={destination}&mode=transit">
                </iframe>
                '''
                return map_html, True
            return None, False

        def handle_speech_result(result):
            """Handle speech recognition results"""
            outputs = []
            
            # Default values
            transcript = result.get("transcript", "")
            mode = "welcome"
            mode_label_text = "Current Mode: Welcome"
            agent_response_text = ""
            camera_visible = False
            map_visible = False
            service_visible = False
            map_content = None
            destination = None
            
            # Update based on result
            if result.get("is_final", False) and "intent" in result:
                intent = result["intent"]
                mode = intent.get("type", "welcome")
                mode_label_text = f"Current Mode: {mode.capitalize()}"
                
                # Set visibility based on mode
                camera_visible = (mode == "surroundings")
                map_visible = (mode == "direction")
                service_visible = (mode == "service")
                
                # Handle direction mode
                if mode == "asking_for_direction":
                    destination = next(
                        (e["value"] for e in result.get("entities", [])
                         if e["type"] in ["station", "poi", "terminal"]),
                        None
                    )
                    if destination:
                        map_content, _ = update_map(destination)
                
                agent_response_text = result.get("agent_response", "")

            return [
                transcript,              # transcript_box
                mode_label_text,         # mode_label
                agent_response_text,     # agent_response
                camera_visible,          # camera
                map_visible,            # map_frame
                service_visible,         # service_info
                map_content if map_content else gr.skip(),  # map_frame content
                mode,                    # current_mode
                destination             # current_destination
            ]

        # Set up the UI callback
        mantra.set_ui_callback(handle_speech_result)

        # Event handlers
        listen_btn.click(
            fn=on_listen_button,
            inputs=[is_listening],
            outputs=[listen_btn, is_listening]
        )

        camera.stream(
            fn=process_frame,
            inputs=[camera, current_mode],
            outputs=[camera]
        )

        # Update map when destination changes
        current_destination.change(
            fn=update_map,
            inputs=[current_destination],
            outputs=[map_frame, map_frame]  # content and visibility
        )

        return demo

if __name__ == "__main__":
    demo = create_ui()
    demo.queue()  # Enable queuing for better streaming performance
    demo.launch(
        server_name="0.0.0.0",  # Make accessible from all network interfaces
        server_port=7860,       # Default Gradio port
        share=True,             # Create public link
        debug=True
    )