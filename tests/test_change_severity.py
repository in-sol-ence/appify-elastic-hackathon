from services.change_severity import evaluate_change_severity
def test_optional_low_context_stays_low_and_urgent_unavailability_is_high():
 low=evaluate_change_severity('price_increased',10,8,.9,1,3);high=evaluate_change_severity('became_unavailable',95,0,.9,2,0)
 assert low.severity=='Low' and high.severity in {'High','Critical'}
def test_low_confidence_single_source_cannot_be_critical():assert evaluate_change_severity('became_unavailable',100,0,.2,1,0).severity!='Critical'
