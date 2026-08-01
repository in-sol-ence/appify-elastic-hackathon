from models.compatibility import CompatibilityEvaluation
from models.products import Product
from models.search import ComponentSearchProfile, ProductSearchResult

ORDER={"Compatible":0,"Potentially compatible":1,"Insufficient information":2,"Incompatible":3}


def score_product(profile:ComponentSearchProfile,product:Product,evaluation:CompatibilityEvaluation,search_score:float)->tuple[float,dict[str,float]]:
    total_req=max(1,len(profile.hard_requirements)); technical=40*len(evaluation.passed_requirements)/total_req
    relevance=min(15,max(0,search_score)*3)
    interface=10 if any("interface" in x.lower() or "supports" in x.lower() for x in evaluation.passed_requirements) else 0
    software=10 if product.supported_operating_systems or product.supported_software else 0
    documentation=10 if product.documentation_available else 0
    budget=10 if profile.component_budget and product.price_estimate is not None and product.price_estimate<=profile.component_budget else (5 if product.price_estimate is not None else 0)
    confidence=5*product.specification_confidence
    breakdown={"Technical compatibility":technical,"Search relevance":relevance,"Interface fit":interface,"Software support":software,"Documentation":documentation,"Budget fit":budget,"Specification confidence":confidence}
    score=min(100,sum(breakdown.values()))
    if evaluation.status=="Incompatible":score=min(score,39)
    return round(score,1),{k:round(v,1) for k,v in breakdown.items()}


def rank_results(results:list[ProductSearchResult])->list[ProductSearchResult]:
    return sorted(results,key=lambda r:(ORDER.get(r.compatibility_status,9),-r.project_fit_score))
