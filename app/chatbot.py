import os
import json
from typing import Tuple, List
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
import hashlib

load_dotenv()

class Chatbot:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.data = self._load_data()
        self.sessions = {}  # Store conversation history by session ID
    
    def _load_data(self) -> dict:
        """Load scraped data from JSON files"""
        data_dir = Path("data/scraped")
        products = []
        
        for file in data_dir.glob("*.json"):
            if file.name == "all_products.json":
                continue
            with open(file, "r") as f:
                products.append(json.load(f))
        
        return {"products": products}
    
    def refresh_data(self):
        """Reload data from disk"""
        self.data = self._load_data()
    
    def _find_products_by_query(self, query: str) -> List[dict]:
        """Find products matching the query"""
        query_lower = query.lower()
        matches = []
        
        for product in self.data["products"]:
            if (query_lower in product["title"].lower() or 
                query_lower in product["description"].lower()):
                matches.append(product)
        
        return matches
    
    def _generate_nutrition_response(self, product_name: str) -> Tuple[str, List[str]]:
        """Generate response for nutrition queries"""
        matches = self._find_products_by_query(product_name)
        if not matches:
            return "I couldn't find information about that product. Could you clarify?", []
        
        response = []
        references = []
        
        for product in matches[:3]:  # Limit to top 3 matches
            product_info = f"**{product['title']}**\n"
            if product["nutrition"]:
                product_info += "Nutritional information per serving:\n"
                for key, value in product["nutrition"].items():
                    product_info += f"- {key}: {value}\n"
            else:
                product_info += "No nutritional information available.\n"
            
            product_info += f"\n[View product]({product['url']})"
            response.append(product_info)
            references.append(product["url"])
        
        return "\n\n".join(response), references
    
    def _generate_gift_ideas_response(self) -> Tuple[str, List[str]]:
        """Generate response for gift ideas"""
        gift_products = [
            p for p in self.data["products"] 
            if "gift" in p["title"].lower() or 
               any("gift" in cat.lower() for cat in p["categories"])
        ]
        
        if not gift_products:
            return "I couldn't find any gift ideas at the moment.", []
        
        response = ["Here are some great gift ideas from Nestlé:"]
        references = []
        
        for product in gift_products[:5]:  # Limit to 5 gift ideas
            product_info = f"- **{product['title']}**: {product['description'][:100]}..."
            product_info += f"\n  [View product]({product['url']})"
            response.append(product_info)
            references.append(product["url"])
        
        return "\n".join(response), references
    
    def get_response(self, message: str, session_id: str = "default") -> Tuple[str, List[str]]:
        """Get response for user message"""
        # Add to session history
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append({"role": "user", "content": message})
        
        # Check for specific intent patterns
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["calories", "nutrition", "protein", "fat", "sugar"]):
            product_name = message_lower.replace("calories", "").replace("nutrition", "").strip()
            response, references = self._generate_nutrition_response(product_name)
        elif any(word in message_lower for word in ["gift", "present", "christmas", "holiday"]):
            response, references = self._generate_gift_ideas_response()
        else:
            # Fallback to GPT-3.5 for general queries
            try:
                chat_completion = self.client.chat.completions.create(
                    messages=[
                        {
                            "role": "system",
                            "content": "You are Smartie, a helpful assistant for the Made With Nestlé website. "
                                      "Be friendly and provide concise answers. When possible, reference "
                                      "specific products from the site."
                        },
                        *self.sessions[session_id]
                    ],
                    model="gpt-3.5-turbo",
                )
                response = chat_completion.choices[0].message.content
                references = []
            except Exception as e:
                response = "I'm having trouble connecting to the knowledge base. Please try again later."
                references = []
        
        # Add assistant response to session history
        self.sessions[session_id].append({"role": "assistant", "content": response})
        
        return response, references