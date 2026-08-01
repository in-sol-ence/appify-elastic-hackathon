from models.compatibility import CompatibilityEvaluation
from models.products import Product
from models.search import ComponentSearchProfile,ProductSearchResult
from services.product_ranking import rank_results,score_product


def profile():return ComponentSearchProfile(project_id="p",component_role_id="r",role_name="Role",category="motor_driver",purpose="",required_quantity=1,necessity_confidence=100,project_budget=100,component_budget=50,natural_language_description="driver")
def test_compatible_out_ranks_incompatible_and_budget_affects_score():
 p=profile();cheap=Product(product_id="a",manufacturer="D",name="A",category="motor_driver",price_estimate=40,documentation_available=True);expensive=Product(product_id="b",manufacturer="D",name="B",category="motor_driver",price_estimate=100)
 good=CompatibilityEvaluation(status="Compatible");bad=CompatibilityEvaluation(status="Incompatible",failed_requirements=["voltage"])
 gs,gb=score_product(p,cheap,good,1);bs,bb=score_product(p,expensive,bad,100)
 results=[ProductSearchResult(product=expensive,compatibility_status="Incompatible",project_fit_score=bs),ProductSearchResult(product=cheap,compatibility_status="Compatible",project_fit_score=gs)]
 assert rank_results(results)[0].product.product_id=="a";assert gb["Budget fit"]>bb["Budget fit"];assert bs<=39
