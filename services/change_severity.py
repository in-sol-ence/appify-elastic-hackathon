from models.change_events import ChangeSeverity
def evaluate_change_severity(event_type,urgency_score,magnitude=0,source_authority=.5,corroborating_sources=1,alternatives=0,delivery_margin=None):
 event_weight={'became_unavailable':40,'lifecycle_status_changed':35,'delivery_delayed':25,'price_increased':min(25,abs(magnitude)),'source_extraction_failed':10}.get(event_type,8)
 score=min(100,event_weight+urgency_score*.5+source_authority*10+(10 if corroborating_sources>1 else 0)-(min(20,alternatives*5)))
 if corroborating_sources==1 and source_authority<.5:score=min(score,59)
 severity='Critical' if score>=80 else 'High' if score>=60 else 'Medium' if score>=40 else 'Low'
 return ChangeSeverity(severity=severity,score=round(score,1),explanation=f"{event_type} evaluated with component urgency {urgency_score:.1f}, source authority {source_authority:.2f}, and {corroborating_sources} corroborating source(s).")
