import requests
from aiogram import Bot, Dispatcher, executor, types
import asyncio
from threading import Thread
import time
from load_data import loadInStrings, loadInJSON, loadInTxt
from logger import log_handler, logger
from copy import deepcopy

_log = logger('WAXParser', 'WAXParser.log', 'INFO').get_logger()
log = log_handler(_log).log

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
GET_TLM_PRICE = 'https://api.coingecko.com/api/v3/coins/alien-worlds'

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

def fetch_asset(asset_id: str):
    assets_dump = loadInJSON(clear_empty=True, separate=False).get('assets_dump.json')
    if str(asset_id) in assets_dump.keys():
        return assets_dump[str(asset_id)]
    else:
        info = None
        for _ in range(3):
            try:
                asset_response = s.get(f"{ASSETS_URL}{asset_id}").json()
                break
            except:
                continue
        else:
            info = {
                'success': False
            }
        if not info:
            info = get_asset_info(asset_response)
        assets_dump[str(asset_id)] = info
        loadInJSON().save('assets_dump.json', assets_dump)
        
        return info
    

def get_token_price(url=GET_WAX_PRICE):
    response = requests.get(url)
    response_json = response.json()
    return response_json['market_data']['current_price']['usd'], response_json['market_data']['current_price']['rub']

def get_price(template: str) -> float:
    params = get_price_params.copy()
    params['template_id'] = template
    response = requests.get(GET_PRICE_URL, params=params).json()
    if response.get('data'):
        return round(int(response['data'][0]["listing_price"]) / 100000000, 2)
    else:
        log(response)
        return 0

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
    
log('Start!')
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
    f"<b>nft_notifications: {settings['nfts_notifications']}\n"
    f"tokens_notifications: {settings['tokens_notifications']}\n"
    f"assets_notifications: {settings['assets_notifications']}</b>"
)

def run():
    while True:
        accounts = loadInStrings(clear_empty=True, separate=False).get('accounts.txt')
        accounts_dumb = loadInJSON().get('accounts_dumb.json')
            
        for account in accounts:
            settings = loadInTxt().get('settings.txt')
            time.sleep(int(settings['timeout']))
            if account not in accounts_dumb.keys():
                accounts_dumb[account] = deepcopy(defoult_account_data)
                loadInJSON().save('accounts_dumb.json', accounts_dumb)
            
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
                log(f'{account} new NFT(s) {accounts_dumb[account]["nfts_count"]} NFT -> {nfts_count}')
                if settings['nfts_notifications'] == 'true':
                    notification(text)
                
            if tokens != accounts_dumb[account]['tokens']:
                # add new token or balance changed
                _a_ = False
                
                for k, v in tokens.items():
                    if k not in accounts_dumb[account]['tokens'].keys():
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
                        log(f'{account} new token deposit to your wallet: {k}: {v}')
                        loadInJSON().save('accounts_dumb.json', accounts_dumb)
                        _a_ = True
                    
                    
                else:
                    if _a_ == False:
                        for k1, v1 in tokens.items():
                            if v1 != accounts_dumb[account]['tokens'][k1]:
                                _type = "change balance"
                                if v1 > accounts_dumb[account]['tokens'][k1]:
                                    body = f"Add balance:\n"\
                                           f"{k1}: {v1} (+{round(v1 - accounts_dumb[account]['tokens'][k1], 5)} {k1})"
                                    log(f"{account} add balance: +{round(v1 - accounts_dumb[account]['tokens'][k1], 5)} {k1} [{k1} {v1}]")
                                    if round(v1 - accounts_dumb[account]['tokens'][k1], 6) <= 0.0002 and k1 == 'TLM':
                                        notification(
                                            f"<b>Account: {account}\n"\
                                            f"+{round(v1 - accounts_dumb[account]['tokens'][k1], 5)} TLM\n"\
                                            f"Аccount was banned...</b>"
                                        )
                                    accounts_dumb[account]['tokens'][k1] = v1
                                else:    
                                    body = f"Transfer balance:\n"\
                                           f"{k1}: {v1} (-{round(accounts_dumb[account]['tokens'][k1] - v1, 5)} {k1})"
                                    log(f"{account} transfer balance: -{round(accounts_dumb[account]['tokens'][k1] - v1, 5)} {k1} [{k1} {v1}]")
                                    accounts_dumb[account]['tokens'][k1] = v1
                                                
                                text = get_notification_text(
                                    account, 
                                    _type,
                                    body
                                )
                                if settings['tokens_notifications'] == 'true':
                                    notification(text)
                                loadInJSON().save('accounts_dumb.json', accounts_dumb)
                    _a_ = True
                    
            if assets != accounts_dumb[account]['assets']:
                # add or delete assets
                _type = "change assets"
                new_assets = [str(x) for x in assets if x not in accounts_dumb[account]['assets']]
                del_assets = [str(x) for x in accounts_dumb[account]['assets'] if x not in assets]
                
                if new_assets:
                    body = "Add assets:\n" + '\n'.join(new_assets)
                    
                    body += "\n\n"
                    
                    for ass in new_assets:
                        parsed = fetch_asset(ass)
                        
                        if parsed['success']:
                            price = get_price(parsed['template_id'])
                            body += f"<b>Asset: {ass}</b>\n"\
                                    f"<b>Collection name: {parsed['collection_name']}</b>\n"\
                                    f"<b>Name: {parsed['name']}</b>\n"\
                                    f"<b>Rarity: {parsed['rarity']}</b>\n"\
                                    f"<b>Price: {price} WAX</b>\n\n"
                            log(f"{account} new asset: {ass} {parsed['name']} ({price} WAX)")
                        else:
                            body += f"<b>Asset {ass} ParseError.</b>\n\n"
                            log(parsed)
                    
                    text = get_notification_text(
                        account, 
                        _type,
                        body
                    )
                    if settings['assets_notifications'] == 'true':
                        notification(text)
                else:
                    body = "Transfer/delete assets:\n" + '\n'.join(del_assets)
                    log(f"{account} transfer/delete assets: {' '.join(del_assets)}")
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
            if resourses['cpu'] > int(settings['cpu_limit']):
                if limits_notifications['cpu'].get(account):
                    if time.time() - limits_notifications['cpu'][account] >= int(settings['out_of_limit_timeout']):
                        # timeout done! 
                        notification(f"<b>Account {account} out of CPU limit ({resourses['cpu']}%).</b>")
                        log(f"Account {account} out of CPU limit ({resourses['cpu']}%).")
                else:
                    limits_notifications['cpu'][account] = int(time.time())
                    notification(f"<b>Account {account} out of CPU limit ({resourses['cpu']}%).</b>")
                    log(f"Account {account} out of CPU limit ({resourses['cpu']}%).")
                    
            if resourses['net'] > int(settings['net_limit']):
                if limits_notifications['net'].get(account):
                    if time.time() - limits_notifications['net'][account] >= int(settings['out_of_limit_timeout']):
                        # timeout done! 
                        notification(f"<b>Account {account} out of NET limit ({resourses['net']}%).</b>")
                        log(f"Account {account} out of NET limit ({resourses['net']}%).")
                else:
                    limits_notifications['net'][account] = int(time.time())
                    notification(f"<b>Account {account} out of NET limit ({resourses['net']}%).</b>")
                    log(f"Account {account} out of NET limit ({resourses['net']}%).")
            
            if resourses['ram'] > int(settings['ram_limit']):
                if limits_notifications['ram'].get(account):
                    if time.time() - limits_notifications['ram'][account] >= int(settings['out_of_limit_timeout']):
                        # timeout done! 
                        notification(f"<b>Account {account} out of RAM limit ({resourses['ram']}%).</b>")
                        log(f"Account {account} out of RAM limit ({resourses['ram']}%).")
                else:
                    limits_notifications['ram'][account] = int(time.time())
                    notification(f"<b>Account {account} out of RAM limit ({resourses['ram']}%).</b>")
                    log(f"Account {account} out of RAM limit ({resourses['ram']}%).")
                    
                    
@dp.message_handler(commands=['info'])
async def info_handler(message: types.Message):
    try:
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
    except Exception as e:
        _log.exception("Error /info: ")
        await message.reply(f"Error /info: {e}")

@dp.message_handler(commands=['accs'])
async def accs_handler(message: types.Message):
    try:
        accounts = loadInStrings(clear_empty=True, separate=False).get('accounts.txt')
        await bot.send_message(int(settings['user_id']), '\n'.join([f"<code>{x}</code>" for x in accounts]), parse_mode='html')
    except Exception as e:
        _log.exception("Error /accs: ")
        await message.reply(f"Error /accs: {e}")
    
@dp.message_handler(commands=['course'])
async def accs_handler(message: types.Message):
    try:
        tlm_usd, tlm_rub = get_token_price(GET_TLM_PRICE)
        wax_usd, wax_rub = get_token_price(GET_WAX_PRICE)
        text = f"<b>WAX -> USD: {wax_usd}$</b>\n"\
                f"<b>WAX -> RUB: {wax_rub} руб.</b>\n"
        text += f"<b>TLM -> USD: {tlm_usd}$</b>\n"\
                f"<b>TLM -> RUB: {tlm_rub} руб.</b>\n"
        
        await bot.send_message(int(settings['user_id']), text, parse_mode='html')
    except Exception as e:
        _log.exception("Error /course: ")
        await message.reply(f"Error /course: {e}")
    
    
@dp.message_handler(commands=['p'])
async def accs_handler(message: types.Message):
    try:
        if len(message["text"].split()) != 2: 
            await bot.send_message(int(settings['user_id']), "Неверная команда.\nПример: /p namee.wam")
        else:
            c, name = message["text"].split()
            accounts_dumb = loadInJSON().get('accounts_dumb.json')
            if name not in accounts_dumb.keys():
                await bot.send_message(int(settings['user_id']), "Нет информации.")
            else:
                await message.reply("Загрузка...\nПодождите пока все предметы спарсятся.\nОбычно занимает от 5 секунд до 3 минут.")
                account_summ_usd = 0
                account_summ_rub = 0
                text = f"<b>Account: {name}</b>\n"\
                       f"<b>NFTs: {accounts_dumb[name]['nfts_count']}</b>\n"\
                       f"<b>Assets: {len(accounts_dumb[name]['assets'])}</b>\n"\
                       f"<b>Tokens:</b>\n"
                
                tlm_usd, tlm_rub = get_token_price(GET_TLM_PRICE)
                wax_usd, wax_rub = get_token_price(GET_WAX_PRICE)
                for k, v in accounts_dumb[name]['tokens'].items():
                    if k == 'TLM':
                        text += f"<b>{k}: {round(v, 4)} ({round(v*tlm_usd, 2)}$) ({round(v*tlm_rub, 2)} руб.)</b>\n"
                        account_summ_usd += round(v*tlm_usd, 4)
                        account_summ_rub += round(v*tlm_rub, 4)
                        
                    elif k == 'WAX':
                        text += f"<b>{k}: {round(v, 4)} ({round(v*wax_usd, 2)}$) ({round(v*wax_rub, 2)} руб.)</b>\n"
                        account_summ_usd += round(v*wax_usd, 4)
                        account_summ_rub += round(v*wax_rub, 4)
                        
                    else:
                        text += f"<b>{k}: {round(v, 4)}</b>\n"
                
                text += "\n\n"
                ass_names = {}
                
                for ass in accounts_dumb[name]['assets']:
                    parsed = fetch_asset(ass)
                    if parsed['success']:
                        if parsed['name'] not in ass_names.keys():
                            ass_names[parsed['name']] = {'count': 1, 'info': parsed}
                        else:
                            ass_names[parsed['name']]['count'] += 1
                
                for x, y in ass_names.items():
                    price = get_price( y['info']['template_id'] )
                    if y['count'] != 1:
                        text += f"<b>{x} - {y['count']} шт. {price} WAX (~{round(price*y['count'], 2)} WAX)</b>\n"
                    else:
                        text += f"<b>{x} - {y['count']} шт. {price} WAX</b>\n"
                        
                    account_summ_usd += round(price*wax_usd, 4)
                    account_summ_rub += round(price*wax_rub, 4)
                text += "\n"
                text += f"<b>Account USD price: {round(account_summ_usd, 2)} USD</b>\n"
                text += f"<b>Account RUB price: {round(account_summ_rub, 2)} RUB</b>\n"
                await bot.send_message(int(settings['user_id']), text, parse_mode='html')
    except Exception as e:
        _log.exception("Error /p: ")
        await message.reply(f"Error /p: {e}")


@dp.message_handler(commands=['on', 'off'])
async def accs_handler(message: types.Message):
    try:
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
    except Exception as e:
        _log.exception("Error /on | /off: ")
        await message.reply(f"Error /on | /off: {e}")

@dp.message_handler(commands=['help'])
async def accs_handler(message: types.Message):
    try:
        await bot.send_message(
            int(settings['user_id']),
            "/help - <b>Список команд.</b>\n"\
            "/info - <b>Общая информация по аккаунтам</b>\n"\
            "/accs - <b>Список загруженных аккаунтов</b>\n"\
            "/course - <b>Текущие курсы TLM и WAX</b>\n"\
            "/get_cost — <b>Получить количество вещей, цену всех инвентарей и токенов на всех аккаунтах.</b>\n"\
            "/on nfts/tokens/assets — <b>Включение уведомлений</b>\n"\
            "/off nfts/tokens/assets — <b>Выключение уведомлений</b>\n"\
            "/p xxxxx.wam - <b>Полная информация по аккаунту</b>",
            parse_mode='html')
    except Exception as e:
        _log.exception("Error /help: ")
        await message.reply(f"Error /help: {e}")
        
        
@dp.message_handler(commands=['get_cost'])
async def accs_handler(message: types.Message):
    try:
        await message.reply('Загрузка...\nВремя вычислений зависит от количества аккаунтов, обычно около 1-3 минут.')
        accounts_dumb = loadInJSON().get('accounts_dumb.json')
        all_items = {}
        
        text = f"<b>Accounts: {len(accounts_dumb.keys())}</b>\n"
        nfts = sum([accounts_dumb[x]['nfts_count'] for x in accounts_dumb.keys()])
        text += f"<b>NFTs: {nfts}</b>\n"
        text += f"<b>Tokens:</b>\n"
        
        for k, v in accounts_dumb.items():
            for asset in v['assets']:
                parsed = fetch_asset(asset)
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
            
        tlm_usd, tlm_rub = get_token_price(GET_TLM_PRICE)
        wax_usd, wax_rub = get_token_price(GET_WAX_PRICE)
        account_summ_usd = 0
        account_summ_rub = 0
        for k, v in tokens_sum.items():
            if k == 'TLM':
                text += f"<b>{k}: {round(v, 4)} ({round(v*tlm_usd, 2)}$) ({round(v*tlm_rub, 2)} руб.)</b>\n"
                account_summ_usd += round(v*tlm_usd, 4)
                account_summ_rub += round(v*tlm_rub, 4)
            elif k == 'WAX':
                text += f"<b>{k}: {round(v, 4)} ({round(v*wax_usd, 2)}$) ({round(v*wax_rub, 2)} руб.)</b>\n"
                account_summ_usd += round(v*wax_usd, 4)
                account_summ_rub += round(v*wax_rub, 4)
            else:
                text += f"<b>{k}: {round(v, 4)}</b>\n"
        
        text += "\n\n"
        
        text += '\n'.join([f"<b>{k}: {v['count']} шт. {v['price']} WAX ({round(v['price']*v['count'], 2)}WAX)</b>" for k, v in all_items.items()])
        
        text += "\n\n"
        
        usd_acc_summ = 0
        rub_acc_summ = 0
        text += f"<b>All accounts WAX: {round(wax_sum, 2)} WAX</b>\n"\
                f"<b>All accounts WAX USD price: {round(wax_sum*wax_usd, 2)} USD</b>\n"\
                f"<b>All accounts WAX RUB price: {round(wax_sum*wax_rub, 2)} RUB</b>\n"
        usd_acc_summ += round(wax_sum*wax_usd, 2)
        rub_acc_summ += round(wax_sum*wax_rub, 2)

        if tokens_sum.get('TLM'):
            tlm_usd, tlm_rub = get_token_price(GET_TLM_PRICE)
            text += f"<b>All accounts TLM USD price: {round(tokens_sum['TLM']*tlm_usd, 2)} USD</b>\n"
            text += f"<b>All accounts TLM RUB price: {round(tokens_sum['TLM']*tlm_rub, 2)} RUB</b>\n"
            usd_acc_summ += round(tokens_sum['TLM']*tlm_usd, 2)
            rub_acc_summ += round(tokens_sum['TLM']*tlm_rub, 2)
        
        text += "\n" 
        text += f"<b>All accounts USD price: {round(usd_acc_summ, 2)} USD</b>\n"
        text += f"<b>All accounts RUB price: {round(rub_acc_summ, 2)} RUB</b>\n"
        
        text += "\n"
        text += f"<b>WAX -> USD: {wax_usd}$</b>\n"\
                f"<b>WAX -> RUB: {wax_rub} руб.</b>\n"
        text += f"<b>TLM -> USD: {tlm_usd}$</b>\n"\
                f"<b>TLM -> RUB: {tlm_rub} руб.</b>\n"
        await bot.send_message(
            int(settings['user_id']),
            text,    
            parse_mode='html')
    except Exception as e:
        _log.exception("Error /get_cost: ")
        await message.reply(f"Error /get_cost: {e}")
        
        
def start():
    while True:
        try:
            run()
        except Exception as e:
            _log.exception("MainError: ")
            
Thread(target=start).start()
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
        
        