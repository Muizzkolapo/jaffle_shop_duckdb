# Mock Discovery API Setup Runbook

This runbook documents how to set up a local mock Discovery API for testing dbt-mcp without requiring dbt Cloud access.

## Overview

The mock Discovery API is a simple FastAPI server that reads from your `manifest.json` and mimics the dbt Cloud Discovery API GraphQL responses.

## Prerequisites

- A local dbt project with a compiled `manifest.json` (e.g., jaffle_shop_duckdb)
- Python with `fastapi`, `uvicorn`, and `requests` installed

## Part 1: Code Changes to dbt-mcp

These changes add support for a custom Discovery API URL via the `DBT_DISCOVERY_API_URL` environment variable.

### 1.1 Add `discovery_api_url` setting

**File:** `src/dbt_mcp/config/settings.py`

**Location:** Around line 46-57, in the `DbtMcpSettings` class

**Change:** Add this new field after `host_prefix`:

```python
class DbtMcpSettings(BaseSettings):
    # ... existing fields ...

    # dbt Platform settings
    dbt_host: str | None = Field(None, alias="DBT_HOST")
    dbt_mcp_host: str | None = Field(None, alias="DBT_MCP_HOST")
    dbt_prod_env_id: int | None = Field(None, alias="DBT_PROD_ENV_ID")
    dbt_env_id: int | None = Field(None, alias="DBT_ENV_ID")  # legacy support
    dbt_dev_env_id: int | None = Field(None, alias="DBT_DEV_ENV_ID")
    dbt_user_id: int | None = Field(None, alias="DBT_USER_ID")
    dbt_account_id: int | None = Field(None, alias="DBT_ACCOUNT_ID")
    dbt_token: str | None = Field(None, alias="DBT_TOKEN")
    multicell_account_prefix: str | None = Field(None, alias="MULTICELL_ACCOUNT_PREFIX")
    host_prefix: str | None = Field(None, alias="DBT_HOST_PREFIX")
    discovery_api_url: str | None = Field(None, alias="DBT_DISCOVERY_API_URL")  # ADD THIS LINE
```

### 1.2 Update Discovery Config Provider

**File:** `src/dbt_mcp/config/config_providers.py`

**Location:** Around line 89-108, in the `DefaultDiscoveryConfigProvider.get_config()` method

**Change:** Modify the method to check for custom URL first:

```python
async def get_config(self) -> DiscoveryConfig:
    settings, token_provider = await self.credentials_provider.get_credentials()
    assert (
        settings.actual_host
        and settings.actual_prod_environment_id
        and settings.dbt_token
    )
    # Use custom Discovery API URL if provided, otherwise construct from host
    if settings.discovery_api_url:
        url = settings.discovery_api_url
    elif settings.actual_host_prefix:
        url = f"https://{settings.actual_host_prefix}.metadata.{settings.actual_host}/graphql"
    else:
        url = f"https://metadata.{settings.actual_host}/graphql"

    return DiscoveryConfig(
        url=url,
        headers_provider=DiscoveryHeadersProvider(token_provider=token_provider),
        environment_id=settings.actual_prod_environment_id,
    )
```

**What changed:** Added the first `if settings.discovery_api_url:` check before the existing logic.

### 1.3 Update `get_all_sources` signature (Optional - for simplified testing)

**File:** `src/dbt_mcp/discovery/tools.py`

**Location:** Around line 65-75

**Change:** Simplify to only `source_names` and `unique_ids`:

```python
async def get_all_sources(
    source_names: list[str] | None = None,
    unique_ids: list[str] | None = None,
) -> list[dict]:
    return await sources_fetcher.fetch_sources(
        source_names, unique_ids
    )
```

**File:** `src/dbt_mcp/discovery/client.py`

**Location:** Around line 648-658 in `SourcesFetcher.fetch_sources()` method

**Change:** Match the simplified signature:

```python
async def fetch_sources(
    self,
    source_names: list[str] | None = None,
    unique_ids: list[str] | None = None,
) -> list[dict]:
    # Build the source_filter dict from individual parameters
    source_filter: SourceFilter = {}
    if source_names is not None:
        source_filter["sourceNames"] = source_names
    if unique_ids is not None:
        source_filter["uniqueIds"] = unique_ids

    # ... rest of the method unchanged ...
```

## Part 2: Mock Discovery API Server

Create these files in your local dbt project directory (e.g., `jaffle_shop_duckdb/`).

### 2.1 Create Mock API Server

**File:** `<your-dbt-project>/mock_discovery_api.py`

```python
"""
Mock Discovery API Server for local dbt-mcp testing.
Reads from manifest.json and provides GraphQL-like responses.

Run with: uvicorn mock_discovery_api:app --reload --port 8000
"""

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Mock Discovery API")

# Load manifest.json
MANIFEST_PATH = Path(__file__).parent / "target" / "manifest.json"


def load_manifest() -> dict:
    """Load the dbt manifest.json file."""
    with open(MANIFEST_PATH) as f:
        return json.load(f)


def get_sources_from_manifest(
    manifest: dict,
    source_names: list[str] | None = None,
    unique_ids: list[str] | None = None,
) -> list[dict]:
    """Extract sources from manifest and format them like Discovery API."""
    sources = []

    for unique_id, node in manifest.get("sources", {}).items():
        # Apply filters
        if unique_ids and unique_id not in unique_ids:
            continue
        if source_names and node.get("source_name") not in source_names:
            continue

        # Format like Discovery API response
        source_data = {
            "name": node.get("name"),
            "uniqueId": unique_id,
            "description": node.get("description", ""),
            "sourceName": node.get("source_name"),
            "resourceType": node.get("resource_type", "source"),
            "freshness": {
                "maxLoadedAt": None,
                "maxLoadedAtTimeAgoInS": None,
                "freshnessStatus": None,
            },
        }
        sources.append(source_data)

    return sources


def get_models_from_manifest(
    manifest: dict,
    modeling_layer: str | None = None,
) -> list[dict]:
    """Extract models from manifest and format them like Discovery API."""
    models = []

    for unique_id, node in manifest.get("nodes", {}).items():
        if not unique_id.startswith("model."):
            continue

        # Apply filters
        if modeling_layer:
            # Simple heuristic: check if model path contains the layer name
            path = node.get("original_file_path", "")
            if modeling_layer not in path:
                continue

        model_data = {
            "name": node.get("name"),
            "uniqueId": unique_id,
            "description": node.get("description", ""),
        }
        models.append(model_data)

    return models


@app.post("/graphql")
async def graphql_endpoint(request: Request):
    """
    Mock GraphQL endpoint that mimics dbt Cloud Discovery API.
    Handles queries for sources, models, etc.
    """
    body = await request.json()
    query = body.get("query", "")
    variables = body.get("variables", {})

    manifest = load_manifest()

    # Mock response structure
    response: dict[str, Any] = {
        "data": {
            "environment": {}
        }
    }

    # Handle GET_SOURCES query
    if "sources(" in query:
        sources_filter = variables.get("sourcesFilter", {})
        source_names = sources_filter.get("sourceNames")
        unique_ids = sources_filter.get("uniqueIds")

        sources = get_sources_from_manifest(manifest, source_names, unique_ids)

        # Format as GraphQL edges response
        edges = [{"node": source} for source in sources]

        response["data"]["environment"] = {
            "applied": {
                "sources": {
                    "pageInfo": {
                        "hasNextPage": False,
                        "endCursor": ""
                    },
                    "edges": edges
                }
            }
        }

    # Handle GET_MODELS query
    elif "models(" in query:
        models_filter = variables.get("modelsFilter", {})
        modeling_layer = models_filter.get("modelingLayer")

        models = get_models_from_manifest(manifest, modeling_layer)

        # Format as GraphQL edges response
        edges = [{"node": model} for model in models]

        response["data"]["environment"] = {
            "applied": {
                "models": {
                    "pageInfo": {
                        "endCursor": ""
                    },
                    "edges": edges
                }
            }
        }

    # Handle GET_EXPOSURES query
    elif "exposures(" in query:
        exposures = []
        for unique_id, node in manifest.get("exposures", {}).items():
            exposure_data = {
                "name": node.get("name"),
                "uniqueId": unique_id,
                "url": node.get("url", ""),
                "description": node.get("description", ""),
            }
            exposures.append(exposure_data)

        edges = [{"node": exposure} for exposure in exposures]

        response["data"]["environment"] = {
            "definition": {
                "exposures": {
                    "totalCount": len(exposures),
                    "pageInfo": {
                        "hasNextPage": False,
                        "endCursor": ""
                    },
                    "edges": edges
                }
            }
        }

    return JSONResponse(content=response)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "message": "Mock Discovery API is running",
        "manifest_path": str(MANIFEST_PATH),
        "manifest_exists": MANIFEST_PATH.exists(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 2.2 Create Test Script (Optional)

**File:** `<your-dbt-project>/test_mock_api.py`

```python
"""
Quick test script for the mock Discovery API.
Run after starting the mock API server.
"""

import requests


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
            "variables": {"environmentId": 12345}
        }
    )
    data = response.json()
    sources = data["data"]["environment"]["applied"]["sources"]["edges"]
    print(f"Found {len(sources)} sources")
    for edge in sources:
        node = edge["node"]
        print(f"  - {node['sourceName']}.{node['name']} ({node['uniqueId']})")


def test_health():
    """Test the health endpoint."""
    print("\n=== Testing: Health Check ===")
    response = requests.get("http://localhost:8000")
    data = response.json()
    print(f"Status: {data['status']}")
    print(f"Manifest exists: {data['manifest_exists']}")


if __name__ == "__main__":
    try:
        print("Testing Mock Discovery API")
        test_health()
        test_sources_all()
        print("\n✅ All tests completed!")
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to mock API.")
        print("Make sure it's running: uvicorn mock_discovery_api:app --reload --port 8000")
```

## Part 3: Configuration

### 3.1 Install Dependencies

In your dbt project directory:

```bash
pip install fastapi uvicorn requests
```

### 3.2 Configure dbt-mcp `.env`

**File:** `.env` (in dbt-mcp root directory)

Add or update these settings:

```bash
# Disable cloud-only features (keep these except Discovery)
DISABLE_SEMANTIC_LAYER=true
DISABLE_DISCOVERY=false  # Set to false to enable Discovery with mock API
DISABLE_ADMIN_API=true
DISABLE_SQL=true

# Enable local tools
DISABLE_DBT_CLI=false
DISABLE_DBT_CODEGEN=false

# Mock Discovery API configuration
DBT_DISCOVERY_API_URL=http://localhost:8000/graphql
DBT_HOST=localhost
DBT_PROD_ENV_ID=12345
DBT_DEV_ENV_ID=12345
DBT_USER_ID=175956220183410
DBT_ACCOUNT_ID=175956220182654
DBT_TOKEN=fake-token-for-testing

# Local dbt configuration
DBT_PROJECT_DIR=/path/to/your/jaffle_shop_duckdb
DBT_PATH=/path/to/your/jaffle_shop_duckdb/venv/bin/dbt
```

**Important:** Update the paths to match your actual dbt project location.

## Part 4: Testing

### 4.1 Compile your dbt project

First, ensure you have a fresh `manifest.json`:

```bash
cd /path/to/your/jaffle_shop_duckdb
dbt compile
# or
dbt run
```

### 4.2 Start the Mock API Server

In terminal 1:

```bash
cd /path/to/your/jaffle_shop_duckdb
uvicorn mock_discovery_api:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### 4.3 Test the Mock API (Optional)

In terminal 2:

```bash
cd /path/to/your/jaffle_shop_duckdb
python test_mock_api.py
```

### 4.4 Run dbt-mcp with Google ADK Agent

In terminal 2 (or 3 if you ran the test):

```bash
cd /path/to/dbt-mcp/examples/google_adk_agent
python main.py
```

### 4.5 Test with Agent

Once the agent starts, try these queries:

```
User > what tools do you have
User > Show me all sources from jaffle_shop
User > Get all sources without filtering
```

## Expected Results

When successful, you should see:
- Mock API receiving requests in terminal 1
- Agent successfully calling `get_all_sources` tool
- Sources returned from your manifest.json

Example sources for jaffle_shop:
- `source.jaffle_shop.main.raw_customers`
- `source.jaffle_shop.main.raw_orders`
- `source.jaffle_shop.main.raw_payments`

## Troubleshooting

### Mock API not starting
- Check you're in the correct directory (where mock_discovery_api.py is located)
- Verify `target/manifest.json` exists: `ls target/manifest.json`
- Install dependencies: `pip install fastapi uvicorn`

### dbt-mcp timing out
- Ensure mock API is running on port 8000
- Check `.env` has `DBT_DISCOVERY_API_URL=http://localhost:8000/graphql`
- Verify `DISABLE_DISCOVERY=false` in `.env`

### Connection refused errors
- Check the URL in error message - should be `localhost:8000`, not `metadata.localhost`
- If you see `metadata.localhost`, the custom URL setting isn't being picked up
- Verify you made the code changes in Part 1

### No sources returned
- Run `dbt compile` or `dbt run` to regenerate manifest.json
- Check manifest has sources: `cat target/manifest.json | grep '"sources"'`
- Restart mock API after regenerating manifest

## Reverting Changes

To disable mock Discovery API and go back to cloud:

1. **Stop the mock API server** (Ctrl+C in terminal 1)

2. **Update `.env`:**
   ```bash
   DISABLE_DISCOVERY=true  # or remove DBT_DISCOVERY_API_URL
   # Restore your actual cloud settings
   DBT_HOST=cloud.getdbt.com
   DBT_TOKEN=your-actual-token
   ```

3. **Restart dbt-mcp/agent**

The code changes in Part 1 are backward compatible - they don't affect normal cloud usage.

## Known Issues and Fixes

### Issue: `get_model_parents` and `get_model_children` Not Working

**Problem:** The initial mock API implementation only handled basic queries for listing models and sources. Queries that requested the `parents` or `children` fields on models would return empty responses because the mock API didn't extract lineage information from the manifest.

**Root Cause:** The manifest contains `parent_map` and `child_map` that track dependencies between models, sources, and other resources. The mock API needs to:
1. Detect when a query requests `parents` or `children` fields
2. Look up the target model's unique_id in the parent_map/child_map
3. Format the related nodes (parents/children) properly according to their resource type

**Solution:** The updated `mock_discovery_api.py` now includes:

1. **Helper function `format_node_as_parent_child()`**: Formats different node types (models, sources, seeds, snapshots, exposures, metrics) into the structure expected by the Discovery API for parents/children responses.

2. **Helper function `get_model_parents()`**: Extracts parents from the manifest's `parent_map` and filters to include only relevant resource types (models, sources, seeds, snapshots - excluding tests).

3. **Helper function `get_model_children()`**: Extracts children from the manifest's `child_map` and filters to include only relevant resource types (models, exposures, metrics - excluding tests).

4. **Enhanced query handler**: The models query handler now:
   - Detects if the query contains "parents" or "children" keywords
   - Identifies if it's a specific model query (with modelName, uniqueId, OR identifier filter)
   - When a specific model is requested, finds the target model
   - Conditionally adds parents/children fields ONLY if they're requested in the query
   - Falls back to simple model listing for queries without model filters

**Key Fixes:**
1. The original implementation only added parents/children when BOTH a model filter AND lineage fields were present in the query. The fix changes this to handle ANY specific model query, and conditionally adds parents/children based on what's requested in the query.

2. **Important:** dbt-mcp unified `resources()` query pattern with `AppliedResourcesFilter`. The filter accepts `uniqueIds` (list of IDs) and `types` (list of resource types). The mock API now supports:
   - `packages` query to list all package names
   - Unified `resources()` endpoint that filters by `uniqueIds` and `types`
   - Legacy `identifier` field support for backward compatibility

**Verification:** After applying the fix, these tools now work correctly:
- `get_model_parents` - Returns the upstream models and sources for a given model
- `get_model_children` - Returns the downstream models and exposures for a given model
- `get_all_sources` - Still works as before (regression tested)

### Issue: Seed and Snapshot Search Support

**Problem:** The `get_lineage` tool supports searching seeds and snapshots by name, but the mock API didn't have handlers for these resource types.

**Solution:** The mock API now includes:

1. **`get_seeds_from_manifest()` function**: Extracts seeds from the manifest and supports filtering by `identifier` or `uniqueIds`.

2. **`get_snapshots_from_manifest()` function**: Extracts snapshots from the manifest and supports filtering by `identifier` or `uniqueIds`.

3. **Seeds query handler**: Detects queries containing `seeds(` and handles the `GenericMaterializedFilter` with `identifier` field.

4. **Snapshots query handler**: Detects queries containing `snapshots(` and handles the `GenericMaterializedFilter` with `identifier` field.

**Supported Operations:**
```
# Search for seed by name
get_lineage(name="country_codes")  # Searches seeds if not found in models/sources

# Search for snapshot by name
get_lineage(name="orders_snapshot")  # Searches snapshots if not found in other types

# Direct queries
GET_SEEDS with identifier filter
GET_SNAPSHOTS with identifier filter
```

**Test Coverage:**
The `test_mock_api.py` now includes:
- `test_seeds_by_identifier()` - Tests seed search by name
- `test_snapshots_by_identifier()` - Tests snapshot search by name

### Issue: Exposure Filtering Support

**Problem:** The mock API returned ALL exposures without any filtering, making it hard to test lineage disambiguation and unique_id-based queries for exposures.

**Solution:** The mock API now supports proper `ExposureFilter` filtering:

1. **`get_exposures_from_manifest()` function**: Extracts exposures and supports all ExposureFilter fields.

2. **Exposure query handler**: Now properly parses and applies filters from the `filter` variable.

**Supported ExposureFilter Fields** (matching real Discovery API):
- ✅ `uniqueIds` - Filter by unique IDs
- ✅ `exposureType` - Filter by type (dashboard, notebook, etc.)
- ✅ `tags` - Filter by tags (returns exposures with ANY matching tag)
- ❌ `identifier` - NOT supported (matches real API limitation)

**Example Usage:**
```python
# Filter by unique ID
GET_EXPOSURES with filter: { uniqueIds: ["exposure.proj.dashboard"] }

# Filter by type
GET_EXPOSURES with filter: { exposureType: "dashboard" }

# Filter by tags
GET_EXPOSURES with filter: { tags: ["finance", "executive"] }
```

**Test Coverage:**
- `test_exposures_all()` - Gets all exposures without filtering
- `test_exposures_by_unique_id()` - Tests filtering by unique_id

### Issue: `get_lineage` Tool Support

**Problem:** The new `get_lineage` tool uses the Discovery API's `lineage` query with dbt selector syntax, which wasn't implemented in the mock API.

**Solution:** The mock API now includes:

1. **Lineage query handler**: Detects queries containing `lineage(` and handles them appropriately.

2. **Selector syntax parsing**: Parses dbt selector syntax:
   - `+uniqueId` - ancestors only
   - `uniqueId+` - descendants only
   - `+uniqueId+` - both directions

3. **Helper function `get_all_descendants()`**: Recursively traverses the manifest's `child_map` to get all downstream nodes.

4. **Helper function `format_lineage_node()`**: Formats nodes according to the LineageNode schema with all required fields:
   - Common fields: `uniqueId`, `name`, `resourceType`, `filePath`, `matchesMethod`, `tags`, `projectId`, `fqn`
   - Type-specific fields for Model, Source, Seed, Snapshot, Test

5. **`identifier` filter for sources**: The source search now supports filtering by `identifier` (source name), enabling proper name resolution.

**Supported `get_lineage` Parameters:**
- `name` - Resource name (searches models, sources, seeds, and snapshots by identifier)
- `unique_id` - Full unique ID for precise lookup (required for exposures, tests, metrics)
- `direction` - "ancestors", "descendants", or "both" (default)
- `types` - Optional filter for specific resource types

**Example Usage:**
```
# Search by name (works for models, sources, seeds, snapshots)
get_lineage(name="orders")
get_lineage(name="raw_data")  # Seed
get_lineage(name="orders_snapshot")  # Snapshot
get_lineage(name="orders", direction="ancestors")

# Search by unique_id (works for all resource types)
get_lineage(unique_id="model.jaffle_shop.orders", direction="descendants")
get_lineage(unique_id="exposure.jaffle_shop.dashboard")  # Exposures require unique_id

# Filter by resource types
get_lineage(name="customers", types=["Model", "Source"])
```

**Response Structure:**
```json
{
  "target": { ... },      // The requested resource (matchesMethod=true)
  "ancestors": [ ... ],   // Upstream dependencies
  "descendants": [ ... ]  // Downstream dependencies
}
```

---

## Mock API Feature Matrix

Complete overview of mock API capabilities:

| Resource Type | Search by Name (`identifier`) | Filter by `uniqueIds` | Other Filters | Lineage Support |
|--------------|------------------------------|----------------------|---------------|-----------------|
| **Models** | ✅ Yes | ✅ Yes | `modelingLayer` | ✅ Yes |
| **Sources** | ✅ Yes | ✅ Yes | `sourceNames` | ✅ Yes |
| **Seeds** | ✅ Yes | ✅ Yes | - | ✅ Yes |
| **Snapshots** | ✅ Yes | ✅ Yes | - | ✅ Yes |
| **Exposures** | ❌ No (API limitation) | ✅ Yes | `exposureType`, `tags` | ✅ Yes |
| **Tests** | ❌ No | ✅ Yes | - | ✅ Yes |
| **Metrics** | ❌ No | ✅ Yes | - | ✅ Yes |

### Key Capabilities:

**Name Resolution (`identifier` filter):**
- ✅ Models, Sources, Seeds, Snapshots - can search by short name
- ❌ Exposures, Tests, Metrics - require full `unique_id` (matches real API)

**Lineage Queries:**
- ✅ All resource types supported via `unique_id`
- ✅ Selector syntax: `+id` (ancestors), `id+` (descendants), `+id+` (both)
- ✅ Type filtering with `types` parameter
- ✅ Proper categorization of ancestors vs descendants

**Advanced Filtering:**
- ✅ Exposures: Filter by type, tags, or unique IDs
- ✅ Sources: Filter by source names or unique IDs
- ✅ Models: Filter by modeling layer or unique IDs

**Test Coverage:**
All features have corresponding test cases in `test_mock_api.py`
