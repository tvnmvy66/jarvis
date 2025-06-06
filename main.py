from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
import uuid
from google import genai
from google.genai import types

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")
# oclient = OpenAI()
gclient = genai.Client(api_key="AIzaSyBr3UYprUIphD0GbG-BIjSWuz2zpoDAkgE")
app = FastAPI()

# # CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://www.tanmay.blog"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to MongoDB
client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# Pydantic model for validation
class ContactForm(BaseModel):
    email: EmailStr = Field(..., min_length=5, max_length=30)
    message: str = Field(..., min_length=10, max_length=200)

@app.get("/")
async def hello():
    return {"message" : "Hey, I am alive!"}


@app.post("/contact")
async def submit_contact(form: ContactForm):
    doc = form.model_dump()
    try:
        result = await collection.insert_one(doc)
        return {"message": "Message received", "id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# === Serve Audio Files ===
AUDIO_DIR = "audio"
os.makedirs(AUDIO_DIR, exist_ok=True)
app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")

# === WebSocket Route ===
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connected!")

    try:
        while True:
            data = await websocket.receive_text()
            print(f"Received from user: {data}")

            system_prompt = """
            You are a helpful, feminine AI assistant. Keep your replies brief and friendly.
            """

            # === GPT Response ===
            # completion = client.chat.completions.create(
            #     model="gpt-4.1",
            #     messages=[
            #         {"role": "system", "content": system_prompt},
            #         {"role": "user", "content": data}
            #     ]
            # )

            # response_text = completion.choices[0].message.content.strip()

            # === Gemini Response ===
            response = gclient.models.generate_content(
            model="gemini-1.5-flash",
            config=types.GenerateContentConfig(
                system_instruction=system_prompt),
            contents=data
            )
            response_text = response.text
            print("Jarvis:", response_text)

            # === Generate TTS Audio ===
            audio_path = await generate_tts_audio(response_text)
            audio_filename = os.path.basename(audio_path)

            # === Send JSON over WebSocket ===
            await websocket.send_json({
                "text": response_text,
                "audio_url": f"/audio/{audio_filename}"
            })

    except WebSocketDisconnect:
        print("WebSocket disconnected.")
    except Exception as e:
        print("WebSocket error:", e)

# === TTS Audio Generator ===
async def generate_tts_audio(text: str, voice="shimmer", model="tts-1"):
    try:
        response = client.audio.speech.create(
            model=model,
            voice=voice,
            input=text
        )
        filename = f"jarvis_{uuid.uuid4().hex}.mp3"
        path = os.path.join(AUDIO_DIR, filename)
        with open(path, "wb") as f:
            f.write(response.content)
        return path
    except Exception as e:
        print("TTS generation failed:", e)
        return None

# === Health Check ===
@app.get("/ping")
async def ping():
    return {"responseText": "pong"}
