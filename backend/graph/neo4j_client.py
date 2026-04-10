"""Neo4j connection wrapper for the Helio Veracity Layer."""

from neo4j import GraphDatabase
from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class Neo4jClient:
    """Wrapper around the Neo4j Python driver for graph operations."""

    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "helio_veracity_2024")
        self._driver = None

    def connect(self):
        """Establish connection to Neo4j."""
        self._driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        self._driver.verify_connectivity()
        print(f"  [OK] Connected to Neo4j at {self.uri}")

    def close(self):
        """Close the Neo4j connection."""
        if self._driver:
            self._driver.close()
            print("  [OK] Neo4j connection closed")

    def run_query(self, cypher: str, params: dict = None) -> list[dict]:
        """Execute a Cypher query and return results as list of dicts."""
        if not self._driver:
            self.connect()
        with self._driver.session() as session:
            result = session.run(cypher, params or {})
            return [record.data() for record in result]

    def run_write(self, cypher: str, params: dict = None):
        """Execute a write Cypher query."""
        if not self._driver:
            self.connect()
        with self._driver.session() as session:
            session.run(cypher, params or {})

    def clear_graph(self):
        """Delete all nodes and relationships in the graph."""
        self.run_write("MATCH (n) DETACH DELETE n")
        print("  [OK] Graph cleared")

    def get_node_count(self) -> int:
        """Get total number of nodes."""
        result = self.run_query("MATCH (n) RETURN count(n) as count")
        return result[0]["count"] if result else 0

    def get_edge_count(self) -> int:
        """Get total number of relationships."""
        result = self.run_query("MATCH ()-[r]->() RETURN count(r) as count")
        return result[0]["count"] if result else 0

    def get_stats(self) -> dict:
        """Get graph statistics by node label and relationship type."""
        node_stats = self.run_query(
            "MATCH (n) RETURN labels(n)[0] as label, count(n) as count ORDER BY count DESC"
        )
        edge_stats = self.run_query(
            "MATCH ()-[r]->() RETURN type(r) as type, count(r) as count ORDER BY count DESC"
        )
        return {
            "total_nodes": self.get_node_count(),
            "total_edges": self.get_edge_count(),
            "nodes_by_type": {r["label"]: r["count"] for r in node_stats},
            "edges_by_type": {r["type"]: r["count"] for r in edge_stats},
        }


# Singleton instance
neo4j_client = Neo4jClient()
