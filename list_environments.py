"""
List all environments in your dbt Cloud account
"""

import requests
import json

ACCOUNT_ID = "70471823518521"
PROJECT_ID = "70471823535408"
API_TOKEN = "dbtu_C2OQ-54C3lP_rXddqrSyVocB6lR0M8jT9oS8srAXEGSFLR33lY"

# Admin API endpoint (not Discovery API)
# Try standard cloud endpoint first
ADMIN_API_URL = f"https://cloud.getdbt.com/api/v2/accounts/{ACCOUNT_ID}/projects/{PROJECT_ID}/environments/"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

print("="*80)
print("Listing dbt Cloud Environments")
print("="*80)
print(f"\nAccount ID: {ACCOUNT_ID}")
print(f"Project ID: {PROJECT_ID}")
print(f"API URL: {ADMIN_API_URL}\n")

try:
    response = requests.get(ADMIN_API_URL, headers=headers)

    print(f"Status Code: {response.status_code}\n")

    if response.status_code == 200:
        data = response.json()
        environments = data.get("data", [])

        if not environments:
            print("⚠️  No environments found.")
            print("\nYou may need to:")
            print("  1. Create an environment in dbt Cloud")
            print("  2. Go to Deploy → Environments → Create Environment")
        else:
            print(f"✅ Found {len(environments)} environment(s):\n")

            for env in environments:
                env_id = env.get("id")
                name = env.get("name")
                env_type = env.get("type")
                dbt_version = env.get("dbt_version")

                print(f"📦 {name}")
                print(f"   Environment ID: {env_id}")
                print(f"   Type: {env_type}")
                print(f"   dbt Version: {dbt_version}")

                # Check for successful runs
                print(f"   State: {env.get('state', 'N/A')}")
                print()

            print("\n" + "="*80)
            print("💡 Use one of these Environment IDs in your .env file")
            print("="*80)
    else:
        print(f"❌ Error {response.status_code}")
        print(f"Response: {response.text[:500]}")

except Exception as e:
    print(f"❌ Exception: {e}")

print()
