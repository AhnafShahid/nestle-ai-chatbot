import os
import json
from typing import Tuple, List
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

class Chatbot:
    def __init__(self):
        self.hf_api_key = os.getenv("HF_API_KEY")
        self.data = self._load_data()
        self.sessions = {}

    def _load_data(self) -> dict:
        """Load scraped product data from JSON files"""
        data_dir = Path("data/scraped")
        products = []
        
        for file in data_dir.glob("*.json"):
            if file.name == "all_products.json":
                continue
            with open(file, "r") as f:
                products.append(json.load(f))
        
        return {"products": products}

    def refresh_data(self):
        """Reload product data from disk"""
        self.data = self._load_data()

    def _find_products_by_query(self, query: str) -> List[dict]:
        """Find products matching search query"""
        query_lower = query.lower()
        return [
            p for p in self.data["products"]
            if (query_lower in p["title"].lower() or 
                query_lower in p["description"].lower())
        ]

    def _generate_nutrition_response(self, product_name: str) -> Tuple[str, List[str]]:
        """Generate formatted nutrition response"""
        matches = self._find_products_by_query(product_name)
        if not matches:
            return "I couldn't find nutritional information for that product.", []

        response = []
        references = []
        for product in matches[:3]:  # Limit to 3 most relevant
            product_info = f"**{product['title']}**\n"
            
            if product.get("nutrition"):
                product_info += "Nutrition Facts:\n"
                for nutrient, value in product["nutrition"].items():
                    product_info += f"- {nutrient}: {value}\n"
            else:
                product_info += "No nutrition data available.\n"
            
            product_info += f"[View Product]({product['url']})"
            response.append(product_info)
            references.append(product["url"])
        
        return "\n\n".join(response), references

    def _generate_gift_ideas_response(self) -> Tuple[str, List[str]]:
        """Generate gift recommendations"""
        gift_products = [
            p for p in self.data["products"] 
            if "gift" in p["title"].lower() or 
               any("gift" in c.lower() for c in p.get("categories", []))
        ]
        
        if not gift_products:
            return "I couldn't find any gift ideas at the moment.", []
        
        response = ["Here are some Nestlé gift ideas:"]
        references = []
        for product in gift_products[:5]:
            desc = (product["description"][:100] + "...") if product["description"] else ""
            response.append(f"- **{product['title']}**: {desc}")
            references.append(product["url"])
        
        return "\n".join(response), references

    def _query_huggingface(self, prompt: str) -> str:
        """Query Hugging Face Inference API"""
        API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1"
        headers = {"Authorization": f"Bearer {self.hf_api_key}"}
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 200,
                "temperature": 0.7,
                "do_sample": True
            }
        }
        
        try:
            response = requests.post(API_URL, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()[0]["generated_text"].replace(prompt, "").strip()
        except Exception as e:
            print(f"Error querying Hugging Face: {str(e)}")
            return "I'm having trouble generating a response right now."

    def get_response(self, message: str, session_id: str = "default") -> Tuple[str, List[str]]:
        """Main method to get chatbot response"""
        # Add to session history
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        self.sessions[session_id].append({"role": "user", "content": message})

        # Check for specific intents
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["calories", "nutrition", "protein"]):
            return self._generate_nutrition_response(message_lower)
        elif any(word in message_lower for word in ["gift", "present", "christmas"]):
            return self._generate_gift_ideas_response()
        
        # Fallback to LLM for general queries
        prompt = """<s>[INST] <<SYS>>
You are Smartie, a helpful assistant for Made With Nestlé. 
Provide concise, friendly answers about Nestlé products.
<</SYS>>\n\n"""
        
        # Add conversation context
        for msg in self.sessions[session_id][-3:]:  # Last 3 messages
            role = "User" if msg["role"] == "user" else "Assistant"
            prompt += f"{role}: {msg['content']}\n"
        
        prompt += f"User: {message}\nAssistant: [/INST]"
        
        response = self._query_huggingface(prompt)
        self.sessions[session_id].append({"role": "assistant", "content": response})
        return response, []