import os
from functools import lru_cache

from dotenv import load_dotenv
from elasticsearch import ApiError, AuthenticationException, ConnectionError, Elasticsearch, NotFoundError

load_dotenv()

PRODUCTS_INDEX = os.getenv("ELASTICSEARCH_PRODUCTS_INDEX", "products-v1")
EVIDENCE_INDEX = os.getenv("ELASTICSEARCH_EVIDENCE_INDEX", "product-evidence-v1")
EVALUATIONS_INDEX = os.getenv("ELASTICSEARCH_EVALUATIONS_INDEX", "product-evaluations-v1")
OBSERVATIONS_INDEX = os.getenv("ELASTICSEARCH_OBSERVATIONS_INDEX", "product-listing-observations-v1")
CURRENT_LISTINGS_INDEX = os.getenv("ELASTICSEARCH_CURRENT_INDEX", "product-listing-current-v1")
CHANGE_EVENTS_INDEX = os.getenv("ELASTICSEARCH_CHANGES_INDEX", "product-change-events-v1")
SOURCE_HEALTH_INDEX = os.getenv("ELASTICSEARCH_SOURCE_HEALTH_INDEX", "product-source-health-v1")
QUARANTINE_INDEX = os.getenv("ELASTICSEARCH_QUARANTINE_INDEX", "product-observation-quarantine-v1")


class ProductSearchError(RuntimeError): pass
class ProductSearchUnavailable(ProductSearchError): pass
class ProductIndexMissing(ProductSearchError): pass


def require_write_access() -> None:
    if os.getenv("ES_ALLOW_WRITES") != "1":
        raise ProductSearchError("Elasticsearch writes are disabled. Set ES_ALLOW_WRITES=1 for this intentional command.")


@lru_cache(maxsize=1)
def get_elasticsearch_client() -> Elasticsearch:
    url = os.getenv("ELASTICSEARCH_URL")
    if not url:
        raise ProductSearchUnavailable("ELASTICSEARCH_URL is not configured.")
    api_key = os.getenv("ELASTICSEARCH_API_KEY") or None
    try:
        return Elasticsearch(url, api_key=api_key, request_timeout=15, retry_on_timeout=True, max_retries=1)
    except Exception as error:
        raise ProductSearchUnavailable("Product search is temporarily unavailable.") from error


def test_connection(client: Elasticsearch | None = None) -> dict:
    client = client or get_elasticsearch_client()
    try:
        info = client.info()
        return {"reachable": True, "cluster_name": info.get("cluster_name", "unknown"), "version": info.get("version", {}).get("number", "unknown"), "indices": {name: bool(client.indices.exists(index=name)) for name in [PRODUCTS_INDEX, EVIDENCE_INDEX, EVALUATIONS_INDEX, OBSERVATIONS_INDEX, CURRENT_LISTINGS_INDEX, CHANGE_EVENTS_INDEX, SOURCE_HEALTH_INDEX, QUARANTINE_INDEX]}}
    except AuthenticationException as error:
        raise ProductSearchUnavailable("Elasticsearch authentication failed.") from error
    except (ConnectionError, ApiError) as error:
        raise ProductSearchUnavailable("Product search is temporarily unavailable.") from error


def translate_elasticsearch_error(error: Exception) -> ProductSearchError:
    if isinstance(error, NotFoundError): return ProductIndexMissing("The product catalog index has not been initialized.")
    if isinstance(error, AuthenticationException): return ProductSearchUnavailable("Elasticsearch authentication failed.")
    return ProductSearchUnavailable("Product search is temporarily unavailable.")
