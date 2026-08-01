from services.elasticsearch_client import CHANGE_EVENTS_INDEX,get_elasticsearch_client,require_write_access
def acknowledge_change(event_id,client=None):
 require_write_access();client=client or get_elasticsearch_client();client.update(index=CHANGE_EVENTS_INDEX,id=event_id,doc={'acknowledgment_status':'acknowledged'})
def recent_changes(project_id,role_id=None,limit=50,client=None):
 client=client or get_elasticsearch_client();filters=[{'term':{'project_id':project_id}}]
 if role_id:filters.append({'term':{'component_role_id':role_id}})
 response=client.search(index=CHANGE_EVENTS_INDEX,size=limit,query={'bool':{'filter':filters}},sort=[{'observed_at':'desc'}]);return [h['_source'] for h in response.get('hits',{}).get('hits',[])]
