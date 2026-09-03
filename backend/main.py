import json
import os

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AI_API_URL = os.getenv("AI_API_URL")
AI_API_KEY = os.getenv("AI_API_KEY")

# Request model
class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=1000
    )


# Response model
class ChatResponse(BaseModel):
    answer: str


@app.get("/")
async def root():
    return {
        "message": "AI Chat Backend is running"
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):

    # Remove unnecessary spaces
    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty"
        )

    # Request body for external AI API
    payload = {
        "question": question
    }

    # Headers for external AI API
    headers = {
    "x-api-key": AI_API_KEY,
    "Content-Type": "application/json"
    }

    try:
        # Call external AI API
        async with httpx.AsyncClient(timeout=30) as client:

            response = await client.post(
                AI_API_URL,
                json=payload,
                headers=headers
            )

        # Check HTTP status
        if not response.is_success:
            raise HTTPException(
                status_code=502,
                detail="AI API returned an error"
            )

        # First JSON parsing
        data = response.json()

        # Check external API status
        if data.get("statusCode") != 200:
            raise HTTPException(
                status_code=502,
                detail="AI API request failed"
            )

        # The external API's body is a JSON string,
        # so we need to parse it again.
        body = json.loads(data["body"])

        # Get the actual answer
        answer = body.get("answer")

        if not answer:
            raise HTTPException(
                status_code=502,
                detail="AI API did not return an answer"
            )

        # Return clean response to React
        return ChatResponse(
            answer=answer
        )

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="AI API request timed out"
        )

    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="Unable to connect to AI API"
        )

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=502,
            detail="Invalid JSON returned by AI API"
        )