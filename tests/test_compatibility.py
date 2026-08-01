from models.products import Product
from models.search import CompatibilityRequirement,ComponentSearchProfile
from services.compatibility import evaluate_product_compatibility


def profile(*requirements):
 return ComponentSearchProfile(project_id="p",component_role_id="r",role_name="Driver",category="motor_driver",purpose="drive",required_quantity=1,necessity_confidence=100,project_budget=1000,hard_requirements=list(requirements),natural_language_description="motor driver")
def product(**values):return Product(product_id="x",manufacturer="Dev",name="Driver",category="motor_driver",**values)

def test_voltage_current_and_interface_pass():
 p=profile(CompatibilityRequirement(field="required_voltage_v",operator="range_includes",value=24,description="24 V"),CompatibilityRequirement(field="continuous_current_per_channel_a",operator="gte",value=15,description="15 A"),CompatibilityRequirement(field="control_interfaces",operator="contains_any",value=["PWM","UART"],description="PWM or UART"))
 e=evaluate_product_compatibility(p,product(input_voltage_min_v=12,input_voltage_max_v=30,continuous_current_per_channel_a=20,control_interfaces=["PWM"]));assert e.status=="Compatible"

def test_fail_and_unknown_classifications():
 p=profile(CompatibilityRequirement(field="required_voltage_v",operator="range_includes",value=24,description="24 V"),CompatibilityRequirement(field="channel_count",operator="gte",value=2,description="2 channels"))
 assert evaluate_product_compatibility(p,product(input_voltage_min_v=5,input_voltage_max_v=12,channel_count=2)).status=="Incompatible"
 assert evaluate_product_compatibility(p,product()).status=="Insufficient information"

def test_one_missing_field_is_potentially_compatible():
 p=profile(CompatibilityRequirement(field="category",operator="eq",value="motor_driver",description="category"),CompatibilityRequirement(field="channel_count",operator="gte",value=2,description="channels"),CompatibilityRequirement(field="control_interfaces",operator="contains_any",value=["PWM"],description="PWM"))
 e=evaluate_product_compatibility(p,product(channel_count=2));assert e.status=="Potentially compatible" and "PWM" in e.unknown_requirements
