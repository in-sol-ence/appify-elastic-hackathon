from datetime import datetime, timezone

from models.enums import PurchaseStatus, SelectionStatus, VerificationStatus
from models.products import Product
from models.project import ProductSelection, Project
from services.readiness import evaluate_project_readiness


def apply_catalog_product(project:Project,component_role_id:str,product:Product,primary:bool=True,status:SelectionStatus=SelectionStatus.SELECTED)->tuple[ProductSelection,object]:
    if not any(r.id==component_role_id for r in project.component_roles):raise ValueError("Component role does not exist.")
    existing=next((p for p in project.products if p.component_role_id==component_role_id and p.elastic_product_id==product.product_id),None)
    if primary:
        for item in project.products:
            if item.component_role_id==component_role_id:item.primary_product=False
    payload=dict(component_role_id=component_role_id,manufacturer=product.manufacturer,product_name=product.name,model=product.model,manufacturer_part_number=product.manufacturer_part_number,quantity=1,expected_unit_price=product.price_estimate or 0,manufacturer_url=product.source_url,selection_status=status,purchase_status=PurchaseStatus.NOT_PLANNED,verification_status=VerificationStatus.UNVERIFIED,primary_product=primary,elastic_product_id=product.product_id,catalog_specs=product.model_dump(mode="json",exclude={"description","product_summary","created_at","updated_at"}))
    if existing:
        for key,value in payload.items():setattr(existing,key,value)
        selection=existing
    else:
        selection=ProductSelection(**payload);project.products.append(selection)
    return selection,evaluate_project_readiness(project)


def reject_catalog_product(project:Project,component_role_id:str,product:Product,reason:str)->ProductSelection:
    selection,_=apply_catalog_product(project,component_role_id,product,False,SelectionStatus.REJECTED)
    selection.rejection_reason=reason;selection.rejected_at=datetime.now(timezone.utc);return selection
