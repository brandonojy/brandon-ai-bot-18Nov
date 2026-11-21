import json
import requests
from fastapi import FastAPI
from openai import OpenAI

TOKEN = ""  # Paste your Telegram bot token here (from @BotFather)
BASE = f"https://api.telegram.org/bot{TOKEN}"

mypassword = ""  # Paste your OpenAI API key here (starts with sk-)
client = OpenAI(api_key=mypassword)

CONVERSATION = "conv_6afd497d43d8819094bf12402682d15b02238ed1e2933606"


# Function 1: HDB carpark lots (data.gov.sg)
def get_carpark_availability(carpark_number):
    data = requests.get("https://api.data.gov.sg/v1/transport/carpark-availability").json()
    for carpark in data["items"][0]["carpark_data"]:
        if carpark["carpark_number"] == carpark_number.upper():
            info = carpark["carpark_info"][0]
            return f"Carpark {carpark_number}: {info['lots_available']} of {info['total_lots']} lots free"
    return f"Carpark {carpark_number} not found"


# Function 2: LTA traffic camera image (data.gov.sg)
def get_traffic_image(camera_id):
    data = requests.get("https://api.data.gov.sg/v1/transport/traffic-images").json()
    for camera in data["items"][0]["cameras"]:
        if camera["camera_id"] == str(camera_id):
            return camera["image"]
    return f"Camera {camera_id} not found"


# Tell the AI about our 2 functions
my_tools = [
    {"type": "web_search"},
    {"type": "code_interpreter", "container": {"type": "auto", "file_ids": ["file-DRdpAHwGFaSzFAM9a6fEHt"]}},
    {
        "type": "function",
        "name": "get_carpark_availability",
        "description": "Get free lots at an HDB carpark in Singapore, e.g. HE12",
        "parameters": {
            "type": "object",
            "properties": {"carpark_number": {"type": "string"}},
            "required": ["carpark_number"],
        },
    },
    {
        "type": "function",
        "name": "get_traffic_image",
        "description": "Get the latest image URL from a Singapore traffic camera, e.g. 2701",
        "parameters": {
            "type": "object",
            "properties": {"camera_id": {"type": "string"}},
            "required": ["camera_id"],
        },
    },
]


def send_message(reply, chat_id):
  re = requests.post(f"{BASE}/sendMessage", json={"chat_id": chat_id, "text": reply})
  print(re.json())


def handle_update(update):
    latest_query = update["message"]["text"]
    chat_id = update["message"]["chat"]["id"]
    send_message("Processing your query...", chat_id)

    response = client.responses.create(
        model="gpt-6-luna",
        instructions="I am a Telegram chatbot that is wise and give advice on recent news. I can also check HDB carpark lots and traffic cameras.",
        input=latest_query,
        conversation=CONVERSATION,
        tools=my_tools,
    )

    # Did the AI ask to run one of our functions?
    results = []
    for item in response.output:
        if item.type == "function_call":
            args = json.loads(item.arguments)
            if item.name == "get_carpark_availability":
                answer = get_carpark_availability(args["carpark_number"])
            else:
                answer = get_traffic_image(args["camera_id"])
            results.append({"type": "function_call_output", "call_id": item.call_id, "output": answer})

    # If yes, send the results back so the AI can reply
    if results:
        response = client.responses.create(
            model="gpt-6-luna",
            input=results,
            conversation=CONVERSATION,
            tools=my_tools,
        )

    send_message(response.output_text, chat_id)


app = FastAPI()

@app.get("/")
def home():
    return {"status": "OK"}

@app.post("/webhook")
def webhook(update: dict):
    handle_update(update)
    return {"ok": True}
