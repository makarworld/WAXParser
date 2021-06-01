from aiogram import Bot, Dispatcher, executor, types
import asyncio
from threading import Thread
import time
from copy import deepcopy
from cfscrape import create_scraper

from load_data import loadInStrings, loadInTxt
from logger import log_handler, logger
from data import URL as _URL
from data import Payload as _Payload
from data import to_dict
from mw_sql import baseUniversal
from _utils import _utils

scraper = create_scraper()
_log = logger('WAXParser', 'WAXParser.log', 'INFO').get_logger()
log = log_handler(_log).log
base = baseUniversal('accounts.db')

URL = _URL()
Payload = _Payload()
limits_notifications = Payload.limits_notifications.copy()
settings = loadInTxt().get('settings.txt')

bot = Bot(token=settings['bot_token'])
dp = Dispatcher(bot)
zalupa = asyncio.new_event_loop()

_u = _utils(settings, base, _log, log, scraper, URL, Payload)

def notification(text):
    fut = asyncio.run_coroutine_threadsafe(send_welcome(text), zalupa)

async def send_welcome(text):
    uzs = _u.get_user_ids()
    for u in uzs:
        try:
            if len(text) > 4096:
                for x in range(0, len(text), 4096):
                    await bot.send_message(u, text[x:x + 4096], parse_mode='html', disable_web_page_preview=True)
            else:
                await bot.send_message(u, text, parse_mode='html', disable_web_page_preview=True)

        except Exception as e:
            print(f'notification error: {e}')
            
async def send_reply(text, user_id):
    try:
        if len(text) > 4096:
            for x in _u.split_text(text):
                await bot.send_message(user_id, x, parse_mode='html', disable_web_page_preview=True)
        else:
            await bot.send_message(user_id, text, parse_mode='html', disable_web_page_preview=True)

    except Exception as e:
        print(f'SendMessageError: {repr(e)}')

notification(
    f"<b>WAXParser started.\n"
    f"Creator: <a href=\"https://vk.com/abuz.trade\">abuz.trade</a>\n"
    f"GitHub: <a href=\"https://github.com/makarworld/WAXParser\">WAXParser</a>\n"
    f"Donate: <a href=\"https://wax.bloks.io/account/abuztradewax\">abuztradewax</a>\n\n"
    f"Tokens_notifications: {settings['tokens_notifications']}\n"
    f"NFTs_notifications: {settings['nfts_notifications']}</b>"
)

def run():
    while True:
        accounts = loadInStrings(clear_empty=True, separate=False).get('accounts.txt')
        accounts_dumb = _u.get_accounts()
            
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
            
            token, nft = _u.get_links(account)

            for _ in range(3):
                try:
                    tokens_response = scraper.get(token, timeout=10)
                    if tokens_response.status_code == 200:
                        tokens_response = tokens_response.json()
                        break
                    else: 
                        raise Exception(f"url: {token} | status_code: {tokens_response.status_code}")
                    
                except Exception as e:
                    log(f"[{_+1}]GetTokensError: {e}")
                    time.sleep(5)
                    continue
            else:
                tokens_response = {'tokens': [{'symbol': x, 'amount': y } for x, y in accounts_dumb[account]['tokens'].items()]}
               
            for _ in range(3):
                try:
                    nfts_response = scraper.get(nft, timeout=10)
                    if nfts_response.status_code == 200:
                        nfts_response = nfts_response.json()
                        break
                    else: 
                        raise Exception(f"url: {token} | status_code: {nfts_response.status_code}")
                    
                except Exception as e:
                    log(f"[{_+1}]GetNFTsError: {e}")
                    time.sleep(5)
                    continue
            else:
                nfts_response = accounts_dumb[account]['assets']
                
            _p = Payload.wax_token_payload.copy()
            _p['account'] = account

            tokens = [{x['symbol']: x['amount'] for x in tokens_response['tokens']}][0]
            
            resourses = _u.get_resourses(account)
            
            
            tokens['CPU_STAKED'] = resourses['cpu_staked']
            
            if type(nfts_response) is not list:
                assets = list(_u.get_assets(nfts_response).keys())
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
                            text = _u.get_notification_text(
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
                                    _u.update_timer(k1, round(v1 - accounts_dumb[account]['tokens'][k1], 5))
                                    if settings['low_logging'] == 'true':
                                        _text = f"<b>Account: <code>{account}</code>\n+{round(v1 - accounts_dumb[account]['tokens'][k1], 5)} {k1} [{v1} {k1}]</b>"
                                    
                                    if round(v1 - accounts_dumb[account]['tokens'][k1], 6) <= 0.0001 and k1 == 'TLM':
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
                                    text = _u.get_notification_text(
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
                        parsed = _u.fetch_asset(ass)
                        if not parsed['success']:
                            continue
                        price = _u.get_price(parsed['template_id'])
                        body += f"<b>Asset: {ass}</b>\n"\
                                f"<b>Collection name: {parsed['collection_name']}</b>\n"\
                                f"<b>Name: {parsed['name']}</b>\n"\
                                f"<b>Rarity: {parsed['rarity']}</b>\n"\
                                f"<b>Price: {price} WAX</b>\n\n"
                        log(f"{account} new asset: {ass} {parsed['name']} ({price} WAX)")
                        _text += f"<b>[{ass}] {parsed['name']} - {price} WAX</b>\n"
                        _price_sum += price
                    
                    if settings['low_logging'] != 'true':
                        text = _u.get_notification_text(
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
                        text = _u.get_notification_text(
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
            resourses = _u.get_resourses(account)
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
            log(f"{account} fetched.")
            
            # NFT DROP 
            drops = _u.is_nft_dropped(account)
            if drops['success']:
                if drops['isdrop']:
                    # nft dropped
                    info_drop = {}
                    for _drop in drops['items']:
                        inf = base.get_by('assets', ['template_id', _drop], ['name'])[0]['name']
                        if inf in info_drop.keys():
                            info_drop[inf] += 1
                        else:
                            info_drop[inf] = 1
                    
                    print('drop NFT !!!')
                    print(info_drop)
                            
                else:
                    pass # nft not dropped
                
            else:
                _log.error(f"[{account}] Fail to fetch drops")

                    
# command /eval {some_code}
# command /exec {some_code}
@dp.message_handler(commands=['eval', 'exec'])
async def eval_handler(message: types.Message):
    if message['from']['id'] not in _u.get_user_ids():
        return
    
    try:
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
        await send_reply(res, message['from']['id'])
            
    except Exception as e:
        _log.exception("Error /help: ")
        await message.reply(f"Error /help: {e}")
    
# command /info            
@dp.message_handler(commands=['info'])
async def info_handler(message: types.Message):
    if message['from']['id'] not in _u.get_user_ids():
        return
    
    try:
        accounts_dumb = _u.get_accounts()
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
                    
        await send_reply(text, message['from']['id'])
    except Exception as e:
        _log.exception("Error /info: ")
        await message.reply(f"Error /info: {e}")

# command /accs          
@dp.message_handler(commands=['accs'])
async def accs_handler(message: types.Message):
    if message['from']['id'] not in _u.get_user_ids():
        return
    try:
        accounts = loadInStrings(clear_empty=True, separate=False).get('accounts.txt')
        accounts_dumb = _u.get_accounts()
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
                
        await send_reply(text, message['from']['id'])
        
    except Exception as e:
        _log.exception("Error /accs: ")
        await message.reply(f"Error /accs: {e}")
    
# command /course        
@dp.message_handler(commands=['course', 'c'])
async def course_handler(message: types.Message):
    if message['from']['id'] not in _u.get_user_ids():
        return
    try:
        tlm_usd, tlm_rub = _u.get_token_price(URL.GET_TLM_PRICE)
        wax_usd, wax_rub = _u.get_token_price(URL.GET_WAX_PRICE)
        text = f"<b><a href=\"{URL.COINGECKO_WAX_PAGE}\">WAX</a> -> USD: {wax_usd}$</b>\n"\
                f"<b><a href=\"{URL.COINGECKO_WAX_PAGE}\">WAX</a> -> RUB: {wax_rub} руб.</b>\n"
        text += f"<b><a href=\"{URL.COINGECKO_TLM_PAGE}\">TLM</a> -> USD: {tlm_usd}$</b>\n"\
                f"<b><a href=\"{URL.COINGECKO_TLM_PAGE}\">TLM</a> -> RUB: {tlm_rub} руб.</b>\n"
        
        await send_reply(text, message['from']['id'])
        
    except Exception as e:
        _log.exception("Error /course: ")
        await message.reply(f"Error /course: {e}")
    
# command /p {wax_name}    
@dp.message_handler(commands=['p'])
async def p_handler(message: types.Message):
    if message['from']['id'] not in _u.get_user_ids():
        return
    try:
        if len(message["text"].split()) != 2: 
            await bot.send_message(message['from']['id'], "Неверная команда.\nПример: /p namee.wam")
        else:
            c, name = message["text"].split()
            accounts_dumb = _u.get_accounts()
            if name not in accounts_dumb.keys():
                await bot.send_message(message['from']['id'], "Нет информации.")
            else:
                await message.reply("Загрузка...\nПодождите пока все предметы спарсятся.\nОбычно занимает от 5 секунд до 3 минут.")
                account_summ_usd = 0
                account_summ_rub = 0
                text = f"<b>Account: {name}</b>\n"\
                       f"<b>NFTs: {len(accounts_dumb[name]['assets'])}</b>\n"\
                       f"<b>Tokens:</b>\n"
                
                tlm_usd, tlm_rub = _u.get_token_price(URL.GET_TLM_PRICE)
                wax_usd, wax_rub = _u.get_token_price(URL.GET_WAX_PRICE)
                for k, v in accounts_dumb[name]['tokens'].items():
                    if k == 'TLM':
                        text += f"<b>{k}: {round(v, 4)} ({round(v*tlm_usd, 2)}$) ({round(v*tlm_rub, 2)} руб.)</b>\n"
                        account_summ_usd += round(v*tlm_usd, 4)
                        account_summ_rub += round(v*tlm_rub, 4)
                        
                    elif k == 'WAX' or k == 'CPU_STAKED':
                        text += f"<b>{k}: {round(v, 4)} ({round(v*wax_usd, 2)}$) ({round(v*wax_rub, 2)} руб.)</b>\n"
                        account_summ_usd += round(v*wax_usd, 4)
                        account_summ_rub += round(v*wax_rub, 4)
                        
                    else:
                        text += f"<b>{k}: {round(v, 4)}</b>\n"
                
                text += "\n\n"
                ass_names = {}
                
                for ass in accounts_dumb[name]['assets']:
                    parsed = _u.fetch_asset(ass)
                    if not parsed['success']:
                        continue

                    if parsed['name'] not in ass_names.keys():
                        ass_names[parsed['name']] = {'count': 1, 'info': parsed}
                    else:
                        ass_names[parsed['name']]['count'] += 1
                
                for x, y in ass_names.items():
                    price = _u.get_price( y['info']['template_id'] )
                    if y['count'] != 1:
                        text += f"<b>{x} - {y['count']} шт. {price} WAX (~{round(price*y['count'], 2)} WAX)</b>\n"
                    else:
                        text += f"<b>{x} - {y['count']} шт. {price} WAX</b>\n"
                        
                    account_summ_usd += round(price*wax_usd, 4)
                    account_summ_rub += round(price*wax_rub, 4)
                text += "\n"
                text += f"<b>Account USD price: {round(account_summ_usd, 2)} USD</b>\n"
                text += f"<b>Account RUB price: {round(account_summ_rub, 2)} RUB</b>\n"
                
                await send_reply(text, message['from']['id'])
    except Exception as e:
        _log.exception("Error /p: ")
        await message.reply(f"Error /p: {e}")

# command /on {resourse}  
# command /off {resourse}  
@dp.message_handler(commands=['on', 'off'])
async def onoff_handler(message: types.Message):
    if message['from']['id'] not in _u.get_user_ids():
        return
    try:
        if len(message['text'].split()) != 2:
            c = message['text']
            for _type in ['nfts', 'tokens']:
                to = True if c == '/on' else False
                settings = loadInTxt(separator=':').get('settings.txt')
                if settings.get(_type + "_notifications"):
                    settings[_type + "_notifications"] = str(to).lower()
                    loadInTxt().save('settings.txt', settings)
                    await message.reply(f'Успешно изменен тип оповещений {_type}_notifications на {str(to).lower()}.')
                else:
                    await message.reply('InvalidType: один из 2 возможных типов уведомлений nfts/tokens')
                
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
@dp.message_handler(commands=['help', 'h'])
async def help_handler(message: types.Message):
    if message['from']['id'] not in _u.get_user_ids():
        return
    try:
        await bot.send_message(
            message['from']['id'],
            "/help - <b>Список команд.</b>\n"\
            "/info - <b>Общая информация по аккаунтам</b>\n"\
            "/accs - <b>Список загруженных аккаунтов</b>\n"\
            "/course - <b>Текущие курсы TLM и WAX</b>\n"\
            "/get_cost — <b>Получить количество вещей, цену всех инвентарей и токенов на всех аккаунтах.</b>\n"\
            "/on nfts/tokens/assets — <b>Включение уведомлений</b>\n"\
            "/off nfts/tokens/assets — <b>Выключение уведомлений</b>\n"\
            "/p xxxxx.wam - <b>Полная информация по аккаунту</b>\n"\
            "/i xxxxx.wam — <b>Сгенерировать ссылку на контракт с 3 первыми лопатами/дрелями</b>\n"\
            "/f {query} — <b>Поиск NFT по аккаунтам с текстом {query} в названии</b>\n"\
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
    if message['from']['id'] not in _u.get_user_ids():
        return
    try:
        c, acc = message['text'].split()
        
        accounts_dumb = _u.get_accounts()
        if accounts_dumb.get(acc):
            _ = 0
            _tools = []
            for asset in accounts_dumb[acc]['assets']:
                info = _u.fetch_asset(asset)
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
                message['from']['id'],
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
    if message['from']['id'] not in _u.get_user_ids():
        return
    try:
        c, resourse = message['text'].split()
        _type = c[1:]
        settings[_type.lower() + '_limit'] = int(resourse)
        await bot.send_message(
            message['from']['id'],
            f'<b>Установлено оповещение при {_type.upper()} > {resourse}%</b>',    
            parse_mode='html'
        )
        loadInTxt().save('settings.txt', settings)
        
    except Exception as e:
        _log.exception(f"Error {message['text']}: ")
        await message.reply(f"Error {message['text']}: {e}")
        
# command /get_cost
@dp.message_handler(commands=['get_cost', 'gc'])
async def get_cost_handler(message: types.Message):
    if message['from']['id'] not in _u.get_user_ids():
        return
    try:
        await message.reply('Загрузка...\nВремя вычислений зависит от количества аккаунтов, обычно около 1-3 минут.')
        accounts_dumb = _u.get_accounts()
        all_items = {}
        
        text = f"<b>Accounts: {len(accounts_dumb.keys())}</b>\n"
        nfts = sum([len(accounts_dumb[x]['assets']) for x in accounts_dumb.keys()])
        text += f"<b>NFTs: {nfts}</b>\n"
        text += f"<b>Tokens:</b>\n"
        
        for k, v in accounts_dumb.items():
            for asset in v['assets']:
                parsed = _u.fetch_asset(asset)
                if not parsed['success']:
                    continue

                if all_items.get(parsed['name']):
                    all_items[parsed['name']]['count'] += 1
                else:
                    price = _u.get_price(parsed['template_id'])
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
          
        if tokens_sum.get('CPU_STAKED'):
            wax_sum += tokens_sum['CPU_STAKED']
            
        tlm_usd, tlm_rub = _u.get_token_price(URL.GET_TLM_PRICE)
        wax_usd, wax_rub = _u.get_token_price(URL.GET_WAX_PRICE)
        account_summ_usd = 0
        account_summ_rub = 0
        for k, v in tokens_sum.items():
            if k == 'TLM':
                text += f"<b>{k}: {round(v, 4)} ({round(v*tlm_usd, 2)}$) ({round(v*tlm_rub, 2)} руб.)</b>\n"
                account_summ_usd += round(v*tlm_usd, 4)
                account_summ_rub += round(v*tlm_rub, 4)
                
            elif k == 'WAX' or k == 'CPU_STAKED':
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

        await send_reply(text, message['from']['id'])
    except Exception as e:
        _log.exception("Error /get_cost: ")
        await message.reply(f"Error /get_cost: {e}")   
  
# command /i {wax_name}
@dp.message_handler(commands=['f', 'find'])
async def i_handler(message: types.Message):
    if message['from']['id'] not in _u.get_user_ids():
        return
    try:
        ex = message['text'][3:] if message['text'].startswith('/f') else message['text'][6:]
        if not ex:
            await message.reply('Query Not Found.')
        else:
            # {item: [accs]}
            accounts_dumb = _u.get_accounts()
            all_items = {}
            
            for k, v in accounts_dumb.items():
                for asset in v['assets']:
                    parsed = _u.fetch_asset(asset)
                    if not parsed['success']:
                        continue

                    if all_items.get(parsed['name']):
                        if k not in all_items[parsed['name']]:
                            all_items[parsed['name']].append(k)
                    else:
                        all_items[parsed['name']] = [k]
                  
            s_its = []   
            for _k, _v in all_items.items():
                if ex.lower() in _k.lower():
                    s_its.append({'name': _k, 'accs': _v})
            if s_its:
                text = "<b>Found items:</b>\n"
                for itm in s_its:
                    text += f"<b>Name: <i>{itm['name']}</i></b>\n"
                    
                    for ac in itm['accs']:
                        text += f"<code>{ac}</code>\n"
                    else:
                        text += "\n"

                await send_reply(text, message['from']['id'])
            else:
                await bot.send_message(message['from']['id'], '<b>Items not found</b>', parse_mode='html')
            
        
    except Exception as e:
        _log.exception("Error /f: ")
        await message.reply(f"Error /f: {e}")
        
@dp.message_handler(commands=['timer', 't'])
async def help_handler(message: types.Message):
    if message['from']['id'] not in _u.get_user_ids():
        return
    try:
        # /timer start
        # /timer 
        # /timer clear
        # /timer end
        if message['text'] == '/timer' or message['text'] == '/t':
            # return timer info
            timer = _u.timer_to_date()
            text = f"<b>[INFO] Timer\n"\
                   f"Start: {timer['strdate']}\n"\
                   f"Balanses:\n"
            text += "\n".join([f"+{round(y, 2)} {x}" for x, y in timer['timer']['balances'].items()])
            text += "\n\n"
            text += f"Passed: {timer['strbetween']}</b>"
            await send_reply(text, message['from']['id'])

            
        else:
            # start or end
            c, cmd = message['text'].split()[:2]
            if cmd.lower() not in ['start', 'clear', 'end']:
                await message.reply('Error: Command must be start, clear or end')
            else:
                if cmd.lower() == 'start':
                    timer = _u.get_timer()
                    if timer.get('start_timestamp') is None or timer.get('start_timestamp') == 0:
                        # create_timer
                        _u.create_timer()
                        await message.reply('Timer created')
                    else:
                        # timer already started
                        await message.reply('Error: timer already started')

                elif cmd.lower() == 'clear':
                    # clear timer
                    _u.zero_timer()
                    await message.reply('Timer cleared')
                    
                elif cmd.lower() == 'end':
                    timer = _u.timer_to_date()
                    text = f"<b>[INFO] Timer\n"\
                        f"Start: {timer['strdate']}\n"\
                        f"Balanses:\n"
                    text += "\n".join([f"{round(y, 2)} {x}" for x, y in timer['timer']['balances'].items()])
                    text += "\n\n"
                    text += f"Passed: {timer['strbetween']}</b>"
                    await send_reply(text, message['from']['id'])

                    _u.zero_timer()
                    await message.reply('Timer cleared')
                        
    except Exception as e:
        _log.exception("Error /help: ")
        await message.reply(f"Error /help: {e}")


      
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
        
        