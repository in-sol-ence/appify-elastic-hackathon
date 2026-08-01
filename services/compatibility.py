from models.compatibility import CompatibilityEvaluation
from models.products import Product
from models.search import ComponentSearchProfile


def _check(requirement, product):
    field=requirement.field
    if field=="required_voltage_v":
        low,high=product.input_voltage_min_v,product.input_voltage_max_v
        if low is None or high is None:return None
        return low<=float(requirement.value)<=high
    value=getattr(product,field,None)
    if value is None or value==[]: return None
    if requirement.operator=="eq": return str(value).lower()==str(requirement.value).lower()
    if requirement.operator=="gte": return float(value)>=float(requirement.value)
    if requirement.operator=="lte": return float(value)<=float(requirement.value)
    if requirement.operator=="contains_any":
        actual={str(x).lower() for x in (value if isinstance(value,list) else [value])}
        requested=[str(x).lower() for x in requirement.value]
        return any(any(req in item or item in req for item in actual) for req in requested)
    if requirement.operator=="exists": return value is not None
    return None


def evaluate_product_compatibility(profile: ComponentSearchProfile,product: Product)->CompatibilityEvaluation:
    passed=[];failed=[];unknown=[]
    for requirement in profile.hard_requirements:
        result=_check(requirement,product)
        (passed if result is True else failed if result is False else unknown).append(requirement.description)
    if failed: status="Incompatible"
    elif unknown and len(unknown)>=max(2,len(profile.hard_requirements)//2): status="Insufficient information"
    elif unknown: status="Potentially compatible"
    else: status="Compatible"
    warnings=[]
    if product.specification_confidence<0.6:warnings.append("Specification confidence is low.")
    return CompatibilityEvaluation(status=status,passed_requirements=passed,failed_requirements=failed,unknown_requirements=unknown,warnings=warnings)
