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
from typing import Dict, Any, List
import tensorflow as tf
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder
import pickle
import numpy as np
import re
from datetime import timedelta
from asyncio import Lock, sleep
from hashlib import md5

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RateLimitedGemini:
    def __init__(self, requests_per_minute: int = 60):
        self.lock = Lock()
        self.requests_per_minute = requests_per_minute
        self.requests = []
        self.retry_delay = 2

    async def execute(self, func, *args, **kwargs):
        async with self.lock:
            current_time = datetime.datetime.now()
            self.requests = [t for t in self.requests if current_time - t < timedelta(minutes=1)]
            
            while len(self.requests) >= self.requests_per_minute:
                await sleep(self.retry_delay)
                current_time = datetime.datetime.now()
                self.requests = [t for t in self.requests if current_time - t < timedelta(minutes=1)]

            try:
                result = await func(*args, **kwargs)
                self.requests.append(current_time)
                return result
            except Exception as e:
                if "429" in str(e):
                    await sleep(self.retry_delay)
                    return await self.execute(func, *args, **kwargs)
                raise e

class IntentClassifier:
    def __init__(self, model_path_prefix: str):
        self.model = tf.keras.models.load_model(f'{model_path_prefix}_model.h5')
        
        with open(f'{model_path_prefix}_vectorizer.pkl', 'rb') as f:
            self.vectorizer = pickle.load(f)
        
        with open(f'{model_path_prefix}_label_encoder.pkl', 'rb') as f:
            self.label_encoder = pickle.load(f)

    def predict(self, text: str) -> Dict[str, Any]:
        X = self.vectorizer.transform([text]).toarray()
        probs = self.model.predict(X)[0]
        pred_class = np.argmax(probs)
        confidence = float(probs[pred_class])
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
        self.rate_limiter = RateLimitedGemini()
        self.entity_cache = {}
        self.cache_ttl = 3600
        
        # Entity patterns for fallback
        self.entities_patterns = {
            'station': [
                r'(Bundaran HI|Dukuh Atas|Bendungan Hilir|Setiabudi|Istora|Senayan|ASEAN|Blok M|Blok A|Haji Nawi|Fatmawati|Cipete Raya|Lebak Bulus)',
                r'(Tanah Abang|Sudirman|Manggarai|Cikini|Gondangdia|Juanda|Sawah Besar|Jayakarta|Jakarta Kota|Tebet|Cawang|Duren Kalibata|Pasar Minggu)'
            ],
            'poi': [
                r'(Grand Indonesia|Plaza Indonesia|Pacific Place|Senayan City|Plaza Senayan|Sarinah|Central Park|Taman Anggrek|Kota Kasablanka)',
                r'(Monas|Glodok|Kota Tua|Thamrin City)'
            ],
            'transport_type': [
                r'(MRT|KRL|TransJakarta|bus|train|kereta)'
            ],
            'facility': [
                r'(elevator|escalator|lift|stairs|ramp|toilet|gate|exit|entrance)'
            ]
        }
        self.compiled_patterns = {
            entity_type: [re.compile(pattern, re.IGNORECASE) 
                         for pattern in patterns]
            for entity_type, patterns in self.entities_patterns.items()
        }

    def init_vertexai(self):
        vertexai.init(project=self.project_id, location="us-central1")
        return GenerativeModel("gemini-1.5-flash")

    def get_speech_config(self) -> speech.RecognitionConfig:
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

    def _cache_key(self, text: str) -> str:
        return md5(text.lower().strip().encode()).hexdigest()

    def fallback_entity_extraction(self, text: str) -> Dict[str, List]:
        entities = []
        
        for entity_type, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    entities.append({
                        "type": entity_type,
                        "value": match.group(),
                        "start": match.start(),
                        "end": match.end()
                    })
        
        return {"entities": entities}

    def _get_entity_schema(self) -> Dict:
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
        cache_key = self._cache_key(text)
        current_time = datetime.datetime.now().timestamp()

        if cache_key in self.entity_cache:
            cached_result, timestamp = self.entity_cache[cache_key]
            if current_time - timestamp < self.cache_ttl:
                return cached_result

        try:
            async def _extract():
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

            result = await self.rate_limiter.execute(_extract)
            self.entity_cache[cache_key] = (result, current_time)
            
            # Clean old cache entries
            self.entity_cache = {
                k: v for k, v in self.entity_cache.items()
                if current_time - v[1] < self.cache_ttl
            }
            
            return result
            
        except Exception as e:
            print(f"Entity extraction error: {e}")
            print("Using fallback entity extraction")
            return self.fallback_entity_extraction(text)

    async def process_text(self, text: str) -> Dict[str, Any]:
        try:
            # Get intent from trained model
            intent_result = self.intent_classifier.predict(text)
            
            # Get entities with fallback and caching
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