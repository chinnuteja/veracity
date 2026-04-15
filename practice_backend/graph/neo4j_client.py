from neo4j import GraphDatabase
from dotenv import load_dotenv
from pathlib import Path
import os

# We reach out to find the .env file in the backend folder
env_path = Path(__file__).resolve().parent.parent.parent / "backend" / ".env"
load_dotenv(env_path)
class Neo4jClient:
    def __init__(self):
        # We are defining these variables ON the class instance (self)
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD")
        
        # We also need a place to store the actual connection object later
        self._driver = None 

    def connect(self):
        """Establish connection to Neo4j."""
        if not self._driver:
            self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            self._driver.verify_connectivity()
            print(f"  [OK] Connected to Neo4j at {self.uri}")

    def close(self):
        """Close the connection."""
        if self._driver:
            self._driver.close()
            print("  [OK] Neo4j connection closed")

    def run_query(self, cypher: str, params: dict = None) -> list[dict]:
        """Execute a READ query and return results as list of dicts."""
        if not self._driver:
            self.connect()
        with self._driver.session() as session:
            result = session.run(cypher, params or {})
            return [record.data() for record in result]

    def run_write(self, cypher: str, params: dict = None):
        """Execute a WRITE query."""
        if not self._driver:
            self.connect()
        with self._driver.session() as session:
            session.run(cypher, params or {})

    def clear_graph(self):
        """Wipe the database."""
        self.run_write("MATCH (n) DETACH DELETE n")
        print("  [OK] Graph cleared")

    def get_stats(self) -> dict:
        """Get graph statistics."""
        node_stats = self.run_query("MATCH (n) RETURN labels(n)[0] as label, count(n) as count")
        edge_stats = self.run_query("MATCH ()-[r]->() RETURN type(r) as type, count(r) as count")
        return {
            "nodes": {row['label']: row['count'] for row in node_stats},
            "edges": {row['type']: row['count'] for row in edge_stats}
        }

# Singleton instance
neo4j_client = Neo4jClient()
