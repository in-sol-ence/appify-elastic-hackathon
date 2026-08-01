import re

from models.project import Project
from models.search import CompatibilityRequirement, ComponentSearchProfile

CATEGORY_ALIASES={"motor driver":"motor_driver","computer":"onboard_computer","compute":"onboard_computer","lidar":"lidar","obstacle":"lidar","ranging":"lidar"}
NUMERIC_FIELDS={"voltage":"required_voltage_v","continuous_current":"continuous_current_per_channel_a","peak_current":"peak_current_per_channel_a","channels":"channel_count","max_price":"price_estimate"}


def _number(value: str):
    match=re.search(r"-?\d+(?:\.\d+)?",value or "")
    return float(match.group()) if match else None


def build_component_search_profile(project: Project, component_role_id: str) -> ComponentSearchProfile:
    role=next((r for r in project.component_roles if r.id==component_role_id),None)
    if not role: raise ValueError("Component role does not exist.")
    text=f"{role.role_name} {role.category}".lower(); category=next((value for key,value in CATEGORY_ALIASES.items() if key in text),role.category.lower().replace(" ","_"))
    hard=[CompatibilityRequirement(field="category",operator="eq",value=category,description=f"Category is {category}")]
    preferred=[]
    reqs=role.acceptance_requirements
    voltage=_number(reqs.get("voltage",""))
    if voltage is not None: hard.append(CompatibilityRequirement(field="required_voltage_v",operator="range_includes",value=voltage,description=f"Voltage range includes {voltage:g} V"))
    current=_number(reqs.get("current",""))
    if current is not None: hard.append(CompatibilityRequirement(field="continuous_current_per_channel_a",operator="gte",value=current,description=f"Continuous current per channel is at least {current:g} A"))
    interface_text=" ".join([reqs.get("interface",""),role.functional_acceptance_criteria]).upper()
    interfaces=[item for item in ["PWM","UART","I2C","SPI","USB","CAN","ETHERNET"] if item in interface_text]
    if interfaces: hard.append(CompatibilityRequirement(field="control_interfaces",operator="contains_any",value=interfaces,description=f"Supports {' or '.join(interfaces)}"))
    for label,field in [("peak", "peak_current_per_channel_a"),("channel","channel_count")]:
        match=re.search(rf"(?:{label})[^0-9]*(\d+(?:\.\d+)?)",role.functional_acceptance_criteria.lower())
        if match: hard.append(CompatibilityRequirement(field=field,operator="gte",value=float(match.group(1)),description=f"{field.replace('_',' ')} at least {match.group(1)}"))
    if project.software_platform: preferred.append(CompatibilityRequirement(field="supported_operating_systems",operator="contains_any",value=[project.software_platform],hard=False,description=f"Supports {project.software_platform}"))
    component_budget=project.total_budget/max(1,len(project.component_roles)) if project.total_budget else None
    if component_budget: preferred.append(CompatibilityRequirement(field="price_estimate",operator="lte",value=component_budget,hard=False,description=f"Estimated price under ${component_budget:.0f}"))
    connections=[]; names=project.entity_names()
    for rel in project.relationships:
        if rel.source_id==role.id: connections.append(names.get(rel.target_id,"Unknown"))
        elif rel.target_id==role.id: connections.append(names.get(rel.source_id,"Unknown"))
    milestone=names.get(role.first_required_milestone_id) if role.first_required_milestone_id else None
    ratings=[r.rating for r in project.role_milestone_ratings if r.component_role_id==role.id]
    natural=f"Find a {role.role_name.lower()} for {role.purpose.lower() or 'this robotics project'}. " + "; ".join(r.description for r in hard[1:])
    return ComponentSearchProfile(project_id=project.id,component_role_id=role.id,role_name=role.role_name,category=category,purpose=role.purpose,required_quantity=role.required_quantity,required_milestone=milestone,required_by_date=role.required_by,criticality=max(ratings,default=0),necessity_confidence=role.necessity_confidence,project_budget=project.total_budget,component_budget=component_budget,hard_requirements=hard,preferred_requirements=preferred,connected_components=sorted(set(connections)),software_platform=project.software_platform,operating_environment=project.operating_environment.value,natural_language_description=natural.strip())
