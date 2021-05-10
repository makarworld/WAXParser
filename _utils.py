import time
from load_data import to_dict

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
        return response_json['market_data']['current_price']['usd'], response_json['market_data']['current_price']['rub']

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
        response = self.scraper.get(self.URL.RESOURSES, json={"account_name": name}).json()
        try:
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
            self.log(f'Похоже аккаунт {name} вписан неверно или не существует ({e})', w=False)
            return {
                'cpu': 0,
                'net': 0,
                'ram': 0,
                'cpu_staked': 0
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
