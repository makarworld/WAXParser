from re import M
import requests
from aiogram import Bot, Dispatcher, executor, types
import asyncio
from threading import Thread
import time
from load_data import loadInStrings, loadInJSON, loadInTxt
from logger import log_handler, logger
from copy import deepcopy
import json
import  random

from data import URL as _URL
from data import Payload as _Payload
from data import to_dict

from mw_sql import baseUniversal

_log = logger('WAXParser', 'WAXParser.log', 'INFO').get_logger()
log = log_handler(_log).log
base = baseUniversal('accounts.db')

URL = _URL()
Payload = _Payload()
limits_notifications = Payload.limits_notifications.copy()

def fetch_asset(asset_id: str):
    inbase = base.get_by("assets", get_by=['asset_id', asset_id], args='all')
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
                asset_response = s.get(f"{URL.ASSETS}{asset_id}", proxies=_proxy, headers=Payload.ass_headers).json()
                break
            except:
                time.sleep(1)
                continue
        else:
            info = {
                'success': False
            }
            
        if not info:
            info = get_asset_info(asset_response)
            if info['success']:
                base.add(
                    table='assets',
                    asset_id=asset_id,
                    name=info['name'],
                    rarity=info['rarity'], 
                    contract=info['contract'],
                    collection_name=info['collection_name'],
                    template_id=info['template_id']
                )
        
        return info

def get_assets(nft_response):
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

        if not base.get_by("assets", get_by=['asset_id', asset_id], args='all'):
            base.add(
                table='assets',
                asset_id=asset_id,
                name=info['name'],
                rarity=info['rarity'], 
                contract=info['contract'],
                collection_name=info['collection_name'],
                template_id=info['template_id']
            )
        
    return res

def get_token_price(url=URL.GET_WAX_PRICE):
    response = requests.get(url)
    response_json = response.json()
    return response_json['market_data']['current_price']['usd'], response_json['market_data']['current_price']['rub']

def get_price(template: str) -> float:
    return 0
    params = Payload.get_price_params.copy()
    params['template_id'] = template
    while True:
        try:
            response = requests.get(URL.GET_PRICE, proxies=_proxy, params=params).json()
            break
        except:
            log("Error with get item price...")
            time.sleep(5)
        
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

def get_resourses(name: str) -> dict:
    response = requests.get(URL.RESOURSES, json={"account_name": name}).json()
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
        log(f'Похоже аккаунт {name} вписан неверно или не существует ({e})', w=False)
        return {
            'cpu': 0,
            'net': 0,
            'ram': 0
        }
        

def get_notification_text(name: str, _type: str, body: str):
    return f"<b>Account:</b> <code>{name}</code>\n"\
           f"<b>Event type: {_type}</b>\n"\
           f"<i>{body}</i>\n"\
           f"<b>Link: {URL.WAX}{name}</b>\n"\
           f"<b>Atomic: {URL.ATOMIC}{name}</b>"

def get_links(name: str) -> tuple:
    return (
        URL.TOKENS.replace('{account}', name),
        URL.NFTS.replace('{account}', name)
    )

def get_accounts():
    accounts_dumb = base.get_table('accounts')
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

settings = loadInTxt().get('settings.txt')

bot = Bot(token=settings['bot_token'])
dp = Dispatcher(bot)
zalupa = asyncio.new_event_loop()

def notification(text):
    fut = asyncio.run_coroutine_threadsafe(send_welcome(text), zalupa)

async def send_welcome(text):
    try:
        await bot.send_message(int(settings['user_id']), text, parse_mode='html', disable_web_page_preview=True)
    except Exception as e:
        print(f'notification error: {e}')


s = requests.Session()
s.headers.update(Payload.ass_headers)
if settings['proxy']:
    _proxy = {
        'http': settings['proxy'],
        'https': settings['proxy']
    }
    s.proxies = _proxy
else:
    _proxy = None
    
notification(
    f"<b>WAXParser started.\n"
    f"Creator: <a href=\"https://vk.com/abuz.trade\">abuz.trade</a>\n"
    f"GitHub: <a href=\"https://github.com/makarworld/WAXParser\">WAXParser</a>\n\n"
    f"Tokens_notifications: {settings['tokens_notifications']}\n"
    f"NFTs_notifications: {settings['nfts_notifications']}</b>"
)

def run():
    while True:
        accounts = loadInStrings(clear_empty=True, separate=False).get('accounts.txt')
        accounts_dumb = get_accounts()
            
        for account in accounts:
            settings = loadInTxt().get('settings.txt')
            time.sleep(int(settings['timeout']))
            if account not in accounts_dumb.keys():
                accounts_dumb[account] = deepcopy(Payload.defoult_account_data)
                base.add(
                    table='accounts',
                    name=account,
                    assets=[],
                    tokens=accounts_dumb[account]['tokens']
                )
            
            token, nft = get_links(account)

            _isretry = False
            for _ in range(3):
                try:
                    tokens_response = requests.get(token, proxies=_proxy, timeout=10)
                    tokens_response = tokens_response.json()
                    if _isretry:
                        log("Подключение восстановлено!")
                    break
                except Exception as e:
                    log(f"[{_+1}]GetTokensError: {e}")
                    time.sleep(5)
                    _isretry = True
                    continue
            else:
                tokens_response = {'tokens': [{'symbol': x, 'amount': y } for x, y in accounts_dumb[account]['tokens'].items()]}
                
            _isretry = False
            for _ in range(3):
                try:
                    nfts_response = requests.get(nft, proxies=_proxy, timeout=10)
                    nfts_response = nfts_response.json()
                    if _isretry:
                        log("Подключение восстановлено!")
                    break
                except Exception as e:
                    log(f"[{_+1}]GetNFTsError: {e}")
                    time.sleep(5)
                    _isretry = True
                    continue
            else:
                nfts_response = accounts_dumb[account]['assets']
                
            _p = Payload.wax_token_payload.copy()
            _p['account'] = account

            tokens = [{x['symbol']: x['amount'] for x in tokens_response['tokens']}][0]
            
            resourses = get_resourses(account)
            
            
            tokens['CPU_STAKED'] = resourses['cpu_staked']
            
            if type(nfts_response) is not list:
                assets = list(get_assets(nfts_response).keys())
            else:
                assets = nfts_response

            # check tokens
            if tokens != accounts_dumb[account]['tokens']:
                # add new token or balance changed
                _a_ = False
                
                for k, v in tokens.items():
                    if k not in accounts_dumb[account]['tokens'].keys():
                        _type = "new token"
                        body = f"New token deposit to your wallet:\n"\
                               f"{k}: {v}"
                        accounts_dumb[account]['tokens'][k] = v
                        if settings['low_logging'] != 'true':
                            text = get_notification_text(
                                account, 
                                _type,
                                body
                            )
                        else:
                            text = f'<b>Account: <code>{account}</code>\nNew token: {k}: {v}</b>'
                            
                        if settings['tokens_notifications'] == 'true':
                            notification(text)
                        log(f'{account} new token deposit to your wallet: {k}: {v}')
                        base.edit_by('accounts', ['name', account], tokens=accounts_dumb[account]['tokens'])
                        _a_ = True
                    
                    
                else:
                    if _a_ == False:
                        for k1, v1 in tokens.items():
                            if v1 != accounts_dumb[account]['tokens'][k1]:
                                _type = "change balance"
                                if v1 > accounts_dumb[account]['tokens'][k1]:
                                    body = f"Add balance:\n"\
                                           f"{k1}: {v1} (+{round(v1 - accounts_dumb[account]['tokens'][k1], 5)} {k1})"
                                    log(f"{account} add balance: +{round(v1 - accounts_dumb[account]['tokens'][k1], 5)} {k1} [{v1} {k1}]")
                                    if settings['low_logging'] == 'true':
                                        _text = f"<b>Account: <code>{account}</code>\n+{round(v1 - accounts_dumb[account]['tokens'][k1], 5)} {k1} [{v1} {k1}]</b>"
                                    
                                    if round(v1 - accounts_dumb[account]['tokens'][k1], 6) <= 0.0009 and k1 == 'TLM':
                                        notification(
                                            f"<b>Account: {account}\n"\
                                            f"+{round(v1 - accounts_dumb[account]['tokens'][k1], 5)} TLM\n"\
                                            f"Seems like account was banned...</b>"
                                        )
                                    accounts_dumb[account]['tokens'][k1] = v1
                                
                                else:    
                                    body = f"Transfer balance:\n"\
                                           f"{k1}: {v1} (-{round(accounts_dumb[account]['tokens'][k1] - v1, 5)} {k1})"
                                    log(f"{account} transfer balance: -{round(accounts_dumb[account]['tokens'][k1] - v1, 5)} {k1} [{v1} {k1}]")
                                    if settings['low_logging'] == 'true':
                                        _text = f"<b>Account: <code>{account}</code>\n-{round(accounts_dumb[account]['tokens'][k1] - v1, 5)} {k1} [{v1} {k1}]</b>"
                                    
                                    accounts_dumb[account]['tokens'][k1] = v1
                                
                                if settings['low_logging'] != 'true':
                                    text = get_notification_text(
                                        account, 
                                        _type,
                                        body
                                    )
                                else:
                                    text = _text
                                    
                                if settings['tokens_notifications'] == 'true':
                                    notification(text)
                                    
                                base.edit_by('accounts', ['name', account], tokens=accounts_dumb[account]['tokens'])
                    _a_ = True
            
            # check assets 
            if assets != accounts_dumb[account]['assets']:
                # add or delete assets
                _type = "change assets"
                new_assets = [str(x) for x in assets if str(x) not in accounts_dumb[account]['assets']]
                del_assets = [str(x) for x in accounts_dumb[account]['assets'] if str(x) not in assets]
                
                if new_assets:
                    body = "Add NFTs:\n" + '\n'.join(new_assets)
                    
                    body += "\n\n"
                    
                    _text = f"<b>Account: <code>{account}</code></b>\n"
                    _price_sum = 0
                    for ass in new_assets:
                        parsed = fetch_asset(ass)
                        if not parsed['success']:
                            continue
                        price = get_price(parsed['template_id'])
                        body += f"<b>Asset: {ass}</b>\n"\
                                f"<b>Collection name: {parsed['collection_name']}</b>\n"\
                                f"<b>Name: {parsed['name']}</b>\n"\
                                f"<b>Rarity: {parsed['rarity']}</b>\n"\
                                f"<b>Price: {price} WAX</b>\n\n"
                        log(f"{account} new asset: {ass} {parsed['name']} ({price} WAX)")
                        _text += f"<b>[{ass}] {parsed['name']} - {price} WAX</b>\n"
                        _price_sum += price
                    
                    if settings['low_logging'] != 'true':
                        text = get_notification_text(
                            account, 
                            _type,
                            body
                        )
                    else:
                        text = _text
                        text += f"\n<b>+{round(_price_sum, 2)} WAX</b>"
                        
                    if settings['nfts_notifications'] == 'true':
                        notification(text)
                        
                elif del_assets:
                    _text = f"<b>Account: <code>{account}</code></b>\n" + '\n'.join(del_assets)
                    body = "Transfer/delete NFTs:\n" + '\n'.join(del_assets)
                    log(f"{account} transfer/delete NFTs: {' '.join(del_assets)}")
                    if settings['low_logging'] != 'true':
                        text = get_notification_text(
                            account, 
                            _type,
                            body
                        )
                    else:
                        text = _text
                    if settings['nfts_notifications'] == 'true':
                        notification(text)
                
                base.edit_by('accounts', ['name', account], assets=list(assets))
            
            # check account resourses
            resourses = get_resourses(account)
            for _res in resourses.keys():
                if 'stake' in _res:
                    continue
                if resourses[_res] > int(settings[_res+'_limit']):
                    if limits_notifications[_res].get(account):
                        if time.time() - limits_notifications[_res][account] >= int(settings['out_of_limit_timeout']):
                            # timeout done! 
                            notification(f"<b>Account {account} out of {_res.upper()} limit ({resourses[_res]}%).</b>")
                            log(f"Account {account} out of {_res.upper()} limit ({resourses[_res]}%).")
                            limits_notifications[_res][account] = int(time.time())
                    else:
                        limits_notifications[_res][account] = int(time.time())
                        notification(f"<b>Account {account} out of {_res.upper()} limit ({resourses[_res]}%).</b>")
                        log(f"Account {account} out of {_res.upper()} limit ({resourses[_res]}%).")

                    
# command /eval {some_code}
# command /exec {some_code}
@dp.message_handler(commands=['eval', 'exec'])
async def eval_handler(message: types.Message):
    try:
        if int(settings['user_id']) == message['from']['id']:
            c, cmd = message['text'].split()
            _t = c[1:]
            if _t == 'eval':
                if cmd.startswith('await'):
                    res = await eval(cmd[6:])
                else:
                    res = eval(cmd)
            else:
                exec(cmd)
                res = 'Ok'
            await message.reply(res)
            
    except Exception as e:
        _log.exception("Error /help: ")
        await message.reply(f"Error /help: {e}")
    
# command /info            
@dp.message_handler(commands=['info'])
async def info_handler(message: types.Message):
    try:
        accounts_dumb = get_accounts()
        text = f"<b>Accounts: {len(accounts_dumb.keys())}</b>\n"
        nfts = sum([len(accounts_dumb[x]['assets']) for x in accounts_dumb.keys()])
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

# command /accs          
@dp.message_handler(commands=['accs'])
async def accs_handler(message: types.Message):
    try:
        accounts = loadInStrings(clear_empty=True, separate=False).get('accounts.txt')
        accounts_dumb = get_accounts()
        text = ""
        for i, x in enumerate(accounts):
            text += f"[{i+1}] <code>{x}</code>"
            if accounts_dumb.get(x):
                if accounts_dumb[x]['tokens'].get('WAX'):
                    text += f" | {round(accounts_dumb[x]['tokens']['WAX'], 2)} WAX"
                else:
                    text += f" | 0 WAX"
                    
                if accounts_dumb[x]['tokens'].get('TLM'):
                    text += f" | {round(accounts_dumb[x]['tokens']['TLM'], 2)} TLM"
                else:
                    text += f" | 0 TLM"
            text += '\n'
                
        await bot.send_message(int(settings['user_id']), text, parse_mode='html')
    except Exception as e:
        _log.exception("Error /accs: ")
        await message.reply(f"Error /accs: {e}")
    
# command /course        
@dp.message_handler(commands=['course'])
async def course_handler(message: types.Message):
    try:
        tlm_usd, tlm_rub = get_token_price(URL.GET_TLM_PRICE)
        wax_usd, wax_rub = get_token_price(URL.GET_WAX_PRICE)
        text = f"<b><a href=\"{URL.COINGECKO_WAX_PAGE}\">WAX</a> -> USD: {wax_usd}$</b>\n"\
                f"<b><a href=\"{URL.COINGECKO_WAX_PAGE}\">WAX</a> -> RUB: {wax_rub} руб.</b>\n"
        text += f"<b><a href=\"{URL.COINGECKO_TLM_PAGE}\">TLM</a> -> USD: {tlm_usd}$</b>\n"\
                f"<b><a href=\"{URL.COINGECKO_TLM_PAGE}\">TLM</a> -> RUB: {tlm_rub} руб.</b>\n"
        
        await bot.send_message(int(settings['user_id']), text, parse_mode='html', disable_web_page_preview=True)
    except Exception as e:
        _log.exception("Error /course: ")
        await message.reply(f"Error /course: {e}")
    
# command /p {wax_name}    
@dp.message_handler(commands=['p'])
async def p_handler(message: types.Message):
    try:
        if len(message["text"].split()) != 2: 
            await bot.send_message(int(settings['user_id']), "Неверная команда.\nПример: /p namee.wam")
        else:
            c, name = message["text"].split()
            accounts_dumb = get_accounts()
            if name not in accounts_dumb.keys():
                await bot.send_message(int(settings['user_id']), "Нет информации.")
            else:
                await message.reply("Загрузка...\nПодождите пока все предметы спарсятся.\nОбычно занимает от 5 секунд до 3 минут.")
                account_summ_usd = 0
                account_summ_rub = 0
                text = f"<b>Account: {name}</b>\n"\
                       f"<b>NFTs: {len(accounts_dumb[name]['assets'])}</b>\n"\
                       f"<b>Tokens:</b>\n"
                
                tlm_usd, tlm_rub = get_token_price(URL.GET_TLM_PRICE)
                wax_usd, wax_rub = get_token_price(URL.GET_WAX_PRICE)
                for k, v in accounts_dumb[name]['tokens'].items():
                    if k == 'TLM':
                        text += f"<b>{k}: {round(v, 4)} ({round(v*tlm_usd, 2)}$) ({round(v*tlm_rub, 2)} руб.)</b>\n"
                        account_summ_usd += round(v*tlm_usd, 4)
                        account_summ_rub += round(v*tlm_rub, 4)
                        
                    elif k == 'WAX' or k == 'STAKE_CPU':
                        text += f"<b>{k}: {round(v, 4)} ({round(v*wax_usd, 2)}$) ({round(v*wax_rub, 2)} руб.)</b>\n"
                        account_summ_usd += round(v*wax_usd, 4)
                        account_summ_rub += round(v*wax_rub, 4)
                        
                    else:
                        text += f"<b>{k}: {round(v, 4)}</b>\n"
                
                text += "\n\n"
                ass_names = {}
                
                for ass in accounts_dumb[name]['assets']:
                    parsed = fetch_asset(ass)
                    if not parsed['success']:
                        continue

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

# command /on {resourse}  
# command /off {resourse}  
@dp.message_handler(commands=['on', 'off'])
async def onoff_handler(message: types.Message):
    try:
        if len(message['text'].split()) != 2:
            if message['text'] == '/on':
                await message.reply('Неверная команда. Введите команду по примеру ниже:\n/on nfts/tokens')
            else:
                await message.reply('Неверная команда. Введите команду по примеру ниже:\n/off nfts/tokens')
        else:
            c, _type = message['text'].split()
            to = True if c == '/on' else False
            settings = loadInTxt(separator=':').get('settings.txt')
            if settings.get(_type + "_notifications"):
                settings[_type + "_notifications"] = str(to).lower()
                loadInTxt().save('settings.txt', settings)
                await message.reply(f'Успешно изменен тип оповещений {_type}_notifications на {str(to).lower()}.')
            else:
                await message.reply('InvalidType: один из 2 возможных типов уведомлений nfts/tokens')
    except Exception as e:
        _log.exception("Error /on | /off: ")
        await message.reply(f"Error /on | /off: {e}")

# command /help
@dp.message_handler(commands=['help'])
async def help_handler(message: types.Message):
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
            "/p xxxxx.wam - <b>Полная информация по аккаунту</b>\n"\
            "/i xxxxx.wam — <b>Сгенерировать ссылку на контракт с 3 первыми лопатами/дрелями</b>\n"\
            "/ram число — <b>Уставить процент загрузки RAM после которых присылается оповещение</b>\n"\
            "/cpu число — <b>Уставить процент загрузки CPU после которых присылается оповещение</b>\n"\
            "/net число — <b>Уставить процент загрузки NET после которых присылается оповещение</b>\n",
            parse_mode='html')
    except Exception as e:
        _log.exception("Error /help: ")
        await message.reply(f"Error /help: {e}")
     
# command /i {wax_name}
@dp.message_handler(commands=['i'])
async def i_handler(message: types.Message):
    try:
        c, acc = message['text'].split()
        
        accounts_dumb = get_accounts()
        if accounts_dumb.get(acc):
            _ = 0
            _tools = []
            for asset in accounts_dumb[acc]['assets']:
                info = fetch_asset(asset)
                if not info['success']:
                    continue
                
                if info['name'] == 'Standard Drill' or info['name'] == 'Standard Shovel':
                    if _ >= 96:
                        break
                    else:
                        _tools.append(asset)
                    _ += 1
            t = str(_tools).replace("'", '"').replace(' ', '')
            link = f'https://wax.bloks.io/account/m.federation?loadContract=true&tab=Actions&account={acc}&scope=m.federation&limit=100&action=setbag&items={t}'
            link = link.replace('[', '%5B').replace(']', '%5D').replace('"', '%22')
            await bot.send_message(
                int(settings['user_id']),
                link,    
                parse_mode='html'
            )
        else:
            await message.reply('Not Found')
    except Exception as e:
        _log.exception("Error /i: ")
        await message.reply(f"Error /i: {e}")
        
# command /cpu {percent}
# command /net {percent}
# command /ram {percent}
@dp.message_handler(commands=['ram', 'net', 'cpu'])
async def res_handler(message: types.Message):
    try:
        c, resourse = message['text'].split()
        _type = c[1:]
        settings[_type.lower() + '_limit'] = int(resourse)
        await bot.send_message(
            int(settings['user_id']),
            f'<b>Установлено оповещение при {_type.upper()} > {resourse}%</b>',    
            parse_mode='html'
        )
        loadInTxt().save('settings.txt', settings)
        
    except Exception as e:
        _log.exception("Error /i: ")
        await message.reply(f"Error /i: {e}")
        
# command /get_cost
@dp.message_handler(commands=['get_cost'])
async def get_cost_handler(message: types.Message):
    try:
        await message.reply('Загрузка...\nВремя вычислений зависит от количества аккаунтов, обычно около 1-3 минут.')
        accounts_dumb = get_accounts()
        all_items = {}
        
        text = f"<b>Accounts: {len(accounts_dumb.keys())}</b>\n"
        nfts = sum([len(accounts_dumb[x]['assets']) for x in accounts_dumb.keys()])
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
            
        tlm_usd, tlm_rub = get_token_price(URL.GET_TLM_PRICE)
        wax_usd, wax_rub = get_token_price(URL.GET_WAX_PRICE)
        account_summ_usd = 0
        account_summ_rub = 0
        for k, v in tokens_sum.items():
            if k == 'TLM':
                text += f"<b>{k}: {round(v, 4)} ({round(v*tlm_usd, 2)}$) ({round(v*tlm_rub, 2)} руб.)</b>\n"
                account_summ_usd += round(v*tlm_usd, 4)
                account_summ_rub += round(v*tlm_rub, 4)
                
            elif k == 'WAX' or k == 'STAKE_CPU':
                text += f"<b>{k}: {round(v, 4)} ({round(v*wax_usd, 2)}$) ({round(v*wax_rub, 2)} руб.)</b>\n"
                account_summ_usd += round(v*wax_usd, 4)
                account_summ_rub += round(v*wax_rub, 4)
                
            else:
                text += f"<b>{k}: {round(v, 4)}</b>\n"
        
        text += "\n\n"
        
        for k, v in all_items.items():
            if v['count'] != 1:
                all_items[k]['text'] = f"<b>{k}: {v['count']} шт. {v['price']} WAX ({round(v['price']*v['count'], 2)} WAX)</b>\n"
            else:
                all_items[k]['text'] = f"<b>{k}: {v['count']} шт. {v['price']} WAX </b>\n"
                
        sorted_items = {k: v for k, v in sorted(all_items.items(), key=lambda item: item[1]['price'])}

        for k, v in sorted_items.items():
            text += v['text']
  
        text += "\n"
        
        usd_acc_summ = 0
        rub_acc_summ = 0
        text += f"<b>All accounts WAX: {round(wax_sum, 2)} WAX</b>\n"\
                f"<b>All accounts WAX USD price: {round(wax_sum*wax_usd, 2)} USD</b>\n"\
                f"<b>All accounts WAX RUB price: {round(wax_sum*wax_rub, 2)} RUB</b>\n"
        usd_acc_summ += round(wax_sum*wax_usd, 2)
        rub_acc_summ += round(wax_sum*wax_rub, 2)

        if tokens_sum.get('TLM'):
            tlm_usd, tlm_rub = get_token_price(URL.GET_TLM_PRICE)
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
        
# start thread
def start():
    while True:
        try:
            log('start')
            run()
        except Exception as e:
            _log.exception("MainError: ")
if __name__ == '__main__':
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
        
        