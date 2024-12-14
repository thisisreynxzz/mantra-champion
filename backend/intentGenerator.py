import json
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from datetime import datetime
import random
import time
import re

def init_vertexai(project_id, location="us-central1"):
    """Initialize VertexAI with project settings."""
    vertexai.init(project=project_id, location=location)
    return GenerativeModel("gemini-1.5-flash")

def create_prompt(batch_size=50):
    """Create a prompt with specified batch size."""
    return f"""Generate a diverse intent classification dataset for a Jakarta public transportation assistance system designed for visually impaired users, with these 3 classes:

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
- "Are there any potholes in this sidewalk?"
- "Where is the nearest tactile path to the MRT entrance?"

3. service_recommendation: Questions about recommended routes, transport types, or best options for travel
Example: "What's the most accessible route to Tanah Abang station?"

Generate {batch_size} examples with equal distribution across classes. Ensure:
- Different variations of questions focusing on accessibility
- Make variations between casual and formal language
- Make sure every class are differentiable
- Specific mentions of Jakarta locations and transport types
- Questions about accessibility features and facilities
- Natural language variations
- Both formal and informal speaking styles
- Mix of short and detailed questions
- Make each example unique and distinctly different from others
- Vary the locations mentioned across Jakarta
- Include different times of day and weather conditions
- Consider different user needs and scenarios for Jakartans"""

def get_response_schema():
    """Define the JSON schema for responses."""
    return {
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

def handle_quota_error(error_message, retry_count):
    """Handle quota exceeded errors with exponential backoff."""
    if "Quota exceeded" in str(error_message):
        # Start with 60 seconds for first retry, then increase exponentially
        wait_time = 60 * (2 ** retry_count)  # 60s, 120s, 240s, etc.
        max_wait = 300  # Cap at 5 minutes
        wait_time = min(wait_time, max_wait)
        print(f"\nQuota exceeded. Waiting {wait_time} seconds before retry (attempt {retry_count + 1})")
        time.sleep(wait_time)
        return True
    return False

def generate_batch(model, batch_size=50, temperature=0.8, max_retries=5):
    """Generate a single batch of examples with retry logic."""
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            response = model.generate_content(
                create_prompt(batch_size),
                generation_config=GenerationConfig(
                    temperature=temperature,
                    candidate_count=1,
                    max_output_tokens=2048,
                    response_mime_type="application/json",
                    response_schema=get_response_schema()
                )
            )
            return json.loads(response.text)
        except Exception as e:
            error_msg = str(e)
            if handle_quota_error(error_msg, retry_count):
                retry_count += 1
                continue
            else:
                print(f"Error generating batch: {error_msg}")
                return []
    
    print("Max retries reached. Moving on...")
    return []

def check_class_balance(dataset):
    """Check the balance of classes in the dataset."""
    class_counts = {}
    for item in dataset:
        class_counts[item['intent']] = class_counts.get(item['intent'], 0) + 1
    return class_counts

def check_duplicates(dataset):
    """Check for duplicate examples in the dataset."""
    texts = set()
    duplicates = []
    for item in dataset:
        if item['text'] in texts:
            duplicates.append(item['text'])
        texts.add(item['text'])
    return duplicates

def generate_full_dataset(target_size=10000, batch_size=50):
    """Generate the full dataset with specified target size."""
    PROJECT_ID = 'ai-for-impact-bmth'
    model = init_vertexai(PROJECT_ID)
    
    full_dataset = []
    batches_needed = (target_size + batch_size - 1) // batch_size
    
    for batch_num in range(batches_needed):
        # Vary temperature slightly for each batch to increase diversity
        temperature = 0.7 + (batch_num % 4) * 0.1  # Cycles through 0.7, 0.8, 0.9, 1.0
        
        # Generate batch with retry logic
        batch_data = generate_batch(model, batch_size, temperature)
        if batch_data:
            full_dataset.extend(batch_data)
            print(f"Generated {len(full_dataset)} examples out of {target_size}")
            
            # Add small delay between successful batches
            time.sleep(3)  # Base delay between successful batches
    
    # Balance classes if needed
    class_counts = check_class_balance(full_dataset)
    print("\nClass distribution:", class_counts)
    
    # Check for duplicates
    duplicates = check_duplicates(full_dataset)
    if duplicates:
        print(f"\nFound {len(duplicates)} duplicate examples")
        # Remove duplicates
        seen_texts = set()
        unique_dataset = []
        for item in full_dataset:
            if item['text'] not in seen_texts:
                unique_dataset.append(item)
                seen_texts.add(item['text'])
        full_dataset = unique_dataset
    
    # Save dataset
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"jakarta_transport_intents_{len(full_dataset)}_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(full_dataset, f, indent=2, ensure_ascii=False)
    
    print(f"\nDataset saved to {filename}")
    print(f"Final dataset size: {len(full_dataset)}")
    
    return full_dataset, filename

if __name__ == "__main__":
    dataset, filename = generate_full_dataset(target_size=10000)
    
    # Print sample of saved data
    print("\nSample examples from the dataset:")
    for item in random.sample(dataset, min(3, len(dataset))):
        print(f"\nIntent: {item['intent']}")
        print(f"Text: {item['text']}")