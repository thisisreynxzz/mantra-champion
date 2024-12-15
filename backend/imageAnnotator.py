import google.generativeai as genai
from PIL import Image
import cv2
import numpy as np
import json
import os
from typing import List, Dict
import requests
from urllib.parse import urlparse
import shutil
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import time

class GoogleYOLOAnnotator:
    def __init__(self, goofgle_api_key: str, google_cx: str, gemini_api_key: str):
        self.google_api_key = google_api_key
        self.google_cx = google_cx
        
        # Initialize Gemini
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Class mapping for YOLO format
        self.class_mapping = {}
        self.current_class_id = 0
        
        # Color mapping for visualization
        self.colors = plt.cm.rainbow(np.linspace(0, 1, 20))  # 20 distinct colors

    def create_detection_prompt(self, target_objects: List[str]) -> str:
        """Create a structured prompt for object detection"""
        return f"""Analyze this image and detect the following objects: {', '.join(target_objects)}.
For each object found, provide its location using normalized coordinates (0-1000 range).
Return ONLY a JSON array with this exact format, with no additional text:
[
  {{
    "bbox": [ymin, xmin, ymax, xmax],
    "class": "object_class",
    "confidence": 0.95
  }}
]"""

    def download_images(self, query: str, num_images: int, output_dir: str) -> List[str]:
        """Download images from Google Search API with pagination"""
        base_url = "https://www.googleapis.com/customsearch/v1"
        image_paths = []
        
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'images'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'labels'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'visualizations'), exist_ok=True)

        # Calculate number of pages needed
        pages_needed = (num_images + 9) // 10  # Ceiling division by 10
        
        for page in range(pages_needed):
            start_index = page * 10 + 1
            
            params = {
                'q': query,
                'key': self.google_api_key,
                'cx': self.google_cx,
                'searchType': 'image',
                'num': min(10, num_images - len(image_paths)),
                'start': start_index
            }

            try:
                response = requests.get(base_url, params=params)
                response.raise_for_status()
                search_results = response.json()

                if 'items' not in search_results:
                    print(f"No more images found for page {page + 1}")
                    break

                for i, item in enumerate(search_results['items'], start_index):
                    if len(image_paths) >= num_images:
                        break

                    try:
                        # Download image
                        img_response = requests.get(item['link'], timeout=10)
                        img_response.raise_for_status()

                        # Save image
                        filename = f"{query.replace(' ', '_')}_{i}.jpg"
                        filepath = os.path.join(output_dir, 'images', filename)
                        
                        with open(filepath, 'wb') as f:
                            f.write(img_response.content)
                        
                        image_paths.append(filepath)
                        print(f"Downloaded {len(image_paths)}/{num_images}: {filename}")

                    except Exception as e:
                        print(f"Error downloading image {i}: {str(e)}")
                        continue

            except Exception as e:
                print(f"Error in download process for page {page + 1}: {str(e)}")
                break
                
            # Add a small delay between pages to avoid rate limiting
            if page < pages_needed - 1:
                time.sleep(1)

        return image_paths

    def convert_to_yolo_format(self, detection: Dict, img_width: int, img_height: int) -> tuple:
        """Convert from [ymin, xmin, ymax, xmax] to YOLO format [x_center, y_center, width, height]"""
        ymin, xmin, ymax, xmax = map(float, detection['bbox'])
        
        # Normalize coordinates from 0-1000 to 0-1 range
        xmin = xmin / 1000
        ymin = ymin / 1000
        xmax = xmax / 1000
        ymax = ymax / 1000
        
        # Calculate YOLO format
        x_center = (xmin + xmax) / 2
        y_center = (ymin + ymax) / 2
        width = xmax - xmin
        height = ymax - ymin
        
        # Get or assign class id
        class_name = detection['class']
        if class_name not in self.class_mapping:
            self.class_mapping[class_name] = self.current_class_id
            self.current_class_id += 1
        
        class_id = self.class_mapping[class_name]
        
        return class_id, x_center, y_center, width, height

    def visualize_annotations(self, image_path: str, label_path: str, output_path: str):
        """Visualize YOLO annotations on the image"""
        # Read image
        img = cv2.imread(image_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        height, width = img.shape[:2]
        
        # Create figure and axis
        fig, ax = plt.subplots(1)
        ax.imshow(img)
        
        # Read annotations
        if os.path.exists(label_path):
            with open(label_path, 'r') as f:
                lines = f.readlines()
                
            # Create reverse class mapping
            rev_class_mapping = {v: k for k, v in self.class_mapping.items()}
                
            # Draw each annotation
            for line in lines:
                class_id, x_center, y_center, box_width, box_height = map(float, line.strip().split())
                
                # Convert YOLO coordinates to pixel coordinates
                x_min = int((x_center - box_width/2) * width)
                y_min = int((y_center - box_height/2) * height)
                box_width = int(box_width * width)
                box_height = int(box_height * height)
                
                # Create rectangle patch
                color = self.colors[int(class_id) % len(self.colors)]
                rect = patches.Rectangle(
                    (x_min, y_min),
                    box_width,
                    box_height,
                    linewidth=2,
                    edgecolor=color,
                    facecolor='none'
                )
                ax.add_patch(rect)
                
                # Add label
                class_name = rev_class_mapping[class_id]
                plt.text(
                    x_min,
                    y_min - 5,
                    class_name,
                    color=color,
                    fontsize=8,
                    bbox=dict(facecolor='white', alpha=0.8, edgecolor='none')
                )
        
        # Remove axes
        plt.axis('off')
        
        # Save visualization
        plt.savefig(output_path, bbox_inches='tight', pad_inches=0)
        plt.close()

    def process_images(self, image_paths: List[str], target_objects: List[str], output_dir: str):
        """Process images and create YOLO annotations"""
        for img_path in image_paths:
            try:
                # Load and analyze image
                image = Image.open(img_path)
                width, height = image.size
                
                # Get detections from Gemini
                response = self.model.generate_content(
                    [image, self.create_detection_prompt(target_objects)],
                    generation_config=genai.GenerationConfig(
                        temperature=0.1,
                        candidate_count=1,
                        max_output_tokens=1024
                    )
                )
                
                # Parse detections
                try:
                    json_str = response.text[response.text.find('['):response.text.rfind(']')+1]
                    detections = json.loads(json_str)
                    
                    # Create YOLO annotation file
                    base_name = os.path.splitext(os.path.basename(img_path))[0]
                    label_path = os.path.join(output_dir, 'labels', f"{base_name}.txt")
                    
                    with open(label_path, 'w') as f:
                        for det in detections:
                            # Convert to YOLO format
                            class_id, x_center, y_center, width, height = self.convert_to_yolo_format(det, width, height)
                            # Write YOLO format line: <class> <x_center> <y_center> <width> <height>
                            f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")
                    
                    # Create visualization
                    vis_path = os.path.join(output_dir, 'visualizations', f"{base_name}_annotated.jpg")
                    self.visualize_annotations(img_path, label_path, vis_path)
                    
                    print(f"Created YOLO annotations and visualization for {base_name}")
                
                except json.JSONDecodeError as e:
                    print(f"Error parsing detections for {img_path}: {e}")
                    continue
                
            except Exception as e:
                print(f"Error processing {img_path}: {e}")
                continue
        
        # Save class mapping
        with open(os.path.join(output_dir, 'classes.txt'), 'w') as f:
            for class_name, class_id in sorted(self.class_mapping.items(), key=lambda x: x[1]):
                f.write(f"{class_name}\n")

    def display_dataset_summary(self, output_dir: str):
        """Display summary of the created dataset"""
        print("\nDataset Summary:")
        print("-" * 50)
        
        # Count images
        images_dir = os.path.join(output_dir, 'images')
        num_images = len([f for f in os.listdir(images_dir) if f.endswith(('.jpg', '.jpeg', '.png'))])
        print(f"Total images: {num_images}")
        
        # Count annotations
        labels_dir = os.path.join(output_dir, 'labels')
        num_annotations = 0
        class_counts = {}
        
        for label_file in os.listdir(labels_dir):
            if label_file.endswith('.txt'):
                with open(os.path.join(labels_dir, label_file), 'r') as f:
                    annotations = f.readlines()
                    num_annotations += len(annotations)
                    
                    # Count objects per class
                    for ann in annotations:
                        class_id = int(ann.split()[0])
                        class_counts[class_id] = class_counts.get(class_id, 0) + 1
        
        print(f"Total annotations: {num_annotations}")
        print("\nObjects per class:")
        
        # Load class names
        rev_class_mapping = {v: k for k, v in self.class_mapping.items()}
        for class_id, count in sorted(class_counts.items()):
            class_name = rev_class_mapping[class_id]
            print(f"  {class_name}: {count}")

def main():
    # API credentials
    GOOGLE_API_KEY = "AIzaSyBrVnJYSMltRVP5PA3DfER_hc64vjxLp0g"
    GOOGLE_CX = "107e304e2cb5945f0"
    GEMINI_API_KEY = "AIzaSyBUuw-d2wcLmLGGCG730QrF19370FZjoFg"
    
    # Initialize annotator
    annotator = GoogleYOLOAnnotator(GOOGLE_API_KEY, GOOGLE_CX, GEMINI_API_KEY)
    
    # Define search queries and their parameters
    num_images = 100
    search_configs = [
        {
            "query": "transjakarta bus terminal halte",
            "num_images": num_images,
            "subfolder": "transjakarta"
        },
        {
            "query": "pothole in indonesia sidewalk",
            "num_images": num_images,
            "subfolder": "potholes"
        },
        {
            "query": "halte transjakarta",
            "num_images": num_images,
            "subfolder": "halte"
        },
        {
            "query": "tactile path jakarta sidewalk",
            "num_images": num_images,
            "subfolder": "tactile"
        },
        {
            "query": "obstacle on jakarta sidewalk",
            "num_images": num_images,
            "subfolder": "obstacles"
        }
    ]
    
    # Objects to detect across all images
    target_objects = [
        'transjakarta_bus',
        'pothole',
        'tactile_path',
        'obstacle',
        'escalator',
        'stairs',
        'halte',
        'pedestrian',
        'traffic_light',
        'crosswalk'
    ]
    
    base_output_dir = 'gemini_for_yolo_dataset'
    all_image_paths = []
    
    # Process each search configuration
    for config in search_configs:
        print(f"\nProcessing search query: {config['query']}")
        
        # Create subfolder for this query
        query_output_dir = os.path.join(base_output_dir, config['subfolder'])
        os.makedirs(query_output_dir, exist_ok=True)
        
        # Download images for this query
        image_paths = annotator.download_images(
            query=config['query'],
            num_images=config['num_images'],
            output_dir=query_output_dir
        )
        
        # Process images and create annotations
        annotator.process_images(image_paths, target_objects, query_output_dir)
        
        # Add to total image paths
        all_image_paths.extend(image_paths)
        
        # Display summary for this query
        print(f"\nSummary for query '{config['query']}':")
        annotator.display_dataset_summary(query_output_dir)
    
    # Create combined dataset
    print("\nCreating combined dataset...")
    combined_output_dir = os.path.join(base_output_dir, 'combined')
    os.makedirs(os.path.join(combined_output_dir, 'images'), exist_ok=True)
    os.makedirs(os.path.join(combined_output_dir, 'labels'), exist_ok=True)
    os.makedirs(os.path.join(combined_output_dir, 'visualizations'), exist_ok=True)
    
    # Copy all files to combined directory
    for config in search_configs:
        query_dir = os.path.join(base_output_dir, config['subfolder'])
        
        # Copy images
        for file in os.listdir(os.path.join(query_dir, 'images')):
            src = os.path.join(query_dir, 'images', file)
            dst = os.path.join(combined_output_dir, 'images', f"{config['subfolder']}_{file}")
            shutil.copy2(src, dst)
        
        # Copy labels
        for file in os.listdir(os.path.join(query_dir, 'labels')):
            src = os.path.join(query_dir, 'labels', file)
            dst = os.path.join(combined_output_dir, 'labels', f"{config['subfolder']}_{file}")
            shutil.copy2(src, dst)
        
        # Copy visualizations
        for file in os.listdir(os.path.join(query_dir, 'visualizations')):
            src = os.path.join(query_dir, 'labels', file)
            dst = os.path.join(combined_output_dir, 'visualizations', f"{config['subfolder']}_{file}")
            shutil.copy2(src, dst)
    
    # Save combined class mapping
    with open(os.path.join(combined_output_dir, 'classes.txt'), 'w') as f:
        for class_name, class_id in sorted(annotator.class_mapping.items(), key=lambda x: x[1]):
            f.write(f"{class_name}\n")
    
    # Display final combined dataset summary
    print("\nFinal Combined Dataset Summary:")
    print("=" * 50)
    annotator.display_dataset_summary(combined_output_dir)

if __name__ == "__main__":
    main()