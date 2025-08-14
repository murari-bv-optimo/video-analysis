import os
import json
import base64
from openai import OpenAI
from dotenv import load_dotenv
from PIL import Image
import uuid
import asyncio
from typing import List, Dict, Optional
from .models import AIAgentInstructions

load_dotenv()

class RoomAnalyzer:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.ai_instructions = AIAgentInstructions()
        # Configuration for parallel processing
        self.max_concurrent_requests = int(os.getenv('MAX_CONCURRENT_REQUESTS', '5'))
        self.request_delay = float(os.getenv('REQUEST_DELAY', '0.2'))  # 200ms between requests
        
    def encode_image(self, image_path: str) -> str:
        """Encode image to base64 for API"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    async def analyze_room_async(self, image_path: str) -> Optional[str]:
        """Analyze a single room image using GPT-4 Vision"""
        base64_image = self.encode_image(image_path)
        
        prompt = f"""
        {self.ai_instructions.information}
        {self.ai_instructions.instruction}
        {self.ai_instructions.condition}

        Analyze this room image and provide a comprehensive assessment focusing on:
        
        1. Room type identification (bedroom, living_room, kitchen, bathroom, etc.)
        2. Luxury tier assessment (high, medium, low based on visible quality, materials, and furnishings)
        3. Estimated room area in square meters
        4. Detailed condition assessment of all visible elements
        5. Accurate count of all objects and furnishings
        
        For elements not clearly visible, make reasonable assumptions based on typical room standards.
        
        Structure your analysis covering:
        - Wiring and electrical systems
        - HVAC systems (AC units, fans, ventilation)
        - Flooring material and condition
        - Wall condition, paint, and decorative elements
        - Ceiling material and condition
        - Windows and doors
        - All fixtures (lights, fans, mirrors)
        - All furnishings with exact counts
        - Kitchen appliances (if applicable)
        - Balcony details (if visible)
        
        Be specific with counts and conditions. State assumptions clearly.
        """
        
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                                }
                            ]
                        }
                    ],
                    max_tokens=4000
                )
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error analyzing image {image_path}: {str(e)}")
            return None

    async def convert_to_structured_json_async(self, analysis_text: str, room_id: str) -> Optional[Dict]:
        """Convert analysis text to structured JSON format"""
        
        schema_prompt = f"""
        Convert the following room analysis into the exact JSON format specified below.
        Make reasonable estimates for any missing information based on the analysis.
        
        Analysis: {analysis_text}
        
        Return ONLY valid JSON matching this structure:
        {{
            "room_id": "{room_id}",
            "room_type": "bedroom | living_room | kitchen | bathroom | balcony | dining | study | utility | other",
            "estimated_area_sqm": number,
            "features": {{
                "wiring": {{
                    "status": "good | fair | poor",
                    "visible_damage": false,
                    "exposed_wires": false
                }},
                "hvac": {{
                    "has_ac": boolean,
                    "ac_units": number,
                    "fan_count": number,
                    "ventilation_quality": "good | fair | poor"
                }},
                "flooring": {{
                    "material": "tile | wood | concrete | vinyl | carpet | other",
                    "condition": "good | cracked | stained | worn"
                }},
                "walls": {{
                    "paint_color": "string",
                    "paint_condition": "good | peeling | stained | damp",
                    "frame_count": number,
                    "frame_quality": "basic | decorative | premium"
                }},
                "ceiling": {{
                    "material": "plaster | drywall | wood | exposed | other",
                    "condition": "good | water_damage | cracked | moldy"
                }},
                "doors_and_windows": {{
                    "window_count": number,
                    "window_type": "casement | sliding | fixed | louvered | other",
                    "door_count": number,
                    "door_type": "wood | glass | metal | other",
                    "balcony_access": boolean
                }},
                "fixtures": {{
                    "lights": {{
                        "count": number,
                        "type": "LED | fluorescent | incandescent | other",
                        "condition": "good | flickering | broken"
                    }},
                    "fans": {{
                        "count": number,
                        "type": "ceiling | wall | table | other",
                        "condition": "good | noisy | broken"
                    }},
                    "mirrors": {{
                        "count": number,
                        "size": "small | medium | large",
                        "quality": "basic | decorative | premium"
                    }},
                    "decorations": {{
                        "count": number,
                        "types": ["painting", "sculpture", "wall_hangings", "plants", "other"]
                    }}
                }},
                "furnishings": [
                    {{
                        "label": "sofa | bed | table | chair | wardrobe | shelf | curtain | carpet | other",
                        "quantity": number,
                        "quality": "new | good | worn | damaged",
                        "material": "wood | metal | plastic | fabric | other"
                    }}
                ],
                "kitchen_appliances": {{
                    "cooking_stove": {{
                        "present": boolean,
                        "type": "gas | electric | induction",
                        "burners": number,
                        "condition": "good | stained | rusty | broken"
                    }},
                    "chimney": {{
                        "present": boolean,
                        "type": "wall_mounted | island | integrated",
                        "condition": "good | greasy | damaged"
                    }},
                    "sink": {{
                        "material": "steel | ceramic | granite | other",
                        "condition": "clean | clogged | damaged"
                    }}
                }},
                "balcony": {{
                    "present": boolean,
                    "estimated_area_sqm": number,
                    "has_railing": boolean,
                    "railing_material": "steel | glass | concrete | wood | other",
                    "flooring_material": "tile | stone | concrete | other",
                    "security_grill": boolean
                }}
            }},
            "object_counts": {{
                "sofa": number,
                "table": number,
                "chair": number,
                "mirror": number,
                "fan": number,
                "light": number,
                "plant": number,
                "frame": number,
                "window": number,
                "wardrobe": number,
                "cooking_stove": number,
                "curtain": number,
                "decoration": number
            }}
        }}
        """
        
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": schema_prompt}],
                    max_tokens=1200
                )
            )
            
            json_text = response.choices[0].message.content.strip()
            
            if json_text.startswith('```json'):
                json_text = json_text[7:]
            if json_text.endswith('```'):
                json_text = json_text[:-3]
            
            return json.loads(json_text)
            
        except Exception as e:
            print(f"Error converting analysis to JSON: {str(e)}")
            return None

    async def process_single_image_async(self, image_path: str, room_id: str, room_number: int) -> Optional[Dict]:
        """Process a single image asynchronously"""
        print(f"🔍 Analyzing room {room_number}: {image_path}")
        
        analysis = await self.analyze_room_async(image_path)
        if analysis:
            room_data = await self.convert_to_structured_json_async(analysis, room_id)
            if room_data:
                print(f"✓ Room {room_number} analyzed successfully")
                return room_data
            else:
                print(f"✗ Failed to process room {room_number}")
        else:
            print(f"✗ Failed to analyze room {room_number}")
        
        return None

    async def process_multiple_images_async(self, image_paths: List[str]) -> List[Dict]:
        """Process multiple images in parallel for faster processing while respecting rate limits."""
        if not image_paths:
            return []

        print(f"\n📸 Processing {len(image_paths)} images in parallel (max {self.max_concurrent_requests} concurrent)...")

        # Create a semaphore to limit concurrent API requests
        semaphore = asyncio.Semaphore(self.max_concurrent_requests)
        
        # Create tasks for all images to be processed concurrently
        tasks = []
        for i, image_path in enumerate(image_paths, 1):
            room_id = f"room_{i:03d}"
            # Add a small staggered delay to avoid overwhelming the API
            delay = (i - 1) * self.request_delay
            task = self.process_single_image_with_semaphore(image_path, room_id, i, delay, semaphore)
            tasks.append(task)

        # Process all images concurrently
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out failed results and exceptions
            rooms = []
            for i, result in enumerate(results, 1):
                if isinstance(result, dict):
                    rooms.append(result)
                    print(f"✓ Room {i} analyzed successfully")
                elif isinstance(result, Exception):
                    print(f"✗ Room {i} failed with error: {str(result)}")
                else:
                    print(f"✗ Room {i} failed - no result returned")
            
            print(f"🎯 Successfully processed {len(rooms)} out of {len(image_paths)} images")
            return rooms
            
        except Exception as e:
            print(f"❌ Error during parallel processing: {str(e)}")
            return []

    async def process_single_image_with_semaphore(self, image_path: str, room_id: str, room_number: int, delay: float, semaphore: asyncio.Semaphore) -> Optional[Dict]:
        """Process a single image with semaphore control and delay for rate limiting"""
        if delay > 0:
            await asyncio.sleep(delay)
        
        async with semaphore:
            return await self.process_single_image_async(image_path, room_id, room_number)

    def generate_house_summary(self, rooms: List[Dict]) -> Dict:
        """Generate summary statistics for the entire house"""
        if not rooms:
            return {}
        
        total_rooms = len(rooms)
        rooms_with_balcony = sum(1 for room in rooms if room['features']['balcony']['present'])
        total_windows = sum(room['features']['doors_and_windows']['window_count'] for room in rooms)
        total_doors = sum(room['features']['doors_and_windows']['door_count'] for room in rooms)
        total_furnishings = sum(len(room['features']['furnishings']) for room in rooms)
        
        unique_objects = set()
        for room in rooms:
            for obj_type, count in room['object_counts'].items():
                if count > 0:
                    unique_objects.add(obj_type)
        
        return {
            "total_rooms": total_rooms,
            "rooms_with_balcony": rooms_with_balcony,
            "total_windows": total_windows,
            "total_doors": total_doors,
            "total_furnishings": total_furnishings,
            "unique_object_types_detected": list(unique_objects)
        }
    
    async def analyze_images(self, image_paths: List[str], house_id: str = None) -> Dict:
        """Main analysis function for web interface"""
        if house_id is None:
            house_id = str(uuid.uuid4())
        
        rooms = await self.process_multiple_images_async(image_paths)
        
        if rooms:
            house_summary = self.generate_house_summary(rooms)
            
            final_report = {
                "house_id": house_id,
                "assumptions": {
                    "location": "India",
                    "notes": "Land cost, local variations, and external factors excluded"
                },
                "rooms": rooms,
                "house_summary": house_summary
            }
            
            # Save report
            output_dir = os.getenv('OUTPUT_DIR', 'outputs')
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, f"house_analysis_{house_id[:8]}.json")
            
            with open(output_file, 'w') as f:
                json.dump(final_report, f, indent=2)
            
            return {
                "status": "success",
                "house_id": house_id,
                "total_rooms": len(rooms),
                "output_file": output_file,
                "report": final_report
            }
        else:
            return {
                "status": "failed",
                "house_id": house_id,
                "total_rooms": 0,
                "output_file": None,
                "report": None
            }
