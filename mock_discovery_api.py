"""
Mock Discovery API Server for local dbt-mcp testing.
Reads from manifest.json and provides GraphQL-like responses.

Supports:
- packages query: Returns list of package names from manifest
- resources() query: Unified endpoint using AppliedResourcesFilter (uniqueIds + types)
- Legacy endpoints: models, sources, seeds, snapshots, exposures (with identifier support)
- lineage query: Returns lineage trees using dbt selector syntax

Run with: uvicorn mock_discovery_api:app --reload --port 8000
"""
import sys
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
    identifier: str | None = None,
) -> list[dict]:
    """Extract sources from manifest and format them like Discovery API."""
    sources = []

    for unique_id, node in manifest.get("sources", {}).items():
        # Apply filters
        if unique_ids and unique_id not in unique_ids:
            continue
        if source_names and node.get("source_name") not in source_names:
            continue
        # Filter by identifier (source name) - used by search_sources_by_name
        if identifier and node.get("name") != identifier:
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
    unique_ids: list[str] | None = None,
    identifier: str | None = None,
) -> list[dict]:
    """Extract models from manifest and format them like Discovery API."""
    models = []

    for unique_id, node in manifest.get("nodes", {}).items():
        if not unique_id.startswith("model."):
            continue

        # Apply filters
        if unique_ids and unique_id not in unique_ids:
            continue
        if identifier and node.get("name") != identifier:
            continue
        if modeling_layer:
            # Simple heuristic: check if model path contains the layer name
            path = node.get("original_file_path", "")
            if modeling_layer not in path:
                continue

        model_data = {
            "name": node.get("name"),
            "uniqueId": unique_id,
            "description": node.get("description", ""),
            "resourceType": "Model",
        }
        models.append(model_data)

    return models


def get_seeds_from_manifest(
    manifest: dict,
    unique_ids: list[str] | None = None,
    identifier: str | None = None,
) -> list[dict]:
    """Extract seeds from manifest and format them like Discovery API."""
    seeds = []

    for unique_id, node in manifest.get("nodes", {}).items():
        if not unique_id.startswith("seed."):
            continue

        # Apply filters
        if unique_ids and unique_id not in unique_ids:
            continue
        if identifier and node.get("name") != identifier:
            continue

        seed_data = {
            "name": node.get("name"),
            "uniqueId": unique_id,
            "resourceType": "Seed",
        }
        seeds.append(seed_data)

    return seeds


def get_snapshots_from_manifest(
    manifest: dict,
    unique_ids: list[str] | None = None,
    identifier: str | None = None,
) -> list[dict]:
    """Extract snapshots from manifest and format them like Discovery API."""
    snapshots = []

    for unique_id, node in manifest.get("nodes", {}).items():
        if not unique_id.startswith("snapshot."):
            continue

        # Apply filters
        if unique_ids and unique_id not in unique_ids:
            continue
        if identifier and node.get("name") != identifier:
            continue

        snapshot_data = {
            "name": node.get("name"),
            "uniqueId": unique_id,
            "resourceType": "Snapshot",
        }
        snapshots.append(snapshot_data)

    return snapshots


def get_exposures_from_manifest(
    manifest: dict,
    unique_ids: list[str] | None = None,
    exposure_type: str | None = None,
    tags: list[str] | None = None,
) -> list[dict]:
    """Extract exposures from manifest and format them like Discovery API.

    Supports ExposureFilter fields:
    - uniqueIds: Filter by unique IDs
    - exposureType: Filter by exposure type (dashboard, notebook, etc.)
    - tags: Filter by tags (returns exposures that have ANY of the specified tags)

    Note: Does NOT support filtering by name/identifier (matches real API limitation)
    """
    exposures = []

    for unique_id, node in manifest.get("exposures", {}).items():
        # Apply filters
        if unique_ids and unique_id not in unique_ids:
            continue
        if exposure_type and node.get("type") != exposure_type:
            continue
        if tags:
            # Check if exposure has any of the specified tags
            exposure_tags = set(node.get("tags", []))
            if not exposure_tags.intersection(tags):
                continue

        exposure_data = {
            "name": node.get("name"),
            "uniqueId": unique_id,
            "url": node.get("url", ""),
            "description": node.get("description", ""),
            "type": node.get("type", ""),
            "maturity": node.get("maturity"),
            "owner": node.get("owner", {}),
            "tags": node.get("tags", []),
        }
        exposures.append(exposure_data)

    return exposures


def format_node_as_parent_child(manifest: dict, unique_id: str) -> dict:
    """Format a node (model, source, etc.) for parents/children response."""
    # Check if it's a model
    if unique_id.startswith("model."):
        node = manifest.get("nodes", {}).get(unique_id, {})
        return {
            "resourceType": "model",
            "name": node.get("name"),
            "description": node.get("description", ""),
            "uniqueId": unique_id,
        }
    # Check if it's a source
    elif unique_id.startswith("source."):
        node = manifest.get("sources", {}).get(unique_id, {})
        return {
            "resourceType": "source",
            "name": node.get("name"),
            "description": node.get("description", ""),
            "sourceName": node.get("source_name"),
            "uniqueId": unique_id,
        }
    # Check if it's a seed
    elif unique_id.startswith("seed."):
        node = manifest.get("nodes", {}).get(unique_id, {})
        return {
            "resourceType": "seed",
            "name": node.get("name"),
            "description": node.get("description", ""),
            "uniqueId": unique_id,
        }
    # Check if it's a snapshot
    elif unique_id.startswith("snapshot."):
        node = manifest.get("nodes", {}).get(unique_id, {})
        return {
            "resourceType": "snapshot",
            "name": node.get("name"),
            "description": node.get("description", ""),
            "uniqueId": unique_id,
        }
    # Check if it's an exposure
    elif unique_id.startswith("exposure."):
        node = manifest.get("exposures", {}).get(unique_id, {})
        return {
            "resourceType": "exposure",
            "name": node.get("name"),
            "description": node.get("description", ""),
            "uniqueId": unique_id,
        }
    # Check if it's a metric
    elif unique_id.startswith("metric."):
        node = manifest.get("metrics", {}).get(unique_id, {})
        return {
            "resourceType": "metric",
            "name": node.get("name"),
            "description": node.get("description", ""),
            "uniqueId": unique_id,
        }
    # Default fallback
    else:
        return {
            "resourceType": "unknown",
            "name": unique_id.split(".")[-1] if "." in unique_id else unique_id,
            "description": "",
        }


def get_model_parents(manifest: dict, unique_id: str) -> list[dict]:
    """Get parents of a model from the manifest."""
    parent_map = manifest.get("parent_map", {})
    parent_ids = parent_map.get(unique_id, [])

    # Filter to only include models, sources, seeds, and snapshots (not tests or other types)
    filtered_parents = [
        pid for pid in parent_ids
        if pid.startswith(("model.", "source.", "seed.", "snapshot."))
    ]

    return [format_node_as_parent_child(manifest, pid) for pid in filtered_parents]


def get_model_children(manifest: dict, unique_id: str) -> list[dict]:
    """Get children of a model from the manifest."""
    child_map = manifest.get("child_map", {})
    child_ids = child_map.get(unique_id, [])

    # Filter to only include models, exposures, metrics (not tests)
    filtered_children = [
        cid for cid in child_ids
        if cid.startswith(("model.", "exposure.", "metric."))
    ]

    return [format_node_as_parent_child(manifest, cid) for cid in filtered_children]


def get_model_ancestors(manifest: dict, unique_id: str, visited: set[str] | None = None) -> list[dict]:
    """Get all ancestors (recursive parents) of a model from the manifest."""
    if visited is None:
        visited = set()

    # Prevent cycles
    if unique_id in visited:
        return []
    visited.add(unique_id)

    parent_map = manifest.get("parent_map", {})
    parent_ids = parent_map.get(unique_id, [])

    # Filter to only include models, sources, seeds, and snapshots (not tests)
    filtered_parents = [
        pid for pid in parent_ids
        if pid.startswith(("model.", "source.", "seed.", "snapshot."))
    ]

    # Build list of all ancestors
    all_ancestors = []
    for parent_id in filtered_parents:
        # Add this parent
        all_ancestors.append(format_node_as_parent_child(manifest, parent_id))
        # Recursively get this parent's ancestors
        grandparents = get_model_ancestors(manifest, parent_id, visited)
        all_ancestors.extend(grandparents)

    return all_ancestors


def get_all_descendants(manifest: dict, unique_id: str, visited: set[str] | None = None) -> list[dict]:
    """Get all descendants (recursive children) of a node from the manifest."""
    if visited is None:
        visited = set()

    # Prevent cycles
    if unique_id in visited:
        return []
    visited.add(unique_id)

    child_map = manifest.get("child_map", {})
    child_ids = child_map.get(unique_id, [])

    # Filter to only include relevant resource types (not tests)
    filtered_children = [
        cid for cid in child_ids
        if cid.startswith(("model.", "exposure.", "metric.", "snapshot.", "seed."))
    ]

    # Build list of all descendants
    all_descendants = []
    for child_id in filtered_children:
        # Add this child
        all_descendants.append(format_node_as_parent_child(manifest, child_id))
        # Recursively get this child's descendants
        grandchildren = get_all_descendants(manifest, child_id, visited)
        all_descendants.extend(grandchildren)

    return all_descendants


def format_lineage_node(manifest: dict, unique_id: str, matches_method: bool = False) -> dict | None:
    """Format a node for lineage response with all required fields."""
    node = None
    resource_type = None

    # Find the node in manifest
    if unique_id.startswith("model."):
        node = manifest.get("nodes", {}).get(unique_id)
        resource_type = "Model"
    elif unique_id.startswith("source."):
        node = manifest.get("sources", {}).get(unique_id)
        resource_type = "Source"
    elif unique_id.startswith("seed."):
        node = manifest.get("nodes", {}).get(unique_id)
        resource_type = "Seed"
    elif unique_id.startswith("snapshot."):
        node = manifest.get("nodes", {}).get(unique_id)
        resource_type = "Snapshot"
    elif unique_id.startswith("exposure."):
        node = manifest.get("exposures", {}).get(unique_id)
        resource_type = "Exposure"
    elif unique_id.startswith("metric."):
        node = manifest.get("metrics", {}).get(unique_id)
        resource_type = "Metric"
    elif unique_id.startswith("test."):
        node = manifest.get("nodes", {}).get(unique_id)
        resource_type = "Test"

    if not node:
        return None

    # Build lineage node with all fields from our GraphQL query
    lineage_node = {
        "uniqueId": unique_id,
        "name": node.get("name", ""),
        "resourceType": resource_type,
        "filePath": node.get("original_file_path", ""),
        "matchesMethod": matches_method,
        "tags": node.get("tags", []),
        "projectId": 12345,  # Dummy value - real API returns actual project ID
        "fqn": node.get("fqn", []),
    }

    # Add type-specific fields
    if resource_type == "Model":
        lineage_node["database"] = node.get("database", "")
        lineage_node["schema"] = node.get("schema", "")
        lineage_node["alias"] = node.get("alias", "")
        lineage_node["materializationType"] = node.get("config", {}).get("materialized", "")
        lineage_node["lastRunStatus"] = None  # Not available in manifest

    elif resource_type == "Source":
        lineage_node["database"] = node.get("database", "")
        lineage_node["schema"] = node.get("schema", "")
        lineage_node["sourceName"] = node.get("source_name", "")
        lineage_node["lastRunStatus"] = None

    elif resource_type in ("Seed", "Snapshot"):
        lineage_node["database"] = node.get("database", "")
        lineage_node["schema"] = node.get("schema", "")
        lineage_node["alias"] = node.get("alias", "")
        lineage_node["lastRunStatus"] = None

    elif resource_type == "Test":
        lineage_node["lastRunStatus"] = None

    return lineage_node


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

    # Handle unified resources() query FIRST ('s pattern)
    # IMPORTANT: Check this before legacy endpoints to avoid false matches
    if "resources" in query and ("resources(" in query or "resources {" in query):
        resource_filter = variables.get("filter", {})
        unique_ids = resource_filter.get("uniqueIds", [])
        types = resource_filter.get("types", [])

        print(f"[RESOURCES QUERY] Filters: uniqueIds={unique_ids}, types={types}", file=sys.stderr)

        all_resources = []

        # Fetch each resource type requested
        for resource_type in types:
            if resource_type == "Model":
                models = get_models_from_manifest(manifest, unique_ids=unique_ids)
                all_resources.extend(models)
            elif resource_type == "Source":
                sources = get_sources_from_manifest(manifest, unique_ids=unique_ids)
                all_resources.extend(sources)
            elif resource_type == "Seed":
                seeds = get_seeds_from_manifest(manifest, unique_ids=unique_ids)
                all_resources.extend(seeds)
            elif resource_type == "Snapshot":
                snapshots = get_snapshots_from_manifest(manifest, unique_ids=unique_ids)
                all_resources.extend(snapshots)

        # If no types specified, return all resources matching uniqueIds
        if not types and unique_ids:
            all_resources.extend(get_models_from_manifest(manifest, unique_ids=unique_ids))
            all_resources.extend(get_sources_from_manifest(manifest, unique_ids=unique_ids))
            all_resources.extend(get_seeds_from_manifest(manifest, unique_ids=unique_ids))
            all_resources.extend(get_snapshots_from_manifest(manifest, unique_ids=unique_ids))

        print(f"[RESOURCES QUERY] Returning {len(all_resources)} resources", file=sys.stderr)

        edges = [{"node": resource} for resource in all_resources]

        response["data"]["environment"] = {
            "applied": {
                "resources": {
                    "pageInfo": {
                        "hasNextPage": False,
                        "endCursor": ""
                    },
                    "edges": edges
                }
            }
        }

    # Handle GET_SOURCES query
    elif "sources" in query and ("sources(" in query or "sources {" in query):
        sources_filter = variables.get("sourcesFilter", {})
        source_names = sources_filter.get("sourceNames")
        unique_ids = sources_filter.get("uniqueIds")
        identifier = sources_filter.get("identifier")

        print(f"[SOURCES QUERY] Filters: sourceNames={source_names}, uniqueIds={unique_ids}, identifier={identifier}", file=sys.stderr)

        sources = get_sources_from_manifest(manifest, source_names, unique_ids, identifier)

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

    # Handle GET_MODELS query (including parents/children)
    elif "models" in query and ("models(" in query or "models {" in query):
        models_filter = variables.get("modelsFilter", {})
        modeling_layer = models_filter.get("modelingLayer")

        # Check if this is a specific model query (has filters)
        # Note: dbt-mcp sends 'uniqueIds' (list), 'identifier' (string), or 'modelName' (string)
        unique_ids_filter = models_filter.get("uniqueIds") if models_filter else None
        identifier_filter = models_filter.get("identifier") if models_filter else None
        model_name_filter = models_filter.get("modelName") if models_filter else None

        # Extract single value from uniqueIds list if present
        unique_id_filter = unique_ids_filter[0] if unique_ids_filter and len(unique_ids_filter) > 0 else None

        # Use identifier as model_name if provided
        if identifier_filter and not model_name_filter:
            model_name_filter = identifier_filter

        # Debug logging
        print(f"[MODELS QUERY] Filters: uniqueIds={unique_ids_filter}, identifier={identifier_filter}, modelName={model_name_filter}", file=sys.stderr)
        print(f"[MODELS QUERY] Resolved: unique_id={unique_id_filter}, model_name={model_name_filter}", file=sys.stderr)

        # Determine if query asks for parents, children, or ancestors
        has_parents = "parents" in query
        has_children = "children" in query
        has_ancestors = "ancestors" in query

        # Check if this is a query for a specific model (with or without lineage)
        if model_name_filter or unique_id_filter:
            # Single model query - find the specific model
            target_model = None
            for unique_id, node in manifest.get("nodes", {}).items():
                if not unique_id.startswith("model."):
                    continue
                # Match by full unique_id
                if unique_id_filter and unique_id == unique_id_filter:
                    target_model = (unique_id, node)
                    break
                # Match by name (either from model_name_filter or short unique_id_filter)
                if model_name_filter and node.get("name") == model_name_filter:
                    target_model = (unique_id, node)
                    break
                # Handle case where unique_id_filter is just the model name (not full unique_id)
                if unique_id_filter and not unique_id_filter.startswith("model.") and node.get("name") == unique_id_filter:
                    target_model = (unique_id, node)
                    break

            if target_model:
                unique_id, node = target_model
                print(f"[MODELS QUERY] Found model: {unique_id}, node keys: {list(node.keys())[:10]}", file=sys.stderr)
                model_data = {
                    "name": node.get("name"),
                    "uniqueId": unique_id,
                    "description": node.get("description", ""),
                    "resourceType": node.get("resource_type", "model"),
                }
                print(f"[MODELS QUERY] resourceType from manifest: {node.get('resource_type')}", file=sys.stderr)

                # Add additional fields if requested in query
                if "compiledCode" in query:
                    model_data["compiledCode"] = node.get("compiled_code", node.get("raw_code", ""))
                if "database" in query:
                    model_data["database"] = node.get("database", "")
                if "schema" in query:
                    model_data["schema"] = node.get("schema", "")
                if "alias" in query:
                    model_data["alias"] = node.get("alias", "")
                if "catalog" in query:
                    # Simplified catalog response
                    columns = node.get("columns", {})
                    model_data["catalog"] = {
                        "columns": [
                            {
                                "name": col_name,
                                "description": col_data.get("description", ""),
                                "type": col_data.get("data_type", ""),
                            }
                            for col_name, col_data in columns.items()
                        ]
                    }

                # Add parents, children, or ancestors if requested
                if has_parents:
                    parents = get_model_parents(manifest, unique_id)
                    model_data["parents"] = parents
                    print(f"[MODELS QUERY] Added {len(parents)} parents to response", file=sys.stderr)
                if has_children:
                    children = get_model_children(manifest, unique_id)
                    model_data["children"] = children
                    print(f"[MODELS QUERY] Added {len(children)} children to response", file=sys.stderr)
                if has_ancestors:
                    ancestors = get_model_ancestors(manifest, unique_id)
                    model_data["ancestors"] = ancestors
                    print(f"[MODELS QUERY] Added {len(ancestors)} ancestors to response", file=sys.stderr)

                print(f"[MODELS QUERY] Response node keys: {list(model_data.keys())}", file=sys.stderr)
                edges = [{"node": model_data}]
            else:
                print(f"[MODELS QUERY] Model not found!", file=sys.stderr)
                edges = []
        else:
            # List all models
            models = get_models_from_manifest(manifest, modeling_layer)
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

    # Handle GET_LINEAGE query
    elif "lineage" in query and ("lineage(" in query or "lineage {" in query):
        lineage_filter = variables.get("filter", {})
        unique_ids = lineage_filter.get("uniqueIds", [])
        types_filter = lineage_filter.get("types")

        print(f"[LINEAGE QUERY] Filter: uniqueIds={unique_ids}, types={types_filter}", file=sys.stderr)

        lineage_nodes = []

        for selector in unique_ids:
            # Parse selector syntax: +id (ancestors), id+ (descendants), +id+ (both)
            get_ancestors = selector.startswith("+")
            get_descendants = selector.endswith("+")

            # Extract the actual unique_id
            target_id = selector.strip("+")

            print(f"[LINEAGE QUERY] Selector: {selector} -> target={target_id}, ancestors={get_ancestors}, descendants={get_descendants}", file=sys.stderr)

            # Add target node with matchesMethod=true
            target_node = format_lineage_node(manifest, target_id, matches_method=True)
            if target_node:
                lineage_nodes.append(target_node)

            # Add ancestors
            if get_ancestors:
                ancestors = get_model_ancestors(manifest, target_id)
                for ancestor in ancestors:
                    node = format_lineage_node(manifest, ancestor["uniqueId"], matches_method=False)
                    if node and (not types_filter or node.get("resourceType") in types_filter):
                        lineage_nodes.append(node)

            # Add descendants
            if get_descendants:
                descendants = get_all_descendants(manifest, target_id)
                for desc in descendants:
                    node = format_lineage_node(manifest, desc["uniqueId"], matches_method=False)
                    if node and (not types_filter or node.get("resourceType") in types_filter):
                        lineage_nodes.append(node)

        print(f"[LINEAGE QUERY] Returning {len(lineage_nodes)} nodes", file=sys.stderr)

        response["data"]["environment"] = {
            "applied": {
                "lineage": lineage_nodes
            }
        }

    # Handle GET_SEEDS query
    elif "seeds" in query and ("seeds(" in query or "seeds {" in query):
        seeds_filter = variables.get("seedsFilter", {})
        unique_ids = seeds_filter.get("uniqueIds")
        identifier = seeds_filter.get("identifier")

        print(f"[SEEDS QUERY] Filters: uniqueIds={unique_ids}, identifier={identifier}", file=sys.stderr)

        seeds = get_seeds_from_manifest(manifest, unique_ids, identifier)

        # Format as GraphQL edges response
        edges = [{"node": seed} for seed in seeds]

        response["data"]["environment"] = {
            "applied": {
                "seeds": {
                    "pageInfo": {
                        "hasNextPage": False,
                        "endCursor": ""
                    },
                    "edges": edges
                }
            }
        }

    # Handle GET_SNAPSHOTS query
    elif "snapshots" in query and ("snapshots(" in query or "snapshots {" in query):
        snapshots_filter = variables.get("snapshotsFilter", {})
        unique_ids = snapshots_filter.get("uniqueIds")
        identifier = snapshots_filter.get("identifier")

        print(f"[SNAPSHOTS QUERY] Filters: uniqueIds={unique_ids}, identifier={identifier}", file=sys.stderr)

        snapshots = get_snapshots_from_manifest(manifest, unique_ids, identifier)

        # Format as GraphQL edges response
        edges = [{"node": snapshot} for snapshot in snapshots]

        response["data"]["environment"] = {
            "applied": {
                "snapshots": {
                    "pageInfo": {
                        "hasNextPage": False,
                        "endCursor": ""
                    },
                    "edges": edges
                }
            }
        }

    # Handle GET_PACKAGES query
    elif "packages" in query and ("packages(" in query or "packages {" in query):
        print(f"[PACKAGES QUERY] Extracting package names from manifest", file=sys.stderr)

        # Extract unique package names from manifest
        packages = set()
        for unique_id in manifest.get("nodes", {}).keys():
            # unique_id format: resource_type.package_name.resource_name
            parts = unique_id.split(".")
            if len(parts) >= 2:
                packages.add(parts[1])

        # Also check sources
        for unique_id in manifest.get("sources", {}).keys():
            parts = unique_id.split(".")
            if len(parts) >= 2:
                packages.add(parts[1])

        packages_list = sorted(list(packages))
        print(f"[PACKAGES QUERY] Found packages: {packages_list}", file=sys.stderr)

        response["data"]["environment"] = {
            "applied": {
                "packages": packages_list
            }
        }

    # Handle GET_EXPOSURES query
    elif "exposures" in query and ("exposures(" in query or "exposures {" in query):
        # ExposureFilter supports: uniqueIds, exposureType, tags (but NOT identifier/name)
        exposure_filter = variables.get("filter", {})
        unique_ids = exposure_filter.get("uniqueIds")
        exposure_type = exposure_filter.get("exposureType")
        tags = exposure_filter.get("tags")

        print(f"[EXPOSURES QUERY] Filters: uniqueIds={unique_ids}, exposureType={exposure_type}, tags={tags}", file=sys.stderr)

        exposures = get_exposures_from_manifest(
            manifest,
            unique_ids=unique_ids,
            exposure_type=exposure_type,
            tags=tags
        )

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
