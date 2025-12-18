"""
Test different Discovery API URL patterns
"""

import requests

API_TOKEN = "dbtu_C2OQ-54C3lP_rXddqrSyVocB6lR0M8jT9oS8srAXEGSFLR33lY"
ENVIRONMENT_ID = "70471823504996"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

simple_query = """
{
  __schema {
    queryType {
      name
    }
  }
}
"""

urls_to_test = [
    "https://metadata.cloud.getdbt.com/graphql",
    "https://dk927.us1.dbt.com/api/graphql",
    "https://metadata.dk927.us1.dbt.com/graphql",
]

print("=" * 80)
print("Testing Different Discovery API URLs")
print("=" * 80)

for url in urls_to_test:
    print(f"\n📍 Testing: {url}")
    print("-" * 80)

    try:
        response = requests.post(
            url,
            headers=headers,
            json={"query": simple_query},
            timeout=10
        )

        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type', 'N/A')}")

        if response.status_code == 200:
            try:
                data = response.json()
                if "errors" in data:
                    print(f"❌ GraphQL Errors: {data['errors'][0].get('message', 'Unknown')}")
                elif "data" in data:
                    print(f"✅ Valid GraphQL endpoint!")
                else:
                    print(f"⚠️  Unexpected response: {data}")
            except Exception as e:
                print(f"❌ JSON parsing error: {e}")
                print(f"Response preview: {response.text[:200]}")
        else:
            print(f"❌ HTTP Error {response.status_code}")
            print(f"Response preview: {response.text[:200]}")

    except requests.exceptions.RequestException as e:
        print(f"❌ Connection Error: {e}")

print("\n" + "=" * 80)
print("Test Complete")
print("=" * 80)
