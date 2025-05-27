from neo4j import GraphDatabase
from dotenv import load_dotenv
import os
from typing import Optional

load_dotenv()

class GraphRAG:
    def __init__(self):
        """Initialize Neo4j driver with AuraDB credentials"""
        self.driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI"),
            auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD")),
            encrypted=True  # Required for AuraDB
        )
        self._initialize_graph()

    def _initialize_graph(self):
        """Create necessary constraints and indexes"""
        with self.driver.session() as session:
            # Create uniqueness constraints
            session.run("""
            CREATE CONSTRAINT IF NOT EXISTS 
            FOR (p:Product) REQUIRE p.id IS UNIQUE
            """)
            session.run("""
            CREATE CONSTRAINT IF NOT EXISTS 
            FOR (c:Category) REQUIRE c.name IS UNIQUE
            """)
            
            # Create full-text index for search
            session.run("""
            CALL db.index.fulltext.createNodeIndex(
                'productSearch',
                ['Product'],
                ['title', 'description']
            )
            """)

    def rebuild_graph(self):
        """Rebuild the entire graph from scraped data"""
        from app.scraper import scrape_nestle_site
        products = scrape_nestle_site()
        
        with self.driver.session() as session:
            # Clear existing data
            session.run("MATCH (n) DETACH DELETE n")
            
            # Insert products and relationships
            for product in products:
                session.run("""
                MERGE (p:Product {id: $id})
                SET p.title = $title,
                    p.description = $description,
                    p.url = $url
                """, {
                    "id": product["url"],
                    "title": product["title"],
                    "description": product.get("description", ""),
                    "url": product["url"]
                })
                
                # Add nutrition facts as properties
                for nutrient, value in product.get("nutrition", {}).items():
                    session.run(f"""
                    MATCH (p:Product {{id: $id}})
                    SET p.`{nutrient.replace(" ", "_")}` = $value
                    """, {
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

    def query(self, question: str) -> Optional[str]:
        """Query the knowledge graph for relevant products"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    CALL db.index.fulltext.queryNodes('productSearch', $query)
                    YIELD node, score
                    RETURN node.title AS title, node.description AS description
                    ORDER BY score DESC
                    LIMIT 3
                """, {"query": question})
                
                products = [
                    f"• {record['title']}: {record['description'][:100]}..."
                    for record in result
                ]
                
                if not products:
                    return None
                
                return "I found these related products:\n" + "\n".join(products)
        except Exception as e:
            print(f"Graph query error: {str(e)}")
            return None

    def close(self):
        """Close the Neo4j driver connection"""
        self.driver.close()