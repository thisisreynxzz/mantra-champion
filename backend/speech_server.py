import asyncio
import json
import websockets
from speechToText import MicrophoneStream, listen_print_loop
from google.cloud import speech
from config import SA_JSON_FILE_PATH
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
import datetime

def init_vertexai(project_id, location="us-central1"):
    """Initialize VertexAI with project settings."""
    vertexai.init(project=project_id, location=location)
    return GenerativeModel("gemini-1.5-flash")

def get_response_schema():
    return {
        "type": "object",
        "properties": {
            "intent": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["asking_for_direction", "analyzing_surroundings", "service_recommendation"]
                    },
                    "confidence": {"type": "number"}
                },
                "required": ["type", "confidence"]
            },
            "entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["station", "poi", "terminal", "route", "transport_type", "obstacle", "facility"]
                        },
                        "value": {"type": "string"},
                        "start": {"type": "integer"},
                        "end": {"type": "integer"}
                    },
                    "required": ["type", "value", "start", "end"]
                }
            }
        },
        "required": ["intent", "entities"]
    }

def create_classification_prompt(text):
    return f"""Analyze the following user utterance for intent and entities related to Jakarta public transportation:

"{text}"

Classify the intent as one of:
- asking_for_direction: Questions about getting somewhere using public transport
- analyzing_surroundings: Questions about immediate environment/obstacles near transport facilities
- service_recommendation: Questions about recommended routes or transport options

Identify entities including:
- stations (MRT/KRL)
- POIs (landmarks, malls)
- terminals
- routes
- transport types
- obstacles
- facilities

Return structured JSON with intent type, confidence score (0-1), and entity mentions with their positions."""

async def classify_intent_and_entities(transcript, model):
    """Classify intent and extract entities from speech transcript using Gemini."""
    try:
        response = model.generate_content(
            create_classification_prompt(transcript),
            generation_config=GenerationConfig(
                temperature=0.1,  # Low temperature for consistent classification
                candidate_count=1,
                max_output_tokens=1024,
                response_mime_type="application/json",
                response_schema=get_response_schema()
            )
        )
        
        classification = json.loads(response.text)
        return classification
        
    except Exception as e:
        print(f"Error in classification: {e}")
        return {
            "intent": {"type": "unknown", "confidence": 0.0},
            "entities": []
        }

async def speech_recognition_handler(websocket):
    try:
        print("Client connected to speech recognition")
        
        # Initialize Speech-to-Text client
        client = speech.SpeechClient.from_service_account_file(SA_JSON_FILE_PATH)
        
        # Initialize Gemini model
        PROJECT_ID = 'ai-for-impact-bmth'
        model = init_vertexai(PROJECT_ID)
        
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

                # Only perform classification on final results
                if result.is_final:
                    try:
                        # Get intent and entity classification
                        classification = await classify_intent_and_entities(transcript, model)
                        
                        # Send transcript and classification to websocket client
                        await websocket.send(json.dumps({
                            "transcript": transcript,
                            "is_final": True,
                            "classification": classification,
                            "confidence": result.alternatives[0].confidence,
                            "timestamp": datetime.datetime.now().isoformat()
                        }))
                        
                        # Log the classification for debugging
                        print(f"Classification for: {transcript}")
                        print(json.dumps(classification, indent=2))
                        
                    except Exception as class_error:
                        print(f"Classification error: {class_error}")
                        # Send transcript without classification if there's an error
                        await websocket.send(json.dumps({
                            "transcript": transcript,
                            "is_final": True,
                            "error": str(class_error),
                            "confidence": result.alternatives[0].confidence,
                            "timestamp": datetime.datetime.now().isoformat()
                        }))
                else:
                    # Send interim results without classification
                    await websocket.send(json.dumps({
                        "transcript": transcript,
                        "is_final": False,
                        "confidence": result.alternatives[0].confidence,
                        "timestamp": datetime.datetime.now().isoformat()
                    }))

                # Check for exit commands
                if result.is_final and any(word in transcript.lower() for word in ["exit", "quit"]):
                    print("Exit command received")
                    break

    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected from speech recognition")
    except Exception as e:
        print(f"Error in speech recognition: {e}")
        # Try to send error message to client if connection is still open
        try:
            await websocket.send(json.dumps({
                "error": str(e),
                "timestamp": datetime.datetime.now().isoformat()
            }))
        except:
            pass

async def main():
    async with websockets.serve(speech_recognition_handler, "localhost", 8000) as server:
        print("Speech recognition server started on ws://localhost:8000")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())