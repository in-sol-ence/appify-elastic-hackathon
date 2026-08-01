from datetime import datetime,timezone,timedelta
from models.enums import RoleRequiredness
from models.monitoring import ComponentProcurementState
from models.project import Project
from models.urgency import ComponentUrgency
from services.graph_analysis import dependency_centrality

def deadline_pressure(days):
 if days is None:return 10
 if days<=0:return 100
 if days<=7:return 90
 if days<=14:return 65
 if days<=30:return 40
 if days<=60:return 20
 if days<=90:return 10
 return 5
def calculate_component_urgency(project:Project,component_role_id:str,current_state:ComponentProcurementState,now:datetime|None=None)->ComponentUrgency:
 now=now or datetime.now(timezone.utc);role=next((r for r in project.component_roles if r.id==component_role_id),None)
 if not role:raise ValueError('Component role does not exist.')
 if role.requiredness==RoleRequiredness.REMOVED:return ComponentUrgency(score=0,level='Minimal',explanation=['Component is removed.'])
 if role.requiredness==RoleRequiredness.CONDITIONAL and role.condition_active is False:return ComponentUrgency(score=5,level='Minimal',explanation=['Conditional component is inactive.'])
 days=(role.required_by-now.date()).days if role.required_by else None;pressure=deadline_pressure(days)
 ratings=[x.rating for x in project.role_milestone_ratings if x.component_role_id==role.id];criticality=max(ratings,default=0)*20
 centrality=dependency_centrality(project).get(role.id,0)*100
 proc_gap=0 if current_state.purchase_status in {'Received'} else 30 if current_state.purchase_status=='Ordered' else 100
 replacement=role.replacement_difficulty*20;integration=role.integration_risk*20;confidence=role.necessity_confidence
 factors={'Deadline pressure':pressure*0.30,'Milestone criticality':criticality*0.25,'Dependency centrality':centrality*0.15,'Procurement gap':proc_gap*0.10,'Replacement difficulty':replacement*0.10,'Integration risk':integration*0.05,'Necessity confidence':confidence*0.05}
 score=sum(factors.values());multiplier=1
 if role.requiredness==RoleRequiredness.OPTIONAL:multiplier=.25
 elif role.requiredness in {RoleRequiredness.EXPERIMENTAL,RoleRequiredness.DEFERRED}:multiplier=.4
 if current_state.purchase_status=='Received' and current_state.verification_status in {'Specification reviewed','Bench tested','Integrated'}:multiplier*=.25
 score=max(0,min(100,score*multiplier));buffer=current_state.integration_buffer_days if current_state.integration_buffer_days is not None else {1:2,2:4,3:7,4:14,5:21}[role.integration_risk]
 margin=None
 if role.required_by and current_state.expected_delivery_date:margin=(role.required_by-current_state.expected_delivery_date.date()).days-buffer
 level='Critical' if score>=80 else 'High' if score>=60 else 'Medium' if score>=40 else 'Low' if score>=20 else 'Minimal'
 explanation=[f"{days} days until required." if days is not None else 'Required-by date is unknown.',f"Criticality is {max(ratings,default=0)}/5.",f"Procurement status is {current_state.purchase_status}."]
 if margin is not None:explanation.append(f"Schedule margin is {margin} days." + (' Delivery is already at risk.' if margin<0 else ''))
 return ComponentUrgency(score=round(score,1),level=level,contributing_factors={k:round(v*multiplier,1) for k,v in factors.items()},days_until_required=days,schedule_margin_days=margin,explanation=explanation)
