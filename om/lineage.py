from om.client import OMClient
import logging

class LineageFetcher:
    def __init__(self, client: OMClient):
        self.client = client

    def fetch_downstream_assets(self, entity_type: str, fqn: str, depth: int = 3) -> dict:
        """
        Fetches the downstream lineage for a given entity.
        Calculates the blast radius by counting unique downstream nodes.
        """
        endpoint = f"/lineage/{entity_type}/name/{fqn}"
        params = {
            "upstreamDepth": 0,
            "downstreamDepth": depth
        }
        try:
            data = self.client.get(endpoint, params=params)
            
            # The lineage response typically contains:
            # - 'entity': The root node
            # - 'nodes': A list of all nodes in the graph
            # - 'upstreamEdges': List of edges
            # - 'downstreamEdges': List of edges
            
            nodes = data.get("nodes", [])
            downstream_edges = data.get("downstreamEdges", [])
            
            # Count the number of unique downstream impacted entities
            # In a real scenario we'd traverse the edges, but simply counting nodes
            # returned when upstreamDepth=0 gives us the downstream blast radius.
            impacted_assets = []
            for node in nodes:
                impacted_assets.append({
                    "id": node.get("id"),
                    "type": node.get("type"),
                    "name": node.get("name"),
                    "fqn": node.get("fullyQualifiedName")
                })
            
            return {
                "impacted_assets": impacted_assets,
                "blast_radius": len(impacted_assets)
            }
        except Exception as e:
            logging.error(f"Failed to fetch lineage for {fqn}: {e}")
            return {"impacted_assets": [], "blast_radius": 0}
