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

class NodeRequest(BaseModel):
    label: str
    properties: dict

class RelationshipRequest(BaseModel):
    source_id: str
    target_id: str
    relationship_type: str
    properties: dict

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
                response = f"{response}\n\nAdditional context from our knowledge graph:\n{graph_response}"
        
        return {
            "response": response,
            "references": references,
            "session_id": request.session_id or "default_session"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/add_node")
async def add_node(node: NodeRequest):
    """Add a new node to the knowledge graph"""
    try:
        node_id = graph_rag.add_node(node.label, node.properties)
        return {"message": "Node added successfully", "node_id": node_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/add_relationship")
async def add_relationship(rel: RelationshipRequest):
    """Add a new relationship to the knowledge graph"""
    try:
        graph_rag.add_relationship(
            rel.source_id,
            rel.target_id,
            rel.relationship_type,
            rel.properties
        )
        return {"message": "Relationship added successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/refresh_data")
async def refresh_data():
    """Refresh scraped data from the website"""
    try:
        scrape_nestle_site()
        chatbot.refresh_data()
        graph_rag.rebuild_graph()
        return {"message": "Data refreshed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)