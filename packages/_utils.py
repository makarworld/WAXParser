import time
from datetime import datetime
import os
from copy import deepcopy

from .load_data import loadInStrings, to_dict, loadInJSON

def timer_decorator(func):
    def wrapped(*args, **kwargs):
        if not os.path.exists('./db/timer.json'):
            with open('./db/timer.json', 'w') as f: f.write('{}')
        try:
            data = loadInJSON().get('./db/timer.json')
        except Exception as e:
            print('./db/timer.json error: %s' % e)
            with open('./db/timer.json', 'w') as f: f.write('{}')
            
        return func(*args, **kwargs)

    return wrapped


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
        

    def get_name_by_template(self, template: str):
        try:
            res = self.scraper.get(self.URL.TEMPLATE_INFO.format(template)).json()
            return res['data'][0]['name']
        except:
            return f"Undefined NFT card (template#{template})"

    def get_tokens(self, scraper, account, last_data):
        link = self.URL.TOKENS.format(account)
        for _ in range(3):
            try:
                tokens_response = scraper.get(link, timeout=10)
                if tokens_response.status_code == 200:
                    tokens_response = tokens_response.json()['tokens']
                    return '', [{x['symbol']: x['amount'] for x in tokens_response}][0]
                else: 
                    raise Exception(f"url: {link} | status_code: {tokens_response.status_code}")
                
            except Exception as e:
                #self._log.exception('TOKENS:')
                #self.log("Fail to fetch tokens")
                time.sleep(3)
                continue
        else:
            return f"[{account}] Fail to fetch tokens", last_data
        
    
    def get_nfts(self, scraper, account, last_data):
        link = self.URL.NFTS.format(account)
        for _ in range(3):
            try:
                nfts_response = scraper.get(link, timeout=10)
                if nfts_response.status_code == 200:
                    nfts_response = nfts_response.json()
                    return '', list(self.get_assets(nfts_response).keys())
                else: 
                    raise Exception(f"url: {link} | status_code: {nfts_response.status_code}")
                
            except Exception as e:
                #self._log.exception('NFTS:')
                time.sleep(3)
                continue
        else:
            return f"[{account}] Fail to fetch NFT", last_data

    def is_time_to_notif(self, limits_notifications: dict, item: str, account: str, timeout: int):
        if limits_notifications[item].get(account):
            if time.time() - limits_notifications[item][account] >= int(timeout):
                # timeout done! 
                limits_notifications[item][account] = int(time.time())
                return limits_notifications, True
        else:
            limits_notifications[item][account] = int(time.time())
            return limits_notifications, True
        return limits_notifications, False

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
        try:
            res = self.scraper.post(url, json=_json)
            if res.status_code != 200:
                return {'success': False, 'res': res}
            else:
                decoded = res.json()
                drop = decoded['rows'][0]['template_ids'] if decoded['rows'][0]['miner'] == account else None
                if drop:
                    return {'success': True, 'isdrop': True, 'items': drop}
                return {'success': True, 'isdrop': False, 'items': []}
        except:
            return {'success': False, 'isdrop': False, 'items': []}
            

    def get_user_ids(self):
        ids = [int(x.strip()) for x in self.settings['user_id'].split(',') if x.strip() != '' and x.replace('-', '').strip().isdigit()]
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

    def get_price(self, template: str, name: str) -> float:
        baseinfo = self.base.get_by('prices', ['template_id', template], args='all')
        if baseinfo:
            if self.settings.refresh_price is None:
                self.settings.refresh_price = 3600
                
            if time.time() - int(baseinfo[0]['timestamp']) > int(self.settings.refresh_price):
                price = self.fetch_template_price(template)
                if price == 0:
                    price = float(baseinfo[0]['price'])
                else:
                    self.base.edit_by('prices', ['template_id', template], price=price, timestamp=int(time.time()))
                return price
            else:
                return float(baseinfo[0]['price'])
        else:
            price = self.fetch_template_price(template) 
            self.base.add(
                table='prices',
                name=name,
                template_id=template,
                price=price,
                timestamp=int(time.time())
            )
            return price
                
    def fetch_template_price(self, template: str) -> float:    
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
        try:
            response = self.scraper.post(self.URL.RESOURSES, json={'account_name': name})
            #print(response.text)
            response = response.json()
            if 'code' in response.keys():
                time.sleep(5)
                raise ValueError(f'Internal Service Error | code: {response["code"]}')
            #v1
            if response['cpu_limit']['used'] == 0: 
                cpu = 100
            else:
                cpu = round(response['cpu_limit']['used'] / response['cpu_limit']['max'] * 100, 2)
            net = round(response['net_limit']['used'] / response['net_limit']['max'] * 100, 2)
            ram = round(response['ram_usage'] / response['ram_quota'] * 100, 2)

            #wax_to_cpu = response['cpu_limit']['max'] / float(response['total_resources']['cpu_weight'][:-4])
            #free_wax = (response['cpu_limit']['max'] - response['cpu_limit']['used']) / wax_to_cpu
            #print(free_wax)
            
            #free_wax = ( 1 - round(response['cpu_limit']['used'] / response['cpu_limit']['max'] * 100, 2) ) * float(response['total_resources']['cpu_weight'][:-4])
            
            if response['self_delegated_bandwidth'] is not None:
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
            self.log(f'Error to fetch resources: {name} ({e})')
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

    def get_names(self, path):
        return loadInStrings(separate=False).get(path)
        

    def get_accounts(self, whitelist: list=[], blacklist: list=[]):
        accounts_dumb = self.base.get_table('accounts')
        accounts_dumb = [
            {
                x['name']: {
                    'assets': to_dict(x['assets']), 
                    'tokens': to_dict(x['tokens'])
                }
            for x in accounts_dumb\
            if (x['name'] in whitelist or not whitelist) and\
               x['name'] not in blacklist
            }
        ]
        if accounts_dumb:
            return accounts_dumb[0]
        else:
            return accounts_dumb

    def split_text(self, t, limit=4096):
        t = str(t)
        if len(t) > int(limit):
            text = t.split('\n')
            _text = ""
            _cc = 0
            for i in text:
                if (_cc + len(i) + 2 < int(limit)):
                    _cc += len(i) + 2
                    _text += i + '\n'
                else:
                    yield _text
                    _text = i + '\n'
                    _cc = len(_text)
            else:
                yield _text

    @timer_decorator
    def get_timer(self):
        data = loadInJSON().get('./db/timer.json')
        if not data:
            data = {
                'start_timestamp': 0,
                'balances': {},
                'nfts': []
            }
        loadInJSON().save('./db/timer.json', data)
        return data

    @timer_decorator
    def create_timer(self):
        timer = self.get_timer()
        timer['start_timestamp'] = int(time.time())
        timer['balances'] = {}
        loadInJSON().save('./db/timer.json', timer)
        return timer
    
    @timer_decorator
    def update_timer(self, currency, value):
        timer = self.get_timer()
        if timer['balances'].get(currency):
            timer['balances'][currency] += value
        else:
            timer['balances'][currency] = value
            
        loadInJSON().save('./db/timer.json', timer)
        return timer
    
    @timer_decorator
    def zero_timer(self):
        loadInJSON().save('./db/timer.json', {})

    @timer_decorator
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
        
    @timer_decorator
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
        

    def get_rplanet_pools(self):
        node = self.URL.NODE      
        pools_payload = deepcopy(self.Payload.table_rows)
        pools_payload['code'] = "s.rplanet"
        pools_payload['key_type'] = 'i64'
        pools_payload['limit'] = 1000
        pools_payload['scope'] = "s.rplanet"
        pools_payload['table'] = "pools"
        
        pools = self.scraper.post(node, json=pools_payload).json()
        return pools['rows']

    def get_all_rplanet_info(self, accounts: list):
        result = {}
        pools = self.get_rplanet_pools()
        for account in accounts:
            result[account] = self.get_rplanet_info(account, pools)
        return result
            
    def get_rplanet_info(self, account: str, pools: list=None):
        result = {}
        node = self.URL.NODE
        if pools is None: pools = self.get_rplanet_pools()    

        sum_aether = 0
        for pool in pools:
            if not pool['enabled']:
                continue
            pool_payload = deepcopy(self.Payload.table_rows)
            pool_payload['code'] = "s.rplanet"
            pool_payload['key_type'] = 'name'
            pool_payload['limit'] = 1
            pool_payload['scope'] = pool['id']
            pool_payload['lower_bound'] = account
            pool_payload['upper_bound'] = account
            pool_payload['table'] = "accounts"
            pool_payload['limit'] = 1
            
            pool_info = self.scraper.post(node, json=pool_payload).json()
            
            aether_hour = ( float(pool['fraction'][:-8]) / float(pool['staked']) ) * float(pool_info['rows'][0]['staked']) if pool_info['rows'] else 0
            
            result[pool['id']] = {
                'collected': float(pool_info['rows'][0]['collected'][:-8]) if pool_info['rows'] else 0,
                'staked': int(pool_info['rows'][0]['staked']) if pool_info['rows'] else 0,
                'fraction': pool['fraction'],
                'total_pool_stake': pool['staked'],
                'aether_in_hour': round(aether_hour, 2)
            }
            sum_aether += round(aether_hour, 2)
            
        result['total_aether_in_hour'] = round(sum_aether, 2)
        return result
        