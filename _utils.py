import re
import time
from datetime import datetime
from bs4 import BeautifulSoup as bs
from load_data import to_dict, loadInJSON

class _utils:
    def __init__(self, 
                 settings, 
                 base, 
                 _log, 
                 log,
                 scraper,
                 URL,
                 Payload):
        
        self.settings = settings
        self.base = base
        self._log = _log
        self.log = log
        self.scraper = scraper
        self.URL = URL
        self.Payload = Payload
        

    def is_nft_dropped(self, account):
        url = "https://wax.greymass.com/v1/chain/get_table_rows"
        _json = {
            "json":True,
            "code":"m.federation",
            "scope":"m.federation",
            "table":"claims",
            "table_key":"",
            "lower_bound": account,
            "upper_bound":None,
            "index_position":1,
            "key_type":"",
            "limit":"100",
            "reverse":False,
            "show_payer":False
        }
        res = self.scraper.post(url, json=_json)
        if res.status_code != 200:
            return {'success': False, 'res': res}
        else:
            decoded = res.json()
            drop = decoded['rows'][0]['template_ids'] if decoded['rows'][0]['miner'] == account else None
            if drop:
                return {'success': True, 'isdrop': True, 'items': drop}
            return {'success': True, 'isdrop': False, 'items': []}
            

    def get_user_ids(self):
        ids = [int(x.strip()) for x in self.settings['user_id'].split(',') if x.strip() != '' and x.strip().isdigit()]
        if not ids:
            self._log.error('UserIdError: invalid user_id. User_id must be a digit (write to @get_user_id_bot)')
        return ids

    def fetch_asset(self, asset_id: str):
        inbase = self.base.get_by("assets", get_by=['asset_id', asset_id], args='all')
        if inbase:
            return {
                'success': True,
                'asset_id': inbase[0]['asset_id'],
                'name': inbase[0]['name'],
                'rarity': inbase[0]['rarity'], 
                'contract': inbase[0]['contract'],
                'collection_name': inbase[0]['collection_name'],
                'template_id': inbase[0]['template_id']
            }
        else:
            info = None
            for _ in range(3):
                try:
                    asset_response = self.scraper.get(f"{self.URL.ASSETS}{asset_id}", headers=self.Payload.ass_headers).json()
                    break
                except:
                    time.sleep(1)
                    continue
            else:
                info = {
                    'success': False
                }
                
            if not info:
                info = self.get_asset_info(asset_response)
                if info['success']:
                    self.base.add(
                        table='assets',
                        asset_id=asset_id,
                        name=info['name'],
                        rarity=info['rarity'], 
                        contract=info['contract'],
                        collection_name=info['collection_name'],
                        template_id=info['template_id']
                    )
            
            return info

    def get_assets(self, nft_response):
        res = {}
        for ass in nft_response['data']:
            asset_id = ass['asset_id']
            contract = ass.get('contract')
            collection = ass.get('collection')
            collection_name = collection.get('name') if collection else None
            item_name = ass.get('name')
            
            rarity = ass.get('data').get('rarity') if collection_name == 'Alien Worlds' else None
            template = ass.get('template')
            if template:
                template = template['template_id'] if template.get('template_id') else None
            
            info = {
                'contract': contract,
                'collection_name': collection_name,
                'template_id': template,
                'name': item_name,
                'rarity': rarity
            }
            res[asset_id] = info

            if not self.base.get_by("assets", get_by=['asset_id', asset_id], args='all'):
                self.base.add(
                    table='assets',
                    asset_id=asset_id,
                    name=info['name'],
                    rarity=info['rarity'], 
                    contract=info['contract'],
                    collection_name=info['collection_name'],
                    template_id=info['template_id']
                )
            
        return res

    def get_token_price(self, url):
        response = self.scraper.get(url)
        response_json = response.json()
        return float(response_json['price']['USD']), float(response_json['price']['RUB'])

    def get_price(self, template: str) -> float:
        params = self.Payload.get_price_params.copy()
        params['template_id'] = template
        while True:
            try:
                response = self.scraper.get(self.URL.GET_PRICE, params=params).json()
                break
            except:
                self.log("Error with get item price...")
                time.sleep(5)
            
        if response.get('data'):
            return round(int(response['data'][0]["listing_price"]) / 100000000, 2)
        else:
            self.log(response)
            return 0

    def get_asset_info(self, asset_response):
        if asset_response['success']:
            asset_info = asset_response.get('data')
            if asset_info:
                contract = asset_info.get('contract')
                collection = asset_info.get('collection')
                collection_name = collection.get('name') if collection else None
                item_name = asset_info.get('name')
                
                rarity = asset_info.get('data').get('rarity') if collection_name == 'Alien Worlds' else None
                template = asset_info.get('template')
                if template:
                    template = template['template_id'] if template.get('template_id') != None else None
                
                return {
                    'success': True,
                    'contract': contract,
                    'collection_name': collection_name,
                    'template_id': template,
                    'name': item_name,
                    'rarity': rarity
                }
            else:
                return {'success': False, 'response': asset_response}
        else:
            return {'success': False, 'response': asset_response}

    def get_resourses(self, name: str) -> dict:
        response = self.scraper.get(self.URL.RESOURSES, json={"account_name": name})
        try:
            response = response.json()
            cpu = round(response['cpu_limit']['used'] / response['cpu_limit']['max'] * 100, 2)
            net = round(response['net_limit']['used'] / response['net_limit']['max'] * 100, 2)
            ram = round(response['ram_usage'] / response['ram_quota'] * 100, 2)
            
            if response.get("self_delegated_bandwidth"):
                cpu_staked = round(float(response['self_delegated_bandwidth']['cpu_weight'][:-4]), 2)
            else:
                cpu_staked = 0
                
            return {
                'cpu': cpu,
                'net': net,
                'ram': ram,
                'cpu_staked': cpu_staked
            }
        except Exception as e:
            self.log(f'Error getting account resources: {name} ({e})')
            return {
                'cpu': 0,
                'net': 0,
                'ram': 0,
                'cpu_staked': None
            }
            
    def get_notification_text(self, name: str, _type: str, body: str):
        return f"<b>Account:</b> <code>{name}</code>\n"\
            f"<b>Event type: {_type}</b>\n"\
            f"<i>{body}</i>\n"\
            f"<b>Link: {self.URL.WAX}{name}</b>\n"\
            f"<b>Atomic: {self.URL.ATOMIC}{name}</b>"

    def get_links(self, name: str) -> tuple:
        return (
            self.URL.TOKENS.replace('{account}', name),
            self.URL.NFTS.replace('{account}', name)
        )

    def get_accounts(self):
        accounts_dumb = self.base.get_table('accounts')
        accounts_dumb = [
            {
                x['name']: {
                    'assets': to_dict(x['assets']), 
                    'tokens': to_dict(x['tokens'])
                }
            for x in accounts_dumb
            }
        ]
        if accounts_dumb:
            return accounts_dumb[0]
        else:
            return accounts_dumb

    def split_text(t, limit=4048):
        if len(t) > limit:
            text = t.split('\n')
            _text = ""
            _cc = 0
            for i in text:
                if (_cc + len(i) + 2 < limit):
                    _cc += len(i) + 2
                    _text += i + '\n'
                else:
                    yield _text
                    _text = i + '\n'
                    _cc = len(_text)
            else:
                yield _text

    def get_timer(self):
        data = loadInJSON().get('timer.json')
        if not data:
            data = {
                'start_timestamp': 0,
                'balances': {},
                'nfts': []
            }
        loadInJSON().save('timer.json', data)
        return data

    def create_timer(self):
        timer = self.get_timer()
        timer['start_timestamp'] = int(time.time())
        timer['balances'] = {}
        loadInJSON().save('timer.json', timer)
        return timer
    
    def update_timer(self, currency, value):
        timer = self.get_timer()
        if timer['balances'].get(currency):
            timer['balances'][currency] += value
        else:
            timer['balances'][currency] = value
            
        loadInJSON().save('timer.json', timer)
        return timer
    
    def zero_timer(self):
        loadInJSON().save('timer.json', {})

    def show_time(self, time):
        time = int(time)
        day = time // (24 * 3600)
        time = time % (24 * 3600)
        hour = time // 3600
        time %= 3600
        minutes = time // 60
        time %= 60
        seconds = time
        if day != 0:
            return "%d days %d hours %d mins %d secounds" % (day, hour, minutes, seconds)
        elif day == 0 and hour != 0:
            return "%d hours %d mins %d secounds" % (hour, minutes, seconds)
        elif day == 0 and hour == 0 and minutes != 0:
            return "%d mins %d secounds" % (minutes, seconds)
        else:
            return "%d secounds" % (seconds)
        
    def timer_to_date(self):
        timer = self.get_timer()
        strdate = datetime.fromtimestamp(timer['start_timestamp'])
        time_between = int(time.time() - timer['start_timestamp'])
        strbetween = self.show_time(time_between)
        return {
            'timer': timer,
            'strdate': strdate,
            'time_between': time_between,
            'strbetween': strbetween
        }
        
        
        
        