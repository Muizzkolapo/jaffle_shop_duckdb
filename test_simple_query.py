"""
Simple test to check if data exists in Discovery API
"""

import requests
import json

# Your credentials
ENVIRONMENT_ID = "70471823504996"
API_TOKEN = "dbtu_C2OQ-54C3lP_rXddqrSyVocB6lR0M8jT9oS8srAXEGSFLR33lY"
DISCOVERY_URL = "https://metadata.cloud.getdbt.com/graphql"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# Simple query to check environment
query = """
query CheckEnvironment($environmentId: BigInt!) {
  environment(id: $environmentId) {
    environmentId
    dbtVersion
    name
    applied {
      models {
        totalCount
      }
      sources {
        totalCount
      }
      tests {
        totalCount
      }
    }
  }
}
"""

print("="*80)
print("Checking dbt Cloud Environment Status")
print("="*80)
print(f"Environment ID: {ENVIRONMENT_ID}")
print(f"Discovery URL: {DISCOVERY_URL}\n")

response = requests.post(
    DISCOVERY_URL,
    headers=headers,
    json={
        "query": query,
        "variables": {"environmentId": int(ENVIRONMENT_ID)}
    }
)

data = response.json()

if "errors" in data:
    print("❌ Error:")
    print(json.dumps(data["errors"], indent=2))

    error_code = data["errors"][0].get("extensions", {}).get("code")
    if error_code == "NO_DATA_AVAILABLE":
        print("\n" + "="*80)
        print("⚠️  NO DATA IN DISCOVERY API")
        print("="*80)
        print("\nThis means you haven't run dbt in dbt Cloud yet.")
        print("\n📋 Next Steps:")
        print("  1. Go to: https://dk927.us1.dbt.com")
        print("  2. Click 'Develop' → Open IDE")
        print("  3. Run: dbt build")
        print("  4. Wait for completion")
        print("  5. Run this script again")
else:
    env = data.get("data", {}).get("environment", {})

    if env:
        print("✅ Environment Found!")
        print(f"\nEnvironment ID: {env.get('environmentId')}")
        print(f"Name: {env.get('name')}")
        print(f"dbt Version: {env.get('dbtVersion')}")

        applied = env.get("applied", {})
        models_count = applied.get("models", {}).get("totalCount", 0)
        sources_count = applied.get("sources", {}).get("totalCount", 0)
        tests_count = applied.get("tests", {}).get("totalCount", 0)

        print(f"\n📊 Resource Counts:")
        print(f"  Models: {models_count}")
        print(f"  Sources: {sources_count}")
        print(f"  Tests: {tests_count}")

        if models_count > 0:
            print("\n✅ Data available! You can now query the Discovery API.")
        else:
            print("\n⚠️  No models found. Run 'dbt build' in dbt Cloud IDE first.")
    else:
        print("❌ No environment data returned")

print("\n" + "="*80)
