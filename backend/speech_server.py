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
            model="latest_long",
            use_enhanced=True,
            profanity_filter=False,
            enable_automatic_punctuation=True,
            enable_spoken_punctuation=True,
            enable_spoken_emojis=True,
            speech_contexts=[{
                "phrases": [
                    # Navigation Commands
                    "MANTRA", "navigation", "directions", "help",
                    
                    # MRT Stations
                    "Bundaran HI", "Dukuh Atas", "Bendungan Hilir", "Setiabudi",
                    "Istora", "Senayan", "ASEAN", "Blok M", "Blok A", "Haji Nawi",
                    "Fatmawati", "Cipete Raya", "Lebak Bulus", "Lebak Bulus Grab",
                    
                    # KRL Stations
                    "Tanah Abang", "Sudirman", "Manggarai", "Cikini", "Gondangdia",
                    "Juanda", "Sawah Besar", "Jayakarta", "Jakarta Kota",
                    "Tebet", "Cawang", "Duren Kalibata", "Pasar Minggu",
                    
                    # TransJakarta Corridors & Major Stops
                    "Blok M", "Harmoni", "Grogol", "Kalideres",
                    "Pulogadung", "Kampung Melayu", "Ragunan",
                    "Tanjung Priok", "Pluit", "Pinang Ranti",
                    
                    # Major Areas/Districts
                    "Thamrin", "Sudirman", "Kuningan", "Menteng",
                    "Senayan", "Kebayoran", "Kemang", "SCBD",
                    "Monas", "Glodok", "Kota Tua",
                    
                    # Shopping Centers
                    "Grand Indonesia", "Plaza Indonesia", "Pacific Place",
                    "Senayan City", "Plaza Senayan", "Sarinah",
                    "Central Park", "Taman Anggrek", "Kota Kasablanka",
                    
                    # Common Place Types
                    "halte", "stasiun", "terminal", "mall", "plaza",
                    "rumah sakit", "hospital", "school", "university",
                    "mosque", "masjid", "church", "gereja",
                    
                    # Common Indonesian Words in Navigation
                    "jalan", "street", "gedung", "building",
                    "persimpangan", "intersection", "belok", "turn",
                    "kanan", "right", "kiri", "left", "lurus", "straight",
                    "lewat", "through", "sampai", "until"
                ],
                "boost": 20.0
            }],
            # Audio settings for better quality
            audio_channel_count=1,  # Mono audio
            enable_separate_recognition_per_channel=False,
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