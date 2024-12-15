from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from google.cloud import speech
from config import SA_JSON_FILE_PATH
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
import datetime
from speechToText import MicrophoneStream
from typing import Dict, Any
import tensorflow as tf
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder
import pickle
import numpy as np

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class IntentClassifier:
    def __init__(self, model_path_prefix: str):
        """Load the pre-trained intent classification model."""
        # Load the trained model
        self.model = tf.keras.models.load_model(f'{model_path_prefix}_model.h5')
        
        # Load vectorizer and label encoder
        with open(f'{model_path_prefix}_vectorizer.pkl', 'rb') as f:
            self.vectorizer = pickle.load(f)
        
        with open(f'{model_path_prefix}_label_encoder.pkl', 'rb') as f:
            self.label_encoder = pickle.load(f)

    def predict(self, text: str) -> Dict[str, Any]:
        """Predict intent for input text."""
        # Vectorize the input text
        X = self.vectorizer.transform([text]).toarray()
        
        # Get prediction probabilities
        probs = self.model.predict(X)[0]
        pred_class = np.argmax(probs)
        confidence = float(probs[pred_class])
        
        # Convert prediction to intent label
        predicted_intent = self.label_encoder.inverse_transform([pred_class])[0]
        
        return {
            "type": predicted_intent,
            "confidence": confidence
        }

class SpeechProcessor:
    def __init__(self, intent_model_path: str):
        self.project_id = 'ai-for-impact-bmth'
        self.client = speech.SpeechClient.from_service_account_file(SA_JSON_FILE_PATH)
        self.gemini_model = self.init_vertexai()
        self.intent_classifier = IntentClassifier(intent_model_path)
        self.config = self.get_speech_config()

    def init_vertexai(self):
        """Initialize VertexAI for entity extraction."""
        vertexai.init(project=self.project_id, location="us-central1")
        return GenerativeModel("gemini-1.5-flash")

    def get_speech_config(self) -> speech.RecognitionConfig:
        """Get speech recognition configuration."""
        return speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
            model="latest_long",
            use_enhanced=True,
            enable_automatic_punctuation=True,
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
            audio_channel_count=1,
            enable_separate_recognition_per_channel=False,
        )

    def _get_entity_schema(self) -> Dict:
        """Get schema for entity extraction."""
        return {
            "type": "object",
            "properties": {
                "entities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["station", "poi", "terminal", "route", 
                                       "transport_type", "obstacle", "facility"]
                            },
                            "value": {"type": "string"},
                            "start": {"type": "integer"},
                            "end": {"type": "integer"}
                        },
                        "required": ["type", "value", "start", "end"]
                    }
                }
            },
            "required": ["entities"]
        }

    def _create_entity_prompt(self, text: str) -> str:
        """Create prompt for entity extraction."""
        return f"""Extract entities from the following Jakarta public transportation query:

"{text}"

Identify entities including:
- stations (MRT/KRL)
- POIs (landmarks, malls)
- terminals
- routes
- transport types
- obstacles
- facilities

Return structured JSON with entity mentions and their positions in the text."""

    async def extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract entities using Gemini."""
        try:
            response = self.gemini_model.generate_content(
                self._create_entity_prompt(text),
                generation_config=GenerationConfig(
                    temperature=0.1,
                    candidate_count=1,
                    max_output_tokens=1024,
                    response_mime_type="application/json",
                    response_schema=self._get_entity_schema()
                )
            )
            
            return json.loads(response.text)
            
        except Exception as e:
            print(f"Entity extraction error: {e}")
            return {"entities": []}

    async def process_text(self, text: str) -> Dict[str, Any]:
        """Process text through intent classification and entity extraction."""
        try:
            # Get intent from trained model
            intent_result = self.intent_classifier.predict(text)
            
            # Get entities from Gemini
            entity_result = await self.extract_entities(text)
            
            return {
                "intent": intent_result,
                "entities": entity_result.get("entities", [])
            }
            
        except Exception as e:
            print(f"Processing error: {e}")
            return {
                "intent": {"type": "unknown", "confidence": 0.0},
                "entities": []
            }

# Initialize speech processor with your model path
speech_processor = SpeechProcessor(intent_model_path='./models/intent_classifier')

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        print("Client connected to speech recognition")

        streaming_config = speech.StreamingRecognitionConfig(
            config=speech_processor.config, interim_results=True
        )

        with MicrophoneStream(16000, int(16000 / 10)) as stream:
            audio_generator = stream.generator()
            requests = (
                speech.StreamingRecognizeRequest(audio_content=content)
                for content in audio_generator
            )

            responses = speech_processor.client.streaming_recognize(
                streaming_config, requests
            )

            for response in responses:
                if not response.results:
                    continue

                result = response.results[0]
                if not result.alternatives:
                    continue

                transcript = result.alternatives[0].transcript

                if result.is_final:
                    try:
                        # Process through both models
                        classification = await speech_processor.process_text(transcript)
                        
                        await websocket.send_json({
                            "transcript": transcript,
                            "is_final": True,
                            "classification": classification,
                            "confidence": result.alternatives[0].confidence,
                            "timestamp": datetime.datetime.now().isoformat()
                        })
                        
                        print(f"Classification for: {transcript}")
                        print(json.dumps(classification, indent=2))
                        
                    except Exception as e:
                        print(f"Classification error: {e}")
                        await websocket.send_json({
                            "transcript": transcript,
                            "is_final": True,
                            "error": str(e),
                            "confidence": result.alternatives[0].confidence,
                            "timestamp": datetime.datetime.now().isoformat()
                        })
                else:
                    await websocket.send_json({
                        "transcript": transcript,
                        "is_final": False,
                        "confidence": result.alternatives[0].confidence,
                        "timestamp": datetime.datetime.now().isoformat()
                    })

    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "error": str(e),
                "timestamp": datetime.datetime.now().isoformat()
            })
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)