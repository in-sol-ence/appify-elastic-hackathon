from elasticsearch import ApiError

from models.products import EvidenceFilters, ProductEvidence
from services.elasticsearch_client import EVIDENCE_INDEX, get_elasticsearch_client, translate_elasticsearch_error


def search_product_evidence(product_id:str,query:str,filters:EvidenceFilters|None=None,limit:int=10,client=None)->list[ProductEvidence]:
    client=client or get_elasticsearch_client();filters=filters or EvidenceFilters();exact=[{"term":{"product_id":product_id}}]
    for field in ["source_type","hardware_revision","firmware_version","operating_system","software_version"]:
        value=getattr(filters,field)
        if value:exact.append({"term":{field:value}})
    if filters.minimum_source_authority is not None:exact.append({"range":{"source_authority":{"gte":filters.minimum_source_authority}}})
    if filters.published_after:exact.append({"range":{"published_at":{"gte":filters.published_after.isoformat()}}})
    lexical={"bool":{"filter":exact,"must":[{"multi_match":{"query":query,"fields":["title^3","text"]}}]}}
    hybrid={"bool":{"filter":exact,"should":[{"multi_match":{"query":query,"fields":["title^3","text"]}},{"semantic":{"field":"semantic_text","query":query}}],"minimum_should_match":1}}
    try:
        try:response=client.search(index=EVIDENCE_INDEX,query=hybrid,size=limit)
        except ApiError:response=client.search(index=EVIDENCE_INDEX,query=lexical,size=limit)
        return [ProductEvidence.model_validate({k:v for k,v in hit["_source"].items() if k!="semantic_text"} | {"semantic_text":hit["_source"].get("semantic_text","") if isinstance(hit["_source"].get("semantic_text",""),str) else ""}) for hit in response.get("hits",{}).get("hits",[])]
    except Exception as error:raise translate_elasticsearch_error(error) from error
