import json

class URL:
    WAX_TOKEN = "https://wax.greymass.com/v1/chain/get_currency_balance"
    TOKENS = "http://wax.eosphere.io/v2/state/get_tokens?account={}"
    NODE = "https://api.wax.alohaeos.com/v1/chain/get_table_rows"
    NFTS = "https://wax.api.atomicassets.io/atomicassets/v1/assets?owner={}&page=1&limit=100000&order=desc&sort=asset_id"
    WAX = "https://wax.bloks.io/account/"
    ATOMIC = "https://wax.atomichub.io/profile/"
    ASSETS = "https://wax.api.atomicassets.io/atomicassets/v1/assets/"
    RESOURSES = "https://wax.pink.gg/v1/chain/get_account"
    GET_PRICE = "https://wax.api.atomicassets.io/atomicmarket/v1/sales"
    GET_WAX_PRICE = 'https://api.icodrops.com/portfolio/api/markets/coin?slug=wax'
    GET_TLM_PRICE = 'https://api.icodrops.com/portfolio/api/markets/coin?slug=alien-worlds'
    TEMPLATE_INFO = "https://wax.api.atomicassets.io/atomicassets/v1/templates?ids={}&page=1&limit=100&order=desc&sort=created"

    COINGECKO_WAX_PAGE = "https://www.coingecko.com/ru/%D0%9A%D1%80%D0%B8%D0%BF%D1%82%D0%BE%D0%B2%D0%B0%D0%BB%D1%8E%D1%82%D1%8B/wax"
    COINGECKO_TLM_PAGE = "https://www.coingecko.com/ru/%D0%9A%D1%80%D0%B8%D0%BF%D1%82%D0%BE%D0%B2%D0%B0%D0%BB%D1%8E%D1%82%D1%8B/alien-worlds"

class Payload:
    wax_token_payload = {
        'code': "eosio.token",
        'account': "", 
        'symbol': "WAX"
    }
    
    get_price_params = {
        "state":"1",
        "template_id": "",
        "order": "asc",
        "sort": "price",
        "limit": "1",
        "symbol": "WAX"
    }

    defoult_account_data = {
        "assets": [],
        "tokens": {}
    }

    limits_notifications = {
        'cpu': {},
        'net': {},
        'ram': {},
        'claim_nft': {}
    }

    ass_headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "max-age=0",
        "Connection": "keep-alive",
        "DNT": "1",
        "Host": "wax.api.atomicassets.io",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.85 Safari/537.36"
    }
    
    table_rows = {
        "json": True,
        "code": "s.rplanet",
        "scope": "",
        "table": "",
        "lower_bound": "",
        "upper_bound": "",
        "index_position": 1,
        "key_type": "",
        "limit": 1,
        "reverse": False,
        "show_payer": False
    }

def to_dict(string: str) -> dict:
    repalceses = [
        ["\'", '"'],
        ["'", '"'],
        ["False", 'false'],
        ["True", 'true']
    ]
    for x in repalceses:
        string = string.replace(x[0], x[1])
    return json.loads(string)

if __name__ == '__main__':
    u = Payload()
    print(u.ass_headers)