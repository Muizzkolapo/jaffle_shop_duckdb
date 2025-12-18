"""
Quick test script for the mock Discovery API.
Run after starting the mock API server.
"""

import requests
import json


def test_sources_all():
    """Test getting all sources."""
    print("\n=== Testing: Get All Sources ===")
    response = requests.post(
        "http://localhost:8000/graphql",
        json={
            "query": """
                query GetSources($environmentId: BigInt!) {
                    environment(id: $environmentId) {
                        applied {
                            sources {
                                edges {
                                    node {
                                        name
                                        uniqueId
                                        sourceName
                                        description
                                    }
                                }
                            }
                        }
                    }
                }
            """,
            "variables": {
                "environmentId": 12345
            }
        }
    )

    data = response.json()
    sources = data["data"]["environment"]["applied"]["sources"]["edges"]
    print(f"Found {len(sources)} sources")
    for edge in sources:
        node = edge["node"]
        print(f"  - {node['sourceName']}.{node['name']} ({node['uniqueId']})")

    return sources


def test_sources_filtered():
    """Test getting sources filtered by source_names."""
    print("\n=== Testing: Get Sources Filtered by source_names ===")
    response = requests.post(
        "http://localhost:8000/graphql",
        json={
            "query": """
                query GetSources($environmentId: BigInt!, $sourcesFilter: SourceAppliedFilter) {
                    environment(id: $environmentId) {
                        applied {
                            sources(filter: $sourcesFilter) {
                                edges {
                                    node {
                                        name
                                        uniqueId
                                        sourceName
                                    }
                                }
                            }
                        }
                    }
                }
            """,
            "variables": {
                "environmentId": 12345,
                "sourcesFilter": {
                    "sourceNames": ["jaffle_shop"]
                }
            }
        }
    )

    data = response.json()
    sources = data["data"]["environment"]["applied"]["sources"]["edges"]
    print(f"Found {len(sources)} sources for 'jaffle_shop'")
    for edge in sources:
        node = edge["node"]
        print(f"  - {node['sourceName']}.{node['name']}")


def test_sources_by_unique_id():
    """Test getting a specific source by unique_id."""
    print("\n=== Testing: Get Source by unique_id ===")
    unique_id = "source.jaffle_shop.main.raw_customers"

    response = requests.post(
        "http://localhost:8000/graphql",
        json={
            "query": """
                query GetSources($environmentId: BigInt!, $sourcesFilter: SourceAppliedFilter) {
                    environment(id: $environmentId) {
                        applied {
                            sources(filter: $sourcesFilter) {
                                edges {
                                    node {
                                        name
                                        uniqueId
                                        sourceName
                                        description
                                    }
                                }
                            }
                        }
                    }
                }
            """,
            "variables": {
                "environmentId": 12345,
                "sourcesFilter": {
                    "uniqueIds": [unique_id]
                }
            }
        }
    )

    data = response.json()
    sources = data["data"]["environment"]["applied"]["sources"]["edges"]
    if sources:
        node = sources[0]["node"]
        print(f"Found source: {node['sourceName']}.{node['name']}")
        print(f"  Description: {node['description'] or '(no description)'}")
    else:
        print("Source not found!")


def test_seeds_by_identifier():
    """Test getting seeds filtered by identifier (name)."""
    print("\n=== Testing: Get Seeds by Identifier ===")
    response = requests.post(
        "http://localhost:8000/graphql",
        json={
            "query": """
                query GetSeeds($environmentId: BigInt!, $seedsFilter: GenericMaterializedFilter) {
                    environment(id: $environmentId) {
                        applied {
                            seeds(filter: $seedsFilter) {
                                edges {
                                    node {
                                        name
                                        uniqueId
                                        resourceType
                                    }
                                }
                            }
                        }
                    }
                }
            """,
            "variables": {
                "environmentId": 12345,
                "seedsFilter": {
                    "identifier": "country_codes"  # Example seed name
                }
            }
        }
    )

    data = response.json()
    seeds = data["data"]["environment"]["applied"]["seeds"]["edges"]
    print(f"Found {len(seeds)} seed(s) matching 'country_codes'")
    for edge in seeds:
        node = edge["node"]
        print(f"  - {node['name']} ({node['uniqueId']})")


def test_snapshots_by_identifier():
    """Test getting snapshots filtered by identifier (name)."""
    print("\n=== Testing: Get Snapshots by Identifier ===")
    response = requests.post(
        "http://localhost:8000/graphql",
        json={
            "query": """
                query GetSnapshots($environmentId: BigInt!, $snapshotsFilter: GenericMaterializedFilter) {
                    environment(id: $environmentId) {
                        applied {
                            snapshots(filter: $snapshotsFilter) {
                                edges {
                                    node {
                                        name
                                        uniqueId
                                        resourceType
                                    }
                                }
                            }
                        }
                    }
                }
            """,
            "variables": {
                "environmentId": 12345,
                "snapshotsFilter": {
                    "identifier": "orders_snapshot"  # Example snapshot name
                }
            }
        }
    )

    data = response.json()
    snapshots = data["data"]["environment"]["applied"]["snapshots"]["edges"]
    print(f"Found {len(snapshots)} snapshot(s) matching 'orders_snapshot'")
    for edge in snapshots:
        node = edge["node"]
        print(f"  - {node['name']} ({node['uniqueId']})")


def test_exposures_all():
    """Test getting all exposures (no filter)."""
    print("\n=== Testing: Get All Exposures ===")
    response = requests.post(
        "http://localhost:8000/graphql",
        json={
            "query": """
                query GetExposures($environmentId: BigInt!) {
                    environment(id: $environmentId) {
                        definition {
                            exposures {
                                edges {
                                    node {
                                        name
                                        uniqueId
                                        type
                                        description
                                    }
                                }
                            }
                        }
                    }
                }
            """,
            "variables": {
                "environmentId": 12345
            }
        }
    )

    data = response.json()
    exposures = data["data"]["environment"]["definition"]["exposures"]["edges"]
    print(f"Found {len(exposures)} exposure(s)")
    for edge in exposures:
        node = edge["node"]
        print(f"  - {node['name']} ({node.get('type', 'unknown')}) - {node['uniqueId']}")


def test_exposures_by_unique_id():
    """Test getting specific exposure by unique_id."""
    print("\n=== Testing: Get Exposure by unique_id ===")

    # First get all exposures to find one
    all_response = requests.post(
        "http://localhost:8000/graphql",
        json={
            "query": """
                query GetExposures($environmentId: BigInt!) {
                    environment(id: $environmentId) {
                        definition {
                            exposures {
                                edges {
                                    node {
                                        uniqueId
                                    }
                                }
                            }
                        }
                    }
                }
            """,
            "variables": {"environmentId": 12345}
        }
    )

    all_exposures = all_response.json()["data"]["environment"]["definition"]["exposures"]["edges"]
    if not all_exposures:
        print("  No exposures found in manifest - skipping test")
        return

    # Use the first exposure's unique_id
    test_unique_id = all_exposures[0]["node"]["uniqueId"]

    response = requests.post(
        "http://localhost:8000/graphql",
        json={
            "query": """
                query GetExposures($environmentId: BigInt!, $filter: ExposureFilter) {
                    environment(id: $environmentId) {
                        definition {
                            exposures(filter: $filter) {
                                edges {
                                    node {
                                        name
                                        uniqueId
                                        type
                                        description
                                    }
                                }
                            }
                        }
                    }
                }
            """,
            "variables": {
                "environmentId": 12345,
                "filter": {
                    "uniqueIds": [test_unique_id]
                }
            }
        }
    )

    data = response.json()
    exposures = data["data"]["environment"]["definition"]["exposures"]["edges"]
    if exposures:
        node = exposures[0]["node"]
        print(f"  Found exposure: {node['name']}")
        print(f"  Unique ID: {node['uniqueId']}")
    else:
        print("  Exposure not found!")


def test_health():
    """Test the health endpoint."""
    print("\n=== Testing: Health Check ===")
    response = requests.get("http://localhost:8000")
    data = response.json()
    print(f"Status: {data['status']}")
    print(f"Manifest exists: {data['manifest_exists']}")
    print(f"Manifest path: {data['manifest_path']}")


if __name__ == "__main__":
    try:
        print("Testing Mock Discovery API")
        print("Make sure the server is running: uvicorn mock_discovery_api:app --reload --port 8000")

        test_health()

        # Test sources
        test_sources_all()
        test_sources_filtered()
        test_sources_by_unique_id()

        # Test seeds and snapshots
        test_seeds_by_identifier()
        test_snapshots_by_identifier()

        # Test exposures
        test_exposures_all()
        test_exposures_by_unique_id()

        print("\n✅ All tests completed!")

    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to the mock API server.")
        print("Make sure it's running with: uvicorn mock_discovery_api:app --reload --port 8000")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
