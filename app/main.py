from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
from app.scraper import scrape_nestle_site
from app.chatbot import Chatbot
from app.graphrag import GraphRAG

load_dotenv()

app = FastAPI(title="Nestlé AI Chatbot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

chatbot = Chatbot()
graph_rag = GraphRAG()

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    references: List[str]
    session_id: str

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        response, references = chatbot.get_response(request.message)
        
        if "I don't know" in response:
            graph_response = graph_rag.query(request.message)
            if graph_response:
                response = f"{response}\n\nAdditional context:\n{graph_response}"
        
        return {
            "response": response,
            "references": references,
            "session_id": request.session_id or "default_session"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/refresh_data")
async def refresh_data():
    try:
        scrape_nestle_site()
        chatbot.refresh_data()
        graph_rag.rebuild_graph()
        return {"message": "Data refreshed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))