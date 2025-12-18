"""
Run the get_lineage.gql query against dbt Cloud Discovery API
"""

import requests
import json
from pathlib import Path

# Your credentials
ACCOUNT_ID = "70471823518521"
PROJECT_ID = "70471823535408"
ENVIRONMENT_ID = "70471823504996"
API_TOKEN = "dbtu_C2OQ-54C3lP_rXddqrSyVocB6lR0M8jT9oS8srAXEGSFLR33lY"
DISCOVERY_URL = "https://metadata.cloud.getdbt.com/graphql"

# Headers
headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# Load the GraphQL query
query_file = Path(__file__).parent / "get_lineage.gql"
with open(query_file) as f:
    query = f.read()


def run_lineage_query(selector: str):
    """
    Run lineage query with a selector

    Args:
        selector: dbt selector syntax, e.g.:
            - "model.jaffle_shop.customers" - just this model
            - "+model.jaffle_shop.customers" - this model and ancestors
            - "model.jaffle_shop.customers+" - this model and descendants
            - "+model.jaffle_shop.customers+" - full lineage (both directions)
    """
    print(f"\n{'='*80}")
    print(f"Running Lineage Query: {selector}")
    print(f"{'='*80}\n")

    variables = {
        "environmentId": int(ENVIRONMENT_ID),
        "filter": {
            "selector": selector
        }
    }

    response = requests.post(
        DISCOVERY_URL,
        headers=headers,
        json={
            "query": query,
            "variables": variables
        }
    )

    data = response.json()

    if "errors" in data:
        print("❌ Error:")
        print(json.dumps(data["errors"], indent=2))
        return None

    lineage = data.get("data", {}).get("environment", {}).get("applied", {}).get("lineage", [])

    if not lineage:
        print("⚠️  No lineage data found.")
        print("\nThis usually means:")
        print("  1. The selector didn't match any resources")
        print("  2. No dbt runs have been completed in dbt Cloud yet")
        print("\n💡 Make sure you've run 'dbt build' in dbt Cloud IDE first!")
        return None

    print(f"✅ Found {len(lineage)} nodes in lineage:\n")

    # Group by resource type
    by_type = {}
    for node in lineage:
        resource_type = node.get("resourceType", "unknown")
        if resource_type not in by_type:
            by_type[resource_type] = []
        by_type[resource_type].append(node)

    # Print organized results
    for resource_type, nodes in sorted(by_type.items()):
        print(f"\n{resource_type.upper()}S ({len(nodes)}):")
        print("-" * 80)

        for node in nodes:
            matches = "🎯" if node.get("matchesMethod") else "  "
            print(f"{matches} {node['name']}")
            print(f"   Unique ID: {node['uniqueId']}")

            if node.get("database"):
                print(f"   Location: {node.get('database')}.{node.get('schema')}")

            if node.get("materializationType"):
                print(f"   Materialization: {node['materializationType']}")

            if node.get("sourceName"):
                print(f"   Source: {node['sourceName']}")

            if node.get("lastRunStatus"):
                print(f"   Last Run: {node['lastRunStatus']}")

            print()

    return lineage


def main():
    print("="*80)
    print("dbt Cloud Discovery API - Lineage Query")
    print("="*80)
    print(f"\nEnvironment ID: {ENVIRONMENT_ID}")
    print(f"Discovery URL: {DISCOVERY_URL}")

    # Example queries - try these!
    examples = [
        ("Full lineage of customers model", "+model.jaffle_shop.customers+"),
        ("Just customers model", "model.jaffle_shop.customers"),
        ("Customers and ancestors", "+model.jaffle_shop.customers"),
        ("Customers and descendants", "model.jaffle_shop.customers+"),
    ]

    print("\n" + "="*80)
    print("Available Example Queries:")
    print("="*80)
    for i, (desc, selector) in enumerate(examples, 1):
        print(f"{i}. {desc}: {selector}")

    # Try the full lineage query
    print("\n" + "="*80)
    print("Running Example: Full lineage of 'customers' model")
    print("="*80)

    result = run_lineage_query("+model.jaffle_shop.customers+")

    if result:
        print("\n" + "="*80)
        print("✅ Query Successful!")
        print("="*80)
    else:
        print("\n" + "="*80)
        print("⚠️  No Data Available")
        print("="*80)
        print("\nNext Step: Go to dbt Cloud IDE and run:")
        print("  → https://dk927.us1.dbt.com")
        print("  → Click 'Develop'")
        print("  → Run: dbt build")
        print("\nThen run this script again!")


if __name__ == "__main__":
    main()
