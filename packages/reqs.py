import json
import requests
from cloudscraper import create_scraper
from os.path import exists
import time

class endpoints_data:
    def __init__(self):
        self.file = './db/.endpoints-data'
    
    def get(self):
        if exists(self.file) == False:
            with open(self.file, 'w')as f:
                f.write('{}')
        with open(self.file, 'r') as f:
            o = json.load(f)
        return o
    
    def save(self, o):
        with open(self.file, 'w') as f:
            json.dump(o, f, indent=4)
        return o

def get_endpoints():
    e = endpoints_data()
    o = e.get()
        
    if time.time() - o.get('last-check', 0) > 60*60*24:
        p = {"operationName":"producer","variables":{"offset":0,"limit":80},"query":"query producer($offset: Int = 0, $limit: Int = 21, $where: producer_bool_exp) {\n  info: producer_aggregate(where: $where) {\n    producers: aggregate {\n      count\n      __typename\n    }\n    __typename\n  }\n  producers: producer(\n    where: $where\n    order_by: {total_votes_percent: desc}\n    offset: $offset\n    limit: $limit\n  ) {\n    id\n    owner\n    total_votes\n    bp_json\n    total_votes_percent\n    total_votes_eos\n    total_rewards\n    health_status\n    endpoints\n    rank\n    updated_at\n    __typename\n  }\n}\n"}
        data = requests.post('https://graphql-wax.eosio.online/v1/graphql', json=p).json()
        o['endpoints'] = []
        for x in data['data']['producers']:
            if x['endpoints']['ssl']:
                o['endpoints'] += x['endpoints']['ssl']
        o['endpoints'].append('https://wax.pink.gg')
        
        o['last-check'] = int(time.time())
        e.save(o)
        
    return o['endpoints']

class req_api:
    def __init__(self):
        self.session = requests.Session()
    
    def req(self, url: str, method: str, format: str='json', **kwargs):
        try:
            r = eval(f'self.session.{method.lower()}(url, timeout=2, **kwargs)')
            if format == 'json': 
                r = r.json()
                if r.get('error') != None or r.get('success', True) == False:
                    return {'error': True, 'data': None, 'message': r.get('message')}
            
            elif format == 'text': r = r.text
            
            return {'error': None, 'data': r}
        except Exception as e:
            return {'error': True, 'data': None, 'message': e}

    def node_req(self, query: str, **kwargs):
        e = endpoints_data()
        allnodes = get_endpoints()
        for n in allnodes:
            print(n + query)
            r = self.req(n + query, **kwargs)
            print(r)
            if r.get('error'):
                o = e.get()
                if o.get('errors') == None:
                    o['errors'] = {}
                
                #if time.time() - o['errors'].get(n, 0) > 
                pass
            
            elif r['data'].get('error'):
                pass 
            
            else:
                return {
                    'error': None, 
                    'data': r['data'], 
                    'query': query
                }
        else:
            return {
                'error': True, 
                'data': None, 
                'message': f'Can\'t get response for {len(allnodes)} urls', 
                'query': query
            }
        

if __name__ == '__main__':

    reqs = req_api()
    u = reqs.node_req('/v2/state/get_tokens?account=abuztradewax', method='GET', format='json')
    print(u)