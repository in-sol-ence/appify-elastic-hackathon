import os
from uuid import uuid4

from elasticsearch import ApiError
from elasticsearch.helpers import bulk

from models.compatibility import ProductEvaluation
from models.products import Product
from models.search import ComponentSearchProfile, ProductSearchResult
from services.compatibility import evaluate_product_compatibility
from services.elasticsearch_client import EVALUATIONS_INDEX, PRODUCTS_INDEX, get_elasticsearch_client, translate_elasticsearch_error
from services.product_ranking import rank_results, score_product


def hard_filters(profile:ComponentSearchProfile)->list[dict]:
    filters=[]
    for req in profile.hard_requirements:
        if req.field=="required_voltage_v":
            filters.extend([{"range":{"input_voltage_min_v":{"lte":req.value}}},{"range":{"input_voltage_max_v":{"gte":req.value}}}])
        elif req.operator=="eq":filters.append({"term":{req.field:req.value}})
        elif req.operator=="gte":filters.append({"range":{req.field:{"gte":req.value}}})
        elif req.operator=="lte":filters.append({"range":{req.field:{"lte":req.value}}})
        elif req.operator=="contains_any":filters.append({"terms":{req.field:req.value}})
        elif req.operator=="exists":filters.append({"exists":{"field":req.field}})
    return filters


def build_product_query(profile:ComponentSearchProfile,semantic:bool=True)->dict:
    should=[{"multi_match":{"query":profile.natural_language_description,"fields":["name^4","manufacturer^2","model^3","manufacturer_part_number^5","product_summary^3","description","intended_applications","important_features"],"type":"best_fields"}}]
    if semantic:should.append({"semantic":{"field":"semantic_text","query":profile.natural_language_description}})
    return {"bool":{"filter":hard_filters(profile),"should":should,"minimum_should_match":1}}


def _results(profile,hits,fallback=False):
    results=[]
    for hit in hits:
        source=dict(hit["_source"]);source.pop("semantic_text",None)
        product=Product.model_validate(source);evaluation=evaluate_product_compatibility(profile,product);search_score=float(hit.get("_score") or 0)
        fit,breakdown=score_product(profile,product,evaluation,search_score)
        results.append(ProductSearchResult(product=product,search_score=search_score,project_fit_score=fit,compatibility_status=evaluation.status,matched_requirements=evaluation.passed_requirements,missing_fields=evaluation.unknown_requirements,search_explanation="Keyword search used because semantic search was unavailable." if fallback else "Hybrid lexical and semantic ranking with structured hard filters.",score_explanation=breakdown))
    return rank_results(results)


def search_products(profile:ComponentSearchProfile,limit:int=20,client=None)->list[ProductSearchResult]:
    client=client or get_elasticsearch_client();fallback=False
    try:
        try: response=client.search(index=PRODUCTS_INDEX,query=build_product_query(profile,True),size=limit)
        except ApiError: fallback=True;response=client.search(index=PRODUCTS_INDEX,query=build_product_query(profile,False),size=limit)
        results=_results(profile,response.get("hits",{}).get("hits",[]),fallback)
        if results and os.getenv("ES_ALLOW_WRITES")=="1":_store_evaluations(profile,results,client)
        return results
    except Exception as error:
        from services.elasticsearch_client import ProductSearchError
        if isinstance(error,ProductSearchError):raise
        raise translate_elasticsearch_error(error) from error


def find_similar_products(product_id:str,profile:ComponentSearchProfile|None=None,limit:int=10,client=None)->list[ProductSearchResult]:
    client=client or get_elasticsearch_client()
    try:
        filters=hard_filters(profile) if profile else []
        source=client.get(index=PRODUCTS_INDEX,id=product_id).get("_source",{})
        semantic_text=". ".join(str(source.get(field,"")) for field in ["name","category","product_summary","intended_applications","important_features"] if source.get(field))
        semantic_query={"bool":{"must":[{"semantic":{"field":"semantic_text","query":semantic_text}}],"filter":filters,"must_not":[{"term":{"product_id":product_id}}]}}
        lexical_query={"bool":{"must":[{"more_like_this":{"fields":["name","product_summary","description","intended_applications"],"like":[{"_index":PRODUCTS_INDEX,"_id":product_id}],"min_term_freq":1,"min_doc_freq":1}}],"filter":filters,"must_not":[{"term":{"product_id":product_id}}]}}
        try:response=client.search(index=PRODUCTS_INDEX,query=semantic_query,size=limit)
        except ApiError:response=client.search(index=PRODUCTS_INDEX,query=lexical_query,size=limit)
        if profile:return _results(profile,response.get("hits",{}).get("hits",[]))
        return [ProductSearchResult(product=Product.model_validate({k:v for k,v in hit["_source"].items() if k!="semantic_text"}),search_score=hit.get("_score") or 0,search_explanation="Similar catalog content; compatibility not established.") for hit in response.get("hits",{}).get("hits",[])]
    except Exception as error:raise translate_elasticsearch_error(error) from error


def _store_evaluations(profile,results,client):
    actions=[]
    for result in results:
        evaluation=evaluate_product_compatibility(profile,result.product)
        record=ProductEvaluation(evaluation_id=str(uuid4()),project_id=profile.project_id,component_role_id=profile.component_role_id,product_id=result.product.product_id,compatibility_status=evaluation.status,hard_requirements_passed=evaluation.passed_requirements,hard_requirements_failed=evaluation.failed_requirements,unknown_requirements=evaluation.unknown_requirements,search_score=result.search_score,project_fit_score=result.project_fit_score,failure_reasons=evaluation.failed_requirements,warnings=evaluation.warnings)
        actions.append({"_index":EVALUATIONS_INDEX,"_id":record.evaluation_id,"_source":record.model_dump(mode="json")})
    bulk(client,actions,raise_on_error=False)
