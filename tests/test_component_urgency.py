from datetime import date,datetime,timezone,timedelta
from models.enums import RoleRequiredness
from models.monitoring import ComponentProcurementState
from services.component_urgency import calculate_component_urgency
from services.templates import build_sample_project

def urgency(days,requiredness=RoleRequiredness.MANDATORY,state=None):
 p=build_sample_project();r=p.component_roles[0];r.required_by=date.today()+timedelta(days=days);r.requiredness=requiredness;return calculate_component_urgency(p,r.id,state or ComponentProcurementState(),datetime.now(timezone.utc))
def test_mandatory_due_tomorrow_more_urgent_than_ninety_days():assert urgency(1).score>urgency(90).score
def test_optional_and_inactive_conditional_are_low():
 assert urgency(60,RoleRequiredness.OPTIONAL).level in {'Minimal','Low'}
 p=build_sample_project();r=p.component_roles[0];r.requiredness=RoleRequiredness.CONDITIONAL;r.condition_description='if needed';r.condition_active=False
 assert calculate_component_urgency(p,r.id,ComponentProcurementState()).score==5
def test_received_verified_reduces_urgency():
 state=ComponentProcurementState(purchase_status='Received',verification_status='Bench tested');assert urgency(1,state=state).score<urgency(1).score
def test_negative_schedule_margin_and_missing_date():
 p=build_sample_project();r=p.component_roles[0];r.required_by=date.today()+timedelta(days=5);state=ComponentProcurementState(expected_delivery_date=datetime.now(timezone.utc)+timedelta(days=10))
 assert calculate_component_urgency(p,r.id,state).schedule_margin_days<0
 r.required_by=None;assert calculate_component_urgency(p,r.id,state).days_until_required is None
