import asyncio,hashlib,json,os,re
from datetime import datetime,timezone
from urllib.parse import urlparse
import httpx
from apify import Actor
from bs4 import BeautifulSoup

def allowed(url,approved):
 parsed=urlparse(url);host=(parsed.hostname or '').lower()
 if parsed.scheme not in {'http','https'} or not host:return False
 return any(host==domain or host.endswith('.'+domain) for domain in approved)
def text_at(soup,selector):
 if not selector:return None
 node=soup.select_one(selector);return node.get_text(' ',strip=True) if node else None
def number(text):
 if not text:return None
 match=re.search(r'\d[\d,]*(?:\.\d+)?',text);return float(match.group().replace(',','')) if match else None
def availability(value):
 text=(value or '').lower()
 if any(x in text for x in ['discontinued','end of life']):return 'discontinued'
 if 'limited' in text or 'low stock' in text:return 'limited_stock'
 if 'backorder' in text:return 'backorder'
 if 'preorder' in text or 'pre-order' in text:return 'preorder'
 if any(x in text for x in ['out of stock','unavailable','sold out']):return 'out_of_stock'
 if any(x in text for x in ['in stock','available','ships']):return 'in_stock'
 return 'unknown'
def json_ld_product(soup):
 for node in soup.select('script[type="application/ld+json"]'):
  try:data=json.loads(node.string or '{}')
  except Exception:continue
  candidates=data if isinstance(data,list) else data.get('@graph',[]) if isinstance(data,dict) and '@graph' in data else [data]
  for item in candidates:
   if isinstance(item,dict) and (item.get('@type')=='Product' or item.get('@type')==['Product']):
    return item
 return {}
def parse_delivery(text):
 # Only explicit ISO dates are accepted; vague shipping text stays evidence-only.
 dates=re.findall(r'\b(20\d{2}-\d{2}-\d{2})\b',text or '')
 return (dates[0]+'T00:00:00Z' if dates else None,dates[-1]+'T23:59:59Z' if dates else None)
async def observe(source,base,run_id,approved,delay):
 url=source.get('url','');sid=source.get('source_id','')
 common={'schema_version':'1.0','monitoring_job_id':base.get('monitoring_job_id'),'project_id':base.get('project_id'),'component_role_id':base.get('component_role_id'),'product_id':base.get('product_id'),'source_id':sid,'actor_run_id':run_id,'observed_at':datetime.now(timezone.utc).isoformat(),'source_type':source.get('source_type','supplier_product_page'),'source_url':url,'supplier':source.get('supplier')}
 if not allowed(url,approved):return common|{'identity':{},'commercial':{'availability':'unknown'},'product_state':{},'evidence':{},'extraction':{'status':'failed','confidence':0,'warnings':[],'error_category':'unapproved_source','error_message':'Source domain is not approved.'}}
 try:
  await asyncio.sleep(max(0,delay)/1000)
  request_headers={'User-Agent':'Robotics-BOM-Guardian/1.0'}
  for key,value in source.get('request_headers',{}).items():
   if key.lower() not in {'host','authorization','cookie','proxy-authorization'}:request_headers[key]=str(value)
  async with httpx.AsyncClient(timeout=30,follow_redirects=False,headers=request_headers) as client:response=await client.get(url);response.raise_for_status()
  soup=BeautifulSoup(response.text,'html.parser');data=json_ld_product(soup) if source.get('extraction',{}).get('prefer_json_ld',True) else {};offers=data.get('offers') or {};offers=offers[0] if isinstance(offers,list) and offers else offers
  extraction=source.get('extraction',{});title=data.get('name') or text_at(soup,extraction.get('title_selector'));brand=data.get('brand') or {};manufacturer=brand.get('name') if isinstance(brand,dict) else brand
  mpn=data.get('mpn') or text_at(soup,extraction.get('part_number_selector'));price_text=str(offers.get('price') or '') or text_at(soup,extraction.get('price_selector'));availability_text=str(offers.get('availability') or '') or text_at(soup,extraction.get('availability_selector'));shipping=text_at(soup,extraction.get('shipping_selector'));earliest,latest=parse_delivery(shipping)
  identity={'title':title,'manufacturer':manufacturer,'model':data.get('model'),'manufacturer_part_number':mpn,'supplier_sku':data.get('sku')}
  return common|{'identity':identity,'commercial':{'price':number(price_text),'original_price':None,'currency':offers.get('priceCurrency') or source.get('currency'),'availability':availability(availability_text),'inventory_quantity':None,'delivery_text':shipping,'delivery_earliest':earliest,'delivery_latest':latest},'product_state':{'revision':None,'lifecycle_status':'active'},'evidence':{'content_hash':hashlib.sha256(response.content).hexdigest(),'price_text':price_text or None,'availability_text':availability_text or None,'shipping_text':shipping,'raw':{}},'extraction':{'status':'success','confidence':.9 if data else .65,'warnings':[] if data else ['JSON-LD Product was unavailable; configured selectors were used.']}}
 except Exception as error:return common|{'identity':{},'commercial':{'availability':'unknown'},'product_state':{},'evidence':{},'extraction':{'status':'failed','confidence':0,'warnings':[],'error_category':type(error).__name__,'error_message':str(error)[:500]}}
async def main():
 async with Actor:
  data=await Actor.get_input() or {};run_type=data.get('run_type','scheduled');env=Actor.get_env();run_id=getattr(env,'actor_run_id',None) or 'unknown'
  domains={d.strip().lower() for d in os.getenv('APPROVED_PRODUCT_DOMAINS','').split(',') if d.strip()}
  for item in data.get('approved_sources',[]):
   url=item.get('url') if isinstance(item,dict) else item;host=urlparse(url or '').hostname
   if host:domains.add(host.lower())
  sources=data.get('sources',[]) if run_type!='product_discovery' else data.get('approved_sources',[])
  for source in sources[:min(int(data.get('maximum_requests',10)),10)]:
   result=await observe(source,data,run_id,domains,int(data.get('request_delay_ms',1000)))
   if run_type=='product_discovery':
    result={'schema_version':'1.0','run_type':'product_discovery','project_id':data.get('project_id'),'component_role_id':data.get('component_role_id'),'candidate_identity':result.get('identity',{}),'candidate_supplier':result.get('supplier'),'candidate_commercial':result.get('commercial',{}),'candidate_specifications':{},'search_profile':data.get('search_profile',{}),'source_url':result.get('source_url'),'source_evidence':result.get('evidence',{}),'extraction':result.get('extraction',{}),'compatibility_status':'unevaluated'}
   await Actor.push_data(result)
if __name__=='__main__':asyncio.run(main())
