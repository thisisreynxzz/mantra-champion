import json
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from datetime import datetime

PROJECT_ID = 'ai-for-impact-bmth'
vertexai.init(project=PROJECT_ID, location="us-central1")


model = GenerativeModel("gemini-1.5-flash")

prompt = """Generate a diverse intent classification dataset for a Jakarta public transportation assistance system designed for visually impaired users, with these 3 classes:

1. asking_for_direction: Questions about how to get somewhere using TransJakarta, MRT, or KRL
Example: "How do I get to Blok M station from here using TransJakarta?"

2. analyzing_surroundings: Questions from visually impaired users about their immediate environment near public transport facilities. These questions should focus on:
- Identifying obstacles or hazards
- Locating important elements like doors, gates, or ticket machines
- Finding tactile paths or guide blocks
- Identifying nearby sounds or audio cues
- Understanding spatial layout of stations
Examples: 
- "Are there any stairs or obstacles in front of me?"
- "Where is the nearest tactile path to the MRT entrance?"

3. service_recommendation: Questions about recommended routes, transport types, or best options for travel
Example: "What's the most accessible route to Tanah Abang station?"

Make sure to include:
- Different variations of questions focusing on accessibility
- Variations between casual and formal language
- Specific mentions of Jakarta locations and transport types (TransJakarta, MRT, KRL)
- Questions about accessibility features and facilities
- Natural language variations
- Both formal and informal speaking styles
- Mix of short and detailed questions
- Make distinctable and differentiate for each class

Generate 50 examples, equal count for each class, with strong emphasis on accessibility-focused queries for analyzing_surroundings."""

response_schema = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": ["asking_for_direction", "analyzing_surroundings", "service_recommendation"]
            },
            "text": {
                "type": "string",
                "description": "The example question or request"
            }
        },
        "required": ["intent", "text"]
    }
}

# Generate the dataset
response = model.generate_content(
    prompt,
    generation_config=GenerationConfig(
        temperature=0.8,
        candidate_count=1,
        max_output_tokens=2048,
        response_mime_type="application/json",
        response_schema=response_schema
    )
)

# Parse the response text as JSON
data = json.loads(response.text)

# Create a filename with timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"jakarta_transport_intents_accessibility_{timestamp}.json"

# Save to JSON file with pretty printing
with open(filename, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Data saved to {filename}")

# Print sample of saved data
print("\nFirst few examples from the dataset:")
for item in data[:3]:
    print(f"\nIntent: {item['intent']}")
    print(f"Text: {item['text']}")