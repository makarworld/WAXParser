import requests
from aiogram import Bot, Dispatcher, executor, types
import asyncio
from threading import Thread
import time
from load_data import loadInStrings, loadInJSON, loadInTxt

WAX_TOKEN_URL = "https://wax.greymass.com/v1/chain/get_currency_balance"
wax_token_payload = {'code': "eosio.token", 'account': "", 'symbol': "WAX"}
TOKENS_URL = "https://www.api.bloks.io/wax/account/{account}?type=getAccountTokens&coreSymbol=WAX"
NFTS_URL = "https://www.api.bloks.io/wax/nft?type=getAllNftsForAccount&network=wax&account={account}"
WAX_LINK = "https://wax.bloks.io/account/"
ATOMIC = "https://wax.atomichub.io/profile/"
ASSETS_URL = "https://wax.api.atomicassets.io/atomicassets/v1/assets/"
RESOURSES_URL = "https://wax.greymass.com/v1/chain/get_account"
GET_PRICE_URL = "https://wax.api.atomicassets.io/atomicmarket/v1/sales"
GET_WAX_PRICE = 'https://api.coingecko.com/api/v3/coins/wax'

get_price_params = {
    "state":"1",
    "template_id": "",
    "order": "asc",
    "sort": "price",
    "limit": "1",
    "symbol": "WAX"
}

defoult_account_data = {
    "nfts_count": 0,
    "assets": [],
    "tokens": {}
}

limits_notifications = {
    'cpu': {},
    'net': {},
    'ram': {}
}

def get_wax_price():
  response = requests.get(GET_WAX_PRICE)
  response_json = response.json()
  return response_json['market_data']['current_price']['usd'], response_json['market_data']['current_price']['rub']

def get_price(template: str) -> float:
    params = get_price_params.copy()
    params['template_id'] = template
    response = requests.get(GET_PRICE_URL, params=params).json()
    return round(int(response['data'][0]["listing_price"]) / 100000000, 2)

def get_asset_info(asset_response):
    if asset_response['success']:
        asset_info = asset_response.get('data')
        if asset_info:
            contract = asset_info.get('contract')
            collection = asset_info.get('collection')
            collection_name = collection.get('name') if collection else None
            item_name = asset_info.get('name')
            
            rarity = asset_info.get('data').get('rarity') if collection_name == 'Alien Worlds' else None
            template = asset_info.get('template')
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

def get_resourses(name: str) -> dict:
    response = requests.get(RESOURSES_URL, json={"account_name": name}).json()
    cpu = round(response['cpu_limit']['used'] / response['cpu_limit']['max'] * 100, 2)
    net = round(response['net_limit']['used'] / response['net_limit']['max'] * 100, 2)
    ram = round(response['ram_usage'] / response['ram_quota'] * 100, 2)
    return {
        'cpu': cpu,
        'net': net,
        'ram': ram
    }

def get_notification_text(name: str, _type: str, body: str):
    return f"<b>Account:</b> <code>{name}</code>\n"\
           f"<b>Event type: {_type}</b>\n"\
           f"<i>{body}</i>\n"\
           f"<b>Link: {WAX_LINK}{name}</b>\n"\
           f"<b>Atomic: {ATOMIC}{name}</b>"

def get_links(name: str) -> tuple:
    return (
        TOKENS_URL.replace('{account}', name),
        NFTS_URL.replace('{account}', name)
    )

settings = loadInTxt().get('settings.txt')

bot = Bot(token=settings['bot_token'])
dp = Dispatcher(bot)
zalupa = asyncio.new_event_loop()

def notification(text):
    fut = asyncio.run_coroutine_threadsafe(send_welcome(text), zalupa)
    print('Send notification')

async def send_welcome(text):
    try:
        await bot.send_message(int(settings['user_id']), text, parse_mode='html')
    except Exception as e:
        print(f'notification error: {e}')


s = requests.Session()
notification(
    f"nft_notifications: {settings['nfts_notifications']}\n"
    f"tokens_notifications: {settings['tokens_notifications']}\n"
    f"assets_notifications: {settings['assets_notifications']}"
)

def run():
    while True:
        accounts = loadInStrings(clear_empty=True, separate=False).get('accounts.txt')
        accounts_dumb = loadInJSON().get('accounts_dumb.json')
            
        for account in accounts:
            time.sleep(int(settings['timeout']))
            if account not in accounts_dumb.keys():
                accounts_dumb[account] = defoult_account_data
            
            token, nft = get_links(account)
            try:
                tokens_response = s.get(token).json()
                nfts_response = s.get(nft).json()
            except:
                continue
            _p = wax_token_payload.copy()
            _p['account'] = account
            try:
                wax_balance = s.post(WAX_TOKEN_URL, json=_p).json()
            except:
                continue
            
            
            tokens = [{x['currency']: x['amount'] for x in tokens_response['tokens']}][0]
            if wax_balance:
                wax_balance = float(wax_balance[0][:-4])
                tokens['WAX'] = wax_balance
            
            assets = [x.get('primary_key') for x in nfts_response if x.get('primary_key') is not None]
            nfts_count = len(nfts_response)

            if nfts_count != accounts_dumb[account]['nfts_count']:
                # nfts_count changed
                if nfts_count > accounts_dumb[account]['nfts_count']:
                    _type = 'new NFT'
                    body = f"New NFT card(s) in your inventory.\n"\
                        f"{accounts_dumb[account]['nfts_count']} NFT -> {nfts_count} NFT"
                else:
                    _type = 'NFT transfer/sold'
                    body = f"NFT card(s) was sold or transfer.\n"\
                        f"{accounts_dumb[account]['nfts_count']} NFT -> {nfts_count} NFT"
                    
                text = get_notification_text(
                    account, 
                    _type,
                    body
                )
                
                accounts_dumb[account]['nfts_count'] = nfts_count
                loadInJSON().save('accounts_dumb.json', accounts_dumb)
                if settings['nfts_notifications'] == 'true':
                    notification(text)
                
            if tokens != accounts_dumb[account]['tokens']:
                # add new token or balance changed
                a = False
                for k, v in tokens.items():
                    if k not in accounts_dumb[account]['tokens']:
                        _type = "new token"
                        body = f"New token deposit to your wallet:\n"\
                            f"{k}: {v}"
                        accounts_dumb[account]['tokens'][k] = v
                        text = get_notification_text(
                            account, 
                            _type,
                            body
                        )
                        if settings['tokens_notifications'] == 'true':
                            notification(text)
                        loadInJSON().save('accounts_dumb.json', accounts_dumb)
                        a = True
                    
                    
                else:
                    if not a:
                            
                        for k1, v1 in tokens.items():
                            if v1 != accounts_dumb[account]['tokens'][k1]:
                                _type = "change balance"
                                if v1 > accounts_dumb[account]['tokens'][k1]:
                                    body = f"Add balance:\n"\
                                        f"{k1}: {v1} (+{round(v1 - accounts_dumb[account]['tokens'][k1], 4)} {k1})"
                                    accounts_dumb[account]['tokens'][k1] = v1
                                else:    
                                    body = f"Transfer balance:\n"\
                                        f"{k1}: {v1} (-{round(accounts_dumb[account]['tokens'][k1] - v1, 4)} {k1})"
                                    accounts_dumb[account]['tokens'][k1] = v1
                                                
                                text = get_notification_text(
                                    account, 
                                    _type,
                                    body
                                )
                                if settings['tokens_notifications'] == 'true':
                                    notification(text)
                                loadInJSON().save('accounts_dumb.json', accounts_dumb)
                
            if assets != accounts_dumb[account]['assets']:
                # add or delete assets
                _type = "change assets"
                new_assets = [str(x) for x in assets if x not in accounts_dumb[account]['assets']]
                del_assets = [str(x) for x in accounts_dumb[account]['assets'] if x not in assets]
                
                if new_assets:
                    body = "Add assets:\n" + '\n'.join(new_assets)
                    
                    body += "\n\n"
                    
                    for ass in new_assets:
                        try:
                            asset_response = s.get(f"{ASSETS_URL}{ass}").json()
                        except:
                            body += f"Asset {ass} response error.\n"
                            
                        parsed = get_asset_info(asset_response)
                        
                        price = get_price(parsed['template_id'])
                        
                        if parsed['success']:
                            body += f"<b>Asset: {ass}</b>\n"\
                                    f"<b>Collection name: {parsed['collection_name']}</b>\n"\
                                    f"<b>Name: {parsed['name']}</b>\n"\
                                    f"<b>Rarity: {parsed['rarity']}</b>\n"\
                                    f"<b>Price: {price} WAX</b>\n\n"
                        else:
                            body += f"<b>Asset {ass} ParseError.</b>\n\n"
                            print(parsed)
                    
                    text = get_notification_text(
                        account, 
                        _type,
                        body
                    )
                    if settings['assets_notifications'] == 'true':
                        notification(text)
                else:
                    body = "Transfer/delete assets:\n" + '\n'.join(del_assets)
                    text = get_notification_text(
                        account, 
                        _type,
                        body
                    )
                    if settings['assets_notifications'] == 'true':
                        notification(text)
                    
                accounts_dumb[account]['assets'] = assets
                loadInJSON().save('accounts_dumb.json', accounts_dumb)
                
            resourses = get_resourses(account)
            print(account, 'cpu', resourses['cpu'])
            print(account, 'net', resourses['net'])
            print(account, 'ram', resourses['ram'])
            if resourses['cpu'] > int(settings['cpu_limit']):
                if limits_notifications['cpu'].get(account):
                    if time.time() - limits_notifications['cpu'][account] >= int(settings['out_of_limit_timeout']):
                        # timeout done! 
                        notification(f"<b>Account {account} out of CPU limit ({resourses['cpu']}%).</b>")
                else:
                    limits_notifications['cpu'][account] = int(time.time())
                    notification(f"<b>Account {account} out of CPU limit ({resourses['cpu']}%).</b>")
                    
            if resourses['net'] > int(settings['net_limit']):
                if limits_notifications['net'].get(account):
                    if time.time() - limits_notifications['net'][account] >= int(settings['out_of_limit_timeout']):
                        # timeout done! 
                        notification(f"<b>Account {account} out of NET limit ({resourses['net']}%).</b>")
                else:
                    limits_notifications['net'][account] = int(time.time())
                    notification(f"<b>Account {account} out of NET limit ({resourses['net']}%).</b>")
            
            
            if resourses['ram'] > int(settings['ram_limit']):
                if limits_notifications['ram'].get(account):
                    if time.time() - limits_notifications['ram'][account] >= int(settings['out_of_limit_timeout']):
                        # timeout done! 
                        notification(f"<b>Account {account} out of RAM limit ({resourses['ram']}%).</b>")
                else:
                    limits_notifications['ram'][account] = int(time.time())
                    notification(f"<b>Account {account} out of RAM limit ({resourses['ram']}%).</b>")
                    
                    
@dp.message_handler(commands=['info'])
async def info_handler(message: types.Message):
    accounts_dumb = loadInJSON().get('accounts_dumb.json')
    text = f"<b>Accounts: {len(accounts_dumb.keys())}</b>\n"
    nfts = sum([accounts_dumb[x]['nfts_count'] for x in accounts_dumb.keys()])
    text += f"<b>NFTs: {nfts}</b>\n"
    text += f"<b>Tokens:</b>\n"
    tokens = [accounts_dumb[x]['tokens'] for x in accounts_dumb]
    tokens_sum = {}
    for t in tokens:
        for k, v in t.items():
            if k not in tokens_sum.keys():
                tokens_sum[k] = v
            else:
                tokens_sum[k] += v
    text += '\n'.join([f"<b>{k}: {round(v, 4)}</b>" for k, v in tokens_sum.items()])
                
    await bot.send_message(int(settings['user_id']), text, parse_mode='html')

@dp.message_handler(commands=['accs'])
async def accs_handler(message: types.Message):
    accounts = loadInStrings(clear_empty=True, separate=False).get('accounts.txt')
    await bot.send_message(int(settings['user_id']), '\n'.join([f"<code>{x}</code>" for x in accounts]), parse_mode='html')
    
@dp.message_handler(commands=['p'])
async def accs_handler(message: types.Message):
    if len(message["text"].split()) != 2: 
        await bot.send_message(int(settings['user_id']), "Неверная команда.\nПример: /p namee.wam")
    else:
        c, name = message["text"].split()
        accounts_dumb = loadInJSON().get('accounts_dumb.json')
        if name not in accounts_dumb.keys():
            await bot.send_message(int(settings['user_id']), "Нет информации.")
        else:
            text = f"<b>Account: {name}</b>\n"\
                   f"<b>NFTs: {accounts_dumb[name]['nfts_count']}</b>\n"\
                   f"<b>Assets: {len(accounts_dumb[name]['assets'])}</b>\n"\
                   f"<b>Tokens:</b>\n"
            text += '\n'.join([f"<b>{k}: {round(v, 4)}</b>" for k, v in accounts_dumb[name]['tokens'].items()])
            
            text += "\n\n"
            for ass in accounts_dumb[name]['assets']:
                try:
                    asset_response = s.get(f"{ASSETS_URL}{ass}").json()
                except Exception as e:
                    print(e)
                    text += f"Asset {ass} response error.\n"
                    
                parsed = get_asset_info(asset_response)
                
                price = get_price(parsed['template_id'])
                
                if parsed['success']:
                    text += f"<b>Asset: {ass}</b>\n"\
                            f"<b>Collection name: {parsed['collection_name']}</b>\n"\
                            f"<b>Name: {parsed['name']}</b>\n"\
                            f"<b>Rarity: {parsed['rarity']}</b>\n"\
                            f"<b>Price: {price} WAX</b>\n\n"
                else:
                    text += f"<b>Asset {ass} ParseError.</b>\n\n"
                    print(parsed)
                    
            await bot.send_message(int(settings['user_id']), text, parse_mode='html')

@dp.message_handler(commands=['on', 'off'])
async def accs_handler(message: types.Message):
    if len(message['text'].split()) != 2:
        if message['text'] == '/on':
            await message.reply('Неверная команда. Введите команду по примеру ниже:\n/on nfts/assets/tokens')
        else:
            await message.reply('Неверная команда. Введите команду по примеру ниже:\n/off nfts/assets/tokens')
    else:
        c, _type = message['text'].split()
        to = True if c == '/on' else False
        settings = loadInTxt(separator=':').get('settings.txt')
        if settings.get(_type + "_notifications"):
            settings[_type + "_notifications"] = str(to).lower()
            loadInTxt().save('settings.txt', settings)
            await message.reply(f'Успешно изменен тип оповещений {_type}_notifications на {str(to).lower()}.')
        else:
            await message.reply('InvalidType: один из 3 возможных типов уведомлений nfts/assets/tokens')
    
@dp.message_handler(commands=['help'])
async def accs_handler(message: types.Message):
    await bot.send_message(
        int(settings['user_id']),
        "/help - <b>Список команд.</b>\n"\
        "/info - <b>Общая информация по аккаунтам</b>\n"\
        "/accs - <b>Список загруженных аккаунтов</b>\n"\
        "/p xxxxx.wam - <b>Информация по аккаунту</b>",        
        parse_mode='html')
    
@dp.message_handler(commands=['get_cost'])
async def accs_handler(message: types.Message):
    await message.reply('Загрузка...\nВремя вычислений зависит от количества аккаунтов, обычно около 1-3 минут.')
    accounts_dumb = loadInJSON().get('accounts_dumb.json')
    all_items = {}
    
    text = f"<b>Accounts: {len(accounts_dumb.keys())}</b>\n"
    nfts = sum([accounts_dumb[x]['nfts_count'] for x in accounts_dumb.keys()])
    text += f"<b>NFTs: {nfts}</b>\n"
    text += f"<b>Tokens:</b>\n"
    
    for k, v in accounts_dumb.items():
        for asset in v['assets']:
            try:
                asset_response = s.get(f"{ASSETS_URL}{asset}").json()
            except Exception as e:
                print(e)
                continue
            
            parsed = get_asset_info(asset_response)
            if not parsed['success']:
                continue
            
            if all_items.get(parsed['name']):
                all_items[parsed['name']]['count'] += 1
            else:
                price = get_price(parsed['template_id'])
                all_items[parsed['name']] = {'count': 1, 'price': price}
                
    wax_sum = sum([y['count']*y['price'] for x, y in all_items.items()])
    tokens = [accounts_dumb[x]['tokens'] for x in accounts_dumb]
    tokens_sum = {}
    for t in tokens:
        for k, v in t.items():
            if k not in tokens_sum.keys():
                tokens_sum[k] = v
            else:
                tokens_sum[k] += v
    if tokens_sum.get('WAX'):
        wax_sum += tokens_sum['WAX']
    text += '\n'.join([f"<b>{k}: {round(v, 4)}</b>" for k, v in tokens_sum.items()])
    text += "\n\n"
    
    text += '\n'.join([f"<b>{k}: {v['count']} шт. (~{v['price']} WAX)</b>" for k, v in all_items.items()])
    
    text += "\n\n"
    
    wax_usd, wax_rub = get_wax_price()
    text += f"<b>All accounts WAX price: {round(wax_sum, 2)} WAX</b>\n"\
            f"<b>All accounts USD price: {round(wax_sum*wax_usd, 2)} USD</b>\n"\
            f"<b>All accounts RUB price: {round(wax_sum*wax_rub, 2)} RUB</b>\n\n"\
    
    text += f"<b>WAX -> USD: {wax_usd}$</b>\n"\
            f"<b>WAX -> RUB: {wax_rub} руб.</b>\n"
            
    await bot.send_message(
        int(settings['user_id']),
        text,    
        parse_mode='html')
        
Thread(target=run).start()
executor.start_polling(dp, skip_updates=True, loop=zalupa)
"""
{
    "name": {
        "nfts_count": 1
        "assets": []
        "tokens": {
            "TLM": 1,
            "WAX": 1
        }
    }
}

"""
        
        