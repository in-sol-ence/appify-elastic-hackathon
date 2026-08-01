from services.live_product_comparison import compare_live_products

def product(name,price,availability,delivery,compatibility='Compatible'):
 return {'name':name,'price_score':price,'availability':availability,'delivery_fit':delivery,'compatibility_status':compatibility,'documentation_available':True,'fresh':True,'source_confidence':1,'integration_risk':2}
def test_low_urgency_favors_cost_high_favors_availability():
 cheap=product('cheap',100,'backorder','Late');fast=product('fast',10,'in_stock','Safe')
 assert compare_live_products([cheap,fast],'Low')[0]['name']=='cheap'
 assert compare_live_products([cheap,fast],'High')[0]['name']=='fast'
def test_incompatible_never_first_and_unknown_delivery_reduces_score():
 incompatible=product('bad',100,'in_stock','Safe','Incompatible');safe=product('safe',20,'limited_stock','Safe')
 assert compare_live_products([incompatible,safe],'Critical')[0]['name']=='safe'
 unknown=product('unknown',20,'in_stock','Unknown');assert compare_live_products([safe,unknown],'High')[0]['name']=='safe'
