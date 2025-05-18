from typing import List, Dict, Optional
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
import openai
from langchain.graphs import Neo4jGraph
from langchain.vectorstores import Neo4jVector
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chains import GraphCypherQAChain
from langchain.chat_models import ChatOpenAI
from app.scraper import scrape_nestle_site

load_dotenv()

class GraphRAG:
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI")
        self.user = os.getenv("NEO4J_USER")
        self.password = os.getenv("NEO4J_PASSWORD")
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        self.embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
        self.llm = ChatOpenAI(openai_api_key=os.getenv("OPENAI_API_KEY"), model_name="gpt-3.5-turbo")
        self._initialize_graph()
    
    def _initialize_graph(self):
        """Initialize the graph database with schema if needed"""
        with self.driver.session() as session:
            # Create constraints
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Product) REQUIRE p.id IS UNIQUE")
            session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Category) REQUIRE c.name IS UNIQUE")
            
            # Create full-text index
            session.run("""
            CALL db.index.fulltext.createNodeIndex(
                'productSearch', 
                ['Product'], 
                ['title', 'description']
            )
            """)
    
    def rebuild_graph(self):
        """Rebuild the entire graph from scraped data"""
        products = scrape_nestle_site()
        
        with self.driver.session() as session:
            # Clear existing data
            session.run("MATCH (n) DETACH DELETE n")
            
            # Add products and categories
            for product in products:
                # Create or update product node
                session.run("""
                MERGE (p:Product {id: $id})
                SET p.title = $title,
                    p.description = $description,
                    p.url = $url
                """, {
                    "id": product["url"],
                    "title": product["title"],
                    "description": product["description"],
                    "url": product["url"]
                })
                
                # Add nutritional facts as properties
                for nutrient, value in product.get("nutrition", {}).items():
                    session.run("""
                    MATCH (p:Product {id: $id})
                    SET p.`%s` = $value
                    """ % nutrient.replace(" ", "_"), {
                        "id": product["url"],
                        "value": value
                    })
                
                # Connect categories
                for category in product.get("categories", []):
                    session.run("""
                    MERGE (c:Category {name: $name})
                    MERGE (p:Product {id: $id})-[:IN_CATEGORY]->(c)
                    """, {
                        "name": category,
                        "id": product["url"]
                    })
            
            # Create vector index for semantic search
            Neo4jVector.from_existing_index(
                embedding=self.embeddings,
                index_name="product_embeddings",
                node_label="Product",
                text_node_properties=["title", "description"],
                embedding_node_property="embedding",
                url=self.uri,
                username=self.user,
                password=self.password
            )
    
    def add_node(self, label: str, properties: dict) -> str:
        """Add a new node to the graph"""
        with self.driver.session() as session:
            result = session.run(
                f"CREATE (n:{label} $props) RETURN id(n) as node_id",
                props=properties
            )
            return str(result.single()["node_id"])
    
    def add_relationship(self, source_id: str, target_id: str, relationship_type: str, properties: dict = {}):
        """Add a relationship between two nodes"""
        with self.driver.session() as session:
            session.run("""
            MATCH (a), (b)
            WHERE id(a) = $source_id AND id(b) = $target_id
            CREATE (a)-[r:%s $props]->(b)
            """ % relationship_type,
            {
                "source_id": int(source_id),
                "target_id": int(target_id),
                "props": properties
            })
    
    def query(self, question: str) -> Optional[str]:
        """Query the knowledge graph for relevant information"""
        try:
            graph = Neo4jGraph(
                url=self.uri,
                username=self.user,
                password=self.password
            )
            
            chain = GraphCypherQAChain.from_llm(
                llm=self.llm,
                graph=graph,
                verbose=True,
                return_intermediate_steps=True
            )
            
            result = chain(question)
            
            if result["intermediate_steps"] and result["intermediate_steps"][0]:
                cypher_query = result["intermediate_steps"][0]["query"]
                context = "\n".join([
                    str(item) 
                    for item in result["intermediate_steps"][0]["context"]
                ])
                
                return f"Knowledge Graph Context:\n{context}\n\nGenerated from query:\n{cypher_query}"
            
            return None
        except Exception as e:
            print(f"Error querying graph: {str(e)}")
            return None