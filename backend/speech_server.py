import asyncio
import json
import websockets
from speechToText import MicrophoneStream, listen_print_loop
from google.cloud import speech
from config import SA_JSON_FILE_PATH

async def speech_recognition_handler(websocket):
    try:
        print("Client connected to speech recognition")
        client = speech.SpeechClient.from_service_account_file(SA_JSON_FILE_PATH)
        
        # Configure audio settings
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
        )

        streaming_config = speech.StreamingRecognitionConfig(
            config=config, interim_results=True
        )

        # Start microphone stream
        with MicrophoneStream(16000, int(16000 / 10)) as stream:
            audio_generator = stream.generator()
            requests = (
                speech.StreamingRecognizeRequest(audio_content=content)
                for content in audio_generator
            )

            responses = client.streaming_recognize(streaming_config, requests)

            for response in responses:
                if not response.results:
                    continue

                result = response.results[0]
                if not result.alternatives:
                    continue

                transcript = result.alternatives[0].transcript

                # Send transcript to websocket client
                await websocket.send(json.dumps({
                    "transcript": transcript,
                    "is_final": result.is_final
                }))

                if result.is_final and any(word in transcript.lower() for word in ["exit", "quit"]):
                    break

    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected from speech recognition")
    except Exception as e:
        print(f"Error in speech recognition: {e}")

async def main():
    async with websockets.serve(speech_recognition_handler, "localhost", 8000) as server:
        print("Speech recognition server started on ws://localhost:8000")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())