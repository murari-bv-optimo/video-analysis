from dotenv import load_dotenv
import requests
import os
from openai import OpenAI
import base64

load_dotenv()

room_object_list = ["couch", "light", "table", "chair", "window", "decoration", "curtain", "wardrobe", "fan", "plant"]

client = OpenAI(api_key=os.getenv("openai_api_key"))

image_path=input("Enter image path: ")

def image_to_base64(image_path="aesthetic-room-decor.jpg"):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def generate_room_report(image_base64):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You're an interior architect. Analyze the image and produce a 100-word condition report including wiring, HVAC, flooring, paint, ceiling, estimated area (important), and security features. Also classify the room as high, medium, or low tier."
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Please assess this room:"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                ]
            }
        ]
    )
    return response.choices[0].message.content

def detect_object_counts(image_path):
    object_count_string=""
    for object in room_object_list:

        url = "https://api.va.landing.ai/v1/tools/agentic-object-detection"
        files = {
            "image": open(image_path, "rb")
        }
        data = {
        "prompts": object,
        "model": "agentic"
        }
        headers = {
        "Authorization": "Basic " + os.getenv("landingai_api_key")
        }
        response = requests.post(url, files=files, data=data, headers=headers)
        result=response.json()
        counter = 0
        for item in result["data"][0]:
            if item["label"] == object:
                counter += 1
        object_count_string += f"Number of {object} detected: {counter}" + "\n"
    return object_count_string

if __name__ == "__main__":
    image_base64=image_to_base64(image_path)
    initial_assessment = generate_room_report(image_base64)
    object_counts = detect_object_counts(image_path)
    final_prompt = initial_assessment + object_counts + "\n" + "Given these two pieces of information about this room, estimate the building cost of this room assumed to be in India, excluding the location's land cost since that's extremely variable. Give a very brief answer of not more than two sentences, which clearly give the FINAL TOTAL COST."
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are a cost estimator for interior spaces in India."
            },
            {
                "role": "user",
                "content": final_prompt
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "This is the image of the room again, for reference"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                ]
            }
        ]
    )
    print(response.choices[0].message.content)
