from datetime import datetime,timezone,timedelta
from services.elasticsearch_client import CURRENT_LISTINGS_INDEX,OBSERVATIONS_INDEX,get_elasticsearch_client

def analyze_product_history(product_id,client=None):
 client=client or get_elasticsearch_client();now=datetime.now(timezone.utc)
 response=client.search(index=OBSERVATIONS_INDEX,size=2,query={'bool':{'filter':[{'term':{'product_id':product_id}},{'term':{'extraction.status':'success'}}]}},sort=[{'@timestamp':'desc'}],aggs={'seven_day':{'filter':{'range':{'@timestamp':{'gte':(now-timedelta(days=7)).isoformat()}}},'aggs':{'median':{'percentiles':{'field':'commercial.price','percents':[50]}}}},'thirty_day':{'filter':{'range':{'@timestamp':{'gte':(now-timedelta(days=30)).isoformat()}}},'aggs':{'stats':{'stats':{'field':'commercial.price'}},'median':{'percentiles':{'field':'commercial.price','percents':[50]}}}}})
 hits=response.get('hits',{}).get('hits',[]);prices=[h['_source'].get('commercial',{}).get('price') for h in hits]
 a=response.get('aggregations',{});thirty=a.get('thirty_day',{});stats=thirty.get('stats',{})
 current=prices[0] if prices else None;previous=prices[1] if len(prices)>1 else None
 deliveries=[h['_source'].get('commercial',{}).get('delivery_latest') for h in hits]
 delivery_trend='Unknown'
 if len(deliveries)>1 and deliveries[0] and deliveries[1]:delivery_trend='Delayed' if deliveries[0]>deliveries[1] else 'Improved' if deliveries[0]<deliveries[1] else 'Stable'
 return {'current_price':current,'previous_price':previous,'seven_day_median':a.get('seven_day',{}).get('median',{}).get('values',{}).get('50.0'),'thirty_day_median':thirty.get('median',{}).get('values',{}).get('50.0'),'thirty_day_low':stats.get('min'),'thirty_day_high':stats.get('max'),'price_change_percentage':((current-previous)/previous*100 if current is not None and previous else None),'delivery_trend':delivery_trend,'data_freshness':hits[0]['_source'].get('@timestamp') if hits else None}
def availability_summary(product_id,client=None):
 client=client or get_elasticsearch_client();response=client.search(index=CURRENT_LISTINGS_INDEX,size=100,query={'term':{'product_id':product_id}})
 sources={h['_source'].get('source_id'):h['_source'].get('commercial',{}).get('availability','unknown') for h in response.get('hits',{}).get('hits',[])}
 values=set(sources.values());return {'availability_by_source':sources,'active_sellers':sum(v in {'in_stock','limited_stock'} for v in sources.values()),'source_disagreement':len(values)>1,'data_freshness':max((h['_source'].get('@timestamp','') for h in response.get('hits',{}).get('hits',[])),default=None)}
def current_product_states(project_id,client=None):
 client=client or get_elasticsearch_client();response=client.search(index=CURRENT_LISTINGS_INDEX,size=100,query={'term':{'project_id':project_id}},sort=[{'@timestamp':'desc'}]);return [h['_source'] for h in response.get('hits',{}).get('hits',[])]
