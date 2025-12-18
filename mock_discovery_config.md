# Mock Discovery API Setup

This directory contains a mock Discovery API server for testing dbt-mcp locally without dbt Cloud.

## Prerequisites

```bash
pip install fastapi uvicorn
```

## Running the Mock API

1. Make sure you have a fresh manifest.json:
```bash
dbt compile
# or
dbt run
```

2. Start the mock API server:
```bash
# From the jaffle_shop_duckdb directory
uvicorn mock_discovery_api:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

3. Verify it's running:
```bash
curl http://localhost:8000
```

## Configuring dbt-mcp to use the Mock API

Create or update your dbt-mcp configuration to point to the local mock API:

### Example MCP settings configuration:

```json
{
  "mcpServers": {
    "dbt-mcp-local": {
      "command": "uvx",
      "args": [
        "dbt-mcp",
        "--discovery-api-url",
        "http://localhost:8000/graphql",
        "--discovery-api-token",
        "fake-token-for-testing"
      ],
      "env": {
        "DBT_ENVIRONMENT_ID": "12345"
      }
    }
  }
}
```

## Testing

Once running, you can test the API directly:

### Get all sources
```bash
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query GetSources($environmentId: BigInt!) { environment(id: $environmentId) { applied { sources { edges { node { name uniqueId sourceName } } } } } }",
    "variables": {
      "environmentId": 12345,
      "sourcesFilter": {}
    }
  }'
```

### Get sources by source_name
```bash
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query GetSources($environmentId: BigInt!, $sourcesFilter: SourceAppliedFilter) { environment(id: $environmentId) { applied { sources(filter: $sourcesFilter) { edges { node { name uniqueId sourceName } } } } } }",
    "variables": {
      "environmentId": 12345,
      "sourcesFilter": {
        "sourceNames": ["jaffle_shop"]
      }
    }
  }'
```

### Get lineage for a model
```bash
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query GetLineage($environmentId: BigInt!, $filter: LineageFilter) { environment(id: $environmentId) { applied { lineage(filter: $filter) { ... on ModelLineageNode { uniqueId name resourceType matchesMethod } ... on SourceLineageNode { uniqueId name resourceType matchesMethod } } } } }",
    "variables": {
      "environmentId": 12345,
      "filter": {
        "uniqueIds": ["+model.jaffle_shop.orders+"]
      }
    }
  }'
```

## Supported Features

- **Sources**: List all, filter by sourceNames, uniqueIds, or identifier
- **Models**: List all, filter by modelingLayer, identifier, uniqueId, or modelName
- **Model lineage**: get_model_parents, get_model_children
- **Full lineage**: get_lineage with selector syntax (+id, id+, +id+)
- **Exposures**: List all

## Limitations

This is a simplified mock that:
- Doesn't implement authentication (accepts any token)
- Ignores environment ID
- Reads only from manifest.json (no live data)
- Doesn't track freshness status or lastRunStatus (always returns null)
- projectId is a dummy value (12345)

It's meant for development and testing purposes only.
