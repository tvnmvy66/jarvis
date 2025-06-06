from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")

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

@app.post("/contact")
async def submit_contact(form: ContactForm):
    doc = form.model_dump()
    try:
        result = await collection.insert_one(doc)
        return {"message": "Message received", "id": str(result.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))