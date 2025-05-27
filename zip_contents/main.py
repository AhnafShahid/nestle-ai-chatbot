from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
from app.scraper import scrape_nestle_site
from app.chatbot import Chatbot
from app.graphrag import GraphRAG

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Nestlé AI Chatbot API",
    description="AI-powered chatbot for Made With Nestlé products",
    version="1.0.0",
    docs_url="/docs" if os.getenv("DEPLOY_ENV") != "azure" else None,  # Disable docs in production
    redoc_url=None
)

# Azure-specific middleware
if os.getenv("DEPLOY_ENV") == "azure":
    app.add_middleware(HTTPSRedirectMiddleware)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
chatbot = Chatbot()
graph_rag = GraphRAG()

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    references: List[str]
    session_id: str

@app.on_event("startup")
async def startup_event():
    """Initialize data on startup if in Azure environment"""
    if os.getenv("DEPLOY_ENV") == "azure":
        try:
            if not os.path.exists("data/scraped"):
                os.makedirs("data/scraped")
                scrape_nestle_site()
                graph_rag.rebuild_graph()
        except Exception as e:
            print(f"Startup initialization error: {str(e)}")

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat messages with both traditional and GraphRAG responses"""
    try:
        # First try traditional response
        response, references = chatbot.get_response(request.message)
        
        # Enhance with GraphRAG if needed
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
    """Endpoint to manually refresh scraped data"""
    try:
        scrape_nestle_site()
        chatbot.refresh_data()
        graph_rag.rebuild_graph()
        return {"message": "Data refreshed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint for Azure monitoring"""
    return {"status": "healthy"}

# Only run with uvicorn if not in Azure environment
if __name__ == "__main__" and os.getenv("DEPLOY_ENV") != "azure":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)