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
import random

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
        
        # Response templates
        self.response_templates = {
            'asking_for_direction': [
                "I'll guide you to {destination}. The best route will be shown on the map.",
                "Let me help you get to {destination}. I'm calculating the best transit route for you.",
                "I'll show you how to reach {destination} using public transportation.",
                "I'm plotting the route to {destination} for you now.",
                "Let me find the best way to get you to {destination}."
            ],
            'analyzing_surroundings': [
                "I'll scan the area around you to identify any obstacles or points of interest.",
                "Let me analyze your surroundings to help you navigate safely.",
                "I'll check the environment and highlight any important objects or facilities.",
                "Starting environmental scan to help you navigate better.",
                "I'll identify the important features around you."
            ],
            'service_recommendation': [
                "I'll find the best transit options and services available near you.",
                "Let me check which transportation services would work best for your needs.",
                "I'll recommend the most convenient transit options in this area.",
                "I'll help you find the most suitable transportation services.",
                "Let me suggest the best transit options for your journey."
            ]
        }
        
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
                    
                    # Common Place Types and Facilities
                    "halte", "stasiun", "terminal", "mall", "plaza",
                    "elevator", "escalator", "toilet", "gate", "exit", "entrance"
                ],
                "boost": 20.0
            }],
            audio_channel_count=1,
            enable_separate_recognition_per_channel=False,
        )

    def _generate_direction_response(self, entities: List[Dict]) -> str:
        destination = None
        transport_type = None
        
        for entity in entities:
            if entity['type'] in ['station', 'poi', 'terminal']:
                destination = entity['value']
            elif entity['type'] == 'transport_type':
                transport_type = entity['value']
        
        if destination:
            base_response = random.choice(self.response_templates['asking_for_direction'])
            response = base_response.format(destination=destination)
            
            if transport_type:
                response += f" We'll use the {transport_type} for this journey."
            
            # Add estimated time if available
            response += " Once you confirm, I'll show you the detailed route with estimated travel time."
            
            return response
        return "Could you please specify where you'd like to go?"

    def _generate_surroundings_response(self, entities: List[Dict]) -> str:
        facilities = [e['value'] for e in entities if e['type'] in ['facility', 'obstacle']]
        
        response = random.choice(self.response_templates['analyzing_surroundings'])
        
        if facilities:
            response += f" I'll pay special attention to the {', '.join(facilities)} you mentioned."
        
        response += " Camera is now active to help you navigate."
            
        return response

    def _generate_service_response(self, entities: List[Dict]) -> str:
        transport_types = [e['value'] for e in entities if e['type'] == 'transport_type']
        
        response = random.choice(self.response_templates['service_recommendation'])
        
        if transport_types:
            response += f" I'll focus on {', '.join(transport_types)} services."
        
        response += " Please wait while I gather the latest service information."
            
        return response

    def _generate_agent_response(self, intent: Dict, entities: List[Dict]) -> str:
        if not intent or 'type' not in intent:
            return "I'm not sure what you're asking for. Could you please rephrase that?"
            
        intent_type = intent['type']
        
        if intent_type == 'asking_for_direction':
            return self._generate_direction_response(entities)
        elif intent_type == 'analyzing_surroundings':
            return self._generate_surroundings_response(entities)
        elif intent_type == 'service_recommendation':
            return self._generate_service_response(entities)
        else:
            return "I'm not sure how to help with that. Could you try asking in a different way?"

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
            
            # Generate agent response
            agent_response = self._generate_agent_response(
                intent_result, 
                entity_result.get("entities", [])
            )
            
            return {
                "intent": intent_result,
                "entities": entity_result.get("entities", []),
                "agent_response": agent_response
            }
            
        except Exception as e:
            print(f"Processing error: {e}")
            return {
                "intent": {"type": "unknown", "confidence": 0.0},
                "entities": [],
                "agent_response": "I'm having trouble understanding that. Could you please try again?"
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
                        # Process the final transcript
                        classification = await speech_processor.process_text(transcript)
                        
                        # Prepare the response with all the information
                        response_data = {
                            "transcript": transcript,
                            "is_final": True,
                            "classification": {
                                "intent": classification["intent"],
                                "entities": classification["entities"]
                            },
                            "agent_response": classification["agent_response"],
                            "confidence": result.alternatives[0].confidence,
                            "timestamp": datetime.datetime.now().isoformat()
                        }
                        
                        # Send the response to the client
                        await websocket.send_json(response_data)
                        
                        # Log the classification and response
                        print("\n=== Speech Processing Results ===")
                        print(f"Transcript: {transcript}")
                        print(f"Intent: {classification['intent']}")
                        print(f"Entities: {classification['entities']}")
                        print(f"Agent Response: {classification['agent_response']}")
                        print("================================\n")
                        
                    except Exception as e:
                        print(f"Classification error: {e}")
                        error_response = {
                            "transcript": transcript,
                            "is_final": True,
                            "error": str(e),
                            "confidence": result.alternatives[0].confidence,
                            "timestamp": datetime.datetime.now().isoformat()
                        }
                        await websocket.send_json(error_response)
                else:
                    # Send interim results
                    interim_response = {
                        "transcript": transcript,
                        "is_final": False,
                        "confidence": result.alternatives[0].confidence,
                        "timestamp": datetime.datetime.now().isoformat()
                    }
                    await websocket.send_json(interim_response)

    except websocket.exceptions.ConnectionClosed:
        print("Client disconnected normally")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            error_message = {
                "error": str(e),
                "timestamp": datetime.datetime.now().isoformat()
            }
            await websocket.send_json(error_message)
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass

@app.get("/health")
async def health_check():
    """Health check endpoint to verify the server is running."""
    return {"status": "healthy", "timestamp": datetime.datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000, 
        log_level="info",
        reload=False  # Set to True for development
    )