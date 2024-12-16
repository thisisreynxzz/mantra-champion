# src/speech_processor.py
from google.cloud import speech
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
import random
from typing import Dict, Any, List
import json
import re
from config import SA_JSON_FILE_PATH

class SpeechProcessor:
    def __init__(self, intent_classifier):
        self.client = speech.SpeechClient.from_service_account_file(SA_JSON_FILE_PATH)
        self.intent_classifier = intent_classifier
        self.project_id = 'ai-for-impact-bmth'
        
        # Initialize Vertex AI
        vertexai.init(project=self.project_id, location="us-central1")
        self.gemini_model = GenerativeModel("gemini-1.5-flash")
        
        # Response templates
        self.response_templates = {
            'asking_for_direction': [
                "I'll guide you to {destination}. The best route will be shown on the map.",
                "Let me help you get to {destination}. I'm calculating the best transit route for you.",
                "I'll show you how to reach {destination} using public transportation.",
            ],
            'analyzing_surroundings': [
                "I'll scan the area around you to identify any obstacles or points of interest.",
                "Let me analyze your surroundings to help you navigate safely.",
                "I'll check the environment and highlight any important objects or facilities.",
            ],
            'service_recommendation': [
                "I'll find the best transit options and services available near you.",
                "Let me check which transportation services would work best for your needs.",
                "I'll recommend the most convenient transit options in this area.",
            ]
        }
        
        # Entity patterns for extraction
        self.entity_patterns = {
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
                    "MANTRA", "navigation", "directions", "help",
                    "Bundaran HI", "Dukuh Atas", "Bendungan Hilir",
                    "MRT", "KRL", "TransJakarta", "halte", "stasiun",
                    "elevator", "escalator", "toilet", "exit", "entrance"
                ],
                "boost": 20.0
            }]
        )

    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        entities = []
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    entities.append({
                        "type": entity_type,
                        "value": match.group(),
                        "start": match.start(),
                        "end": match.end()
                    })
        return entities

    def generate_response(self, intent: Dict[str, Any], entities: List[Dict[str, Any]]) -> str:
        if not intent or 'type' not in intent:
            return "I'm not sure what you're asking for. Could you please rephrase that?"
            
        intent_type = intent['type']
        
        if intent_type == 'asking_for_direction':
            destination = next(
                (e['value'] for e in entities if e['type'] in ['station', 'poi']),
                None
            )
            if destination:
                template = random.choice(self.response_templates['asking_for_direction'])
                return template.format(destination=destination)
            return "Could you please specify where you'd like to go?"
            
        elif intent_type == 'analyzing_surroundings':
            facilities = [e['value'] for e in entities if e['type'] == 'facility']
            response = random.choice(self.response_templates['analyzing_surroundings'])
            if facilities:
                response += f" I'll pay special attention to the {', '.join(facilities)} you mentioned."
            return response
            
        elif intent_type == 'service_recommendation':
            transport_types = [e['value'] for e in entities if e['type'] == 'transport_type']
            response = random.choice(self.response_templates['service_recommendation'])
            if transport_types:
                response += f" I'll focus on {', '.join(transport_types)} services."
            return response
            
        return "I'm not sure how to help with that. Could you try asking in a different way?"

    async def process_transcript(self, transcript: str) -> Dict[str, Any]:
        # Get intent
        intent = self.intent_classifier.predict(transcript)
        
        # Extract entities
        entities = self.extract_entities(transcript)
        
        # Generate response
        response = self.generate_response(intent, entities)
        
        return {
            "intent": intent,
            "entities": entities,
            "agent_response": response
        }