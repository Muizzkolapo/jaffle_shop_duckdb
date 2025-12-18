"""
Test script to query dbt Cloud Discovery API
"""

import requests
import json

# Your credentials
ACCOUNT_ID = "70471823518521"
PROJECT_ID = "70471823535408"
ENVIRONMENT_ID = "70471823504996"
API_TOKEN = "dbtu_C2OQ-54C3lP_rXddqrSyVocB6lR0M8jT9oS8srAXEGSFLR33lY"
HOST = "dk927.us1.dbt.com"

# Discovery API endpoint
# Standard Discovery API endpoint (works for all dbt Cloud deployments)
DISCOVERY_URL = "https://metadata.cloud.getdbt.com/graphql"

# Headers
headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}


def query_models():
    """Query all models from Discovery API"""
    query = """
    query GetModels($environmentId: BigInt!) {
        environment(id: $environmentId) {
            applied {
                models {
                    edges {
                        node {
                            name
                            uniqueId
                            description
                            database
                            schema
                            packageName
                            materializedType
                        }
                    }
                }
            }
        }
    }
    """

    response = requests.post(
        DISCOVERY_URL,
        headers=headers,
        json={
            "query": query,
            "variables": {"environmentId": int(ENVIRONMENT_ID)}
        }
    )

    return response.json()


def query_sources():
    """Query all sources from Discovery API"""
    query = """
    query GetSources($environmentId: BigInt!) {
        environment(id: $environmentId) {
            applied {
                sources {
                    edges {
                        node {
                            name
                            uniqueId
                            description
                            sourceName
                            database
                            schema
                        }
                    }
                }
            }
        }
    }
    """

    response = requests.post(
        DISCOVERY_URL,
        headers=headers,
        json={
            "query": query,
            "variables": {"environmentId": int(ENVIRONMENT_ID)}
        }
    )

    return response.json()


def main():
    print("=" * 80)
    print("Testing dbt Cloud Discovery API")
    print("=" * 80)
    print(f"\nAccount ID: {ACCOUNT_ID}")
    print(f"Project ID: {PROJECT_ID}")
    print(f"Environment ID: {ENVIRONMENT_ID}")
    print(f"Discovery URL: {DISCOVERY_URL}")

    # Query models
    print("\n" + "=" * 80)
    print("MODELS")
    print("=" * 80)

    try:
        models_data = query_models()

        if "errors" in models_data:
            print("\n❌ Error querying models:")
            print(json.dumps(models_data["errors"], indent=2))
        else:
            models = models_data.get("data", {}).get("environment", {}).get("applied", {}).get("models", {}).get("edges", [])
            print(f"\n✅ Found {len(models)} models:\n")

            for edge in models:
                model = edge["node"]
                print(f"  📊 {model['name']}")
                print(f"     Unique ID: {model['uniqueId']}")
                print(f"     Database: {model.get('database', 'N/A')}")
                print(f"     Schema: {model.get('schema', 'N/A')}")
                print(f"     Type: {model.get('materializedType', 'N/A')}")
                if model.get('description'):
                    print(f"     Description: {model['description'][:100]}...")
                print()

    except Exception as e:
        print(f"\n❌ Exception querying models: {e}")

    # Query sources
    print("\n" + "=" * 80)
    print("SOURCES")
    print("=" * 80)

    try:
        sources_data = query_sources()

        if "errors" in sources_data:
            print("\n❌ Error querying sources:")
            print(json.dumps(sources_data["errors"], indent=2))
        else:
            sources = sources_data.get("data", {}).get("environment", {}).get("applied", {}).get("sources", {}).get("edges", [])
            print(f"\n✅ Found {len(sources)} sources:\n")

            for edge in sources:
                source = edge["node"]
                print(f"  📁 {source['sourceName']}.{source['name']}")
                print(f"     Unique ID: {source['uniqueId']}")
                print(f"     Database: {source.get('database', 'N/A')}")
                print(f"     Schema: {source.get('schema', 'N/A')}")
                if source.get('description'):
                    print(f"     Description: {source['description'][:100]}...")
                print()

    except Exception as e:
        print(f"\n❌ Exception querying sources: {e}")

    print("=" * 80)
    print("✅ Discovery API Test Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
