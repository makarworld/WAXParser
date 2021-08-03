try:
    from packages.telegram_hundlers import telegramHundlers
    from aiogram import Bot, Dispatcher, executor
    import asyncio
    from threading import Thread
    import time
    from copy import deepcopy
    from cfscrape import create_scraper
    import os

    from packages.load_data import loadInStrings, loadInTxt, Struct, load_settings
    from packages.logger import log_handler, logger
    from packages.data import URL as _URL
    from packages.data import Payload as _Payload
    from packages.mw_sql import baseUniversal
    from packages._utils import _utils
    from packages.telegram_hundlers import telegramHundlers
except ImportError as e:
    print(f"ImportError: {e}")
    print("RU: Установите библиотеки и попробуйте снова.")
    print("**Запустите файл install_packages.bat в папке install чтобы автоматически установить библиотеки")
    print("EN: Please install packages and try again.")
    print("**Open file \"install_packages.bat\" in folder \"install\", it's automatically install needed packages.")
    input()
    quit()
    
banner = """
      _______________________________________________________________________
     |                                                                       |
     |        __        ___    __  __  ____                                  |
     |        \ \      / / \   \ \/ / |  _ \ __ _ _ __ ___  ___ _ __         |
     |         \ \ /\ / / _ \   \  /  | |_) / _` | '__/ __|/ _ \ '__|        |
     |          \ V  V / ___ \  /  \  |  __/ (_| | |  \__ \  __/ |           |
     |           \_/\_/_/   \_\/_/\_\ |_|   \__,_|_|  |___/\___|_|           |
     |                                                                       |
     |      _                   _                _                 _         |
     |     | |__  _   _    __ _| |__  _   _ ____| |_ _ __ __ _  __| | ___    |
     |     | '_ \| | | |  / _` | '_ \| | | |_  /| __| '__/ _` |/ _` |/ _ \   |
     |     | |_) | |_| | | (_| | |_) | |_| |/ / | |_| | | (_| | (_| |  __/   |
     |     |_.__/ \__, |  \__,_|_.__/ \__,_/___(_)__|_|  \__,_|\__,_|\___|   |
     |            |___/                                                      |
     |_______________________________________________________________________|
"""
print(banner)

# message limit (must be lower then 4096)
message_limit = 2048

# path
settings_path = os.path.realpath('.') + '/settings.txt'
accounts_path = os.path.realpath('.') + '/db/accounts.txt'
db_path = os.path.realpath('.') + '/db/accounts.db'
log_path = os.path.realpath('.') + '/parser.log'
timer_path = os.path.realpath('.') + '/db/timer.json'

# 
scraper = create_scraper()
_log = logger(name='WAXParser', file=log_path, level='INFO').get_logger()
log = log_handler(_log).log
base = baseUniversal(db_path)


# settings and other data
URL = _URL()
Payload = _Payload()
limits_notifications = deepcopy(Payload.limits_notifications)
settings = loadInTxt().get(settings_path)
settings = Struct(**settings)
_u = _utils(settings, base, _log, log, scraper, URL, Payload)

# validate settings
if not settings.bot_token or\
    not settings.user_id: 
    log('Fill bot_token and user_id in settings.txt and restart')
    input()
    quit()



# telegram
bot = Bot(token=settings.bot_token)
dp = Dispatcher(bot)
zalupa = asyncio.new_event_loop()

def notification(text):
    asyncio.run_coroutine_threadsafe(send_to_all_ids(text), zalupa)

async def send_to_all_ids(text):
    uzs = _u.get_user_ids()
    for u in uzs:
        try:
            await send_reply(text, u)
        except Exception as e:
            print(f'send_to_all_ids error: {e}')
            


async def send_reply(text, user_id):
    try:
        text = str(text)
        if not text: text = 'Empty message'
        
        if len(text) > message_limit:
            for x in _u.split_text(text, message_limit):
                await bot.send_message(user_id, x, parse_mode='html', disable_web_page_preview=True)
        else:
            await bot.send_message(user_id, text, parse_mode='html', disable_web_page_preview=True)

    except Exception as e:
        _log.exception(f'send_reply error: {repr(e)}')

def parser(settings, limits_notifications):
    notification(
        f"<b>WAXParser started.\n"
        f"Creator: <a href=\"https://vk.com/abuz.trade\">abuz.trade</a>\n"
        f"GitHub: <a href=\"https://github.com/makarworld/WAXParser\">WAXParser</a>\n"
        f"Donate: <a href=\"https://wax.bloks.io/account/abuztradewax\">abuztradewax</a>\n\n"
        f"Tokens_notifications: {settings.tokens_notifications}\n"
        f"NFTs_notifications: {settings.nfts_notifications}</b>"
    )
    
    while True:
        accounts = loadInStrings(clear_empty=True, separate=False).get(accounts_path)
        accounts_db = _u.get_accounts(whitelist=accounts)
        
        for account in accounts:
            acs = loadInStrings(clear_empty=True, separate=False).get(accounts_path)
            if account not in acs:
                continue
                
            log('fetching...', account)
            settings = loadInTxt().get(settings_path)
            settings = Struct(**settings)
            if account not in accounts_db.keys():
                accounts_db[account] = deepcopy(Payload.defoult_account_data)
                base.add(
                    table='accounts',
                    name=account,
                    assets=[],
                    tokens=accounts_db[account]['tokens']
                )
            
            tokens_last = accounts_db[account]['tokens']
            err, tokens = _u.get_tokens(scraper, account, tokens_last)
            if err:
                _log.error(err)
                
            nfts_last = accounts_db[account]['assets']
            err, assets = _u.get_nfts(scraper, account, nfts_last)
            if err:
                _log.error(err)

            resourses = _u.get_resourses(account)
            #print(resourses)
            
            if resourses['cpu_staked'] is not None:
                tokens['CPU_STAKED'] = resourses['cpu_staked']
            else:
                if 'cpu_staked' in accounts_db[account]['tokens'].keys():
                    tokens['CPU_STAKED'] = accounts_db[account]['tokens']['cpu_staked']
            
            # check tokens
            if tokens != accounts_db[account]['tokens']:
                # add new token or balance changed

                for k, v in tokens.items():
                    if k not in accounts_db[account]['tokens'].keys():
                        accounts_db[account]['tokens'][k] = v
                        text = f'<b>Account: <code>{account}</code>\nNew token: {k}: {v}</b>'
                            
                        if settings.tokens_notifications == 'true':
                            notification(text)
                        log(f'{account} new token deposit to your wallet: {k}: {v}')
                        _u.update_timer(k, round(v, 5))
                        base.edit_by('accounts', ['name', account], tokens=accounts_db[account]['tokens'])
                    
                else:
                    for k1, v1 in tokens.items():
                        if v1 != accounts_db[account]['tokens'][k1]:
                            if v1 > accounts_db[account]['tokens'][k1]:
                                log(f"{account} add balance: +{round(v1 - accounts_db[account]['tokens'][k1], 5)} {k1} [{v1} {k1}]")
                                _u.update_timer(k1, round(v1 - accounts_db[account]['tokens'][k1], 5))
                                
                                text = f"<b>Account: <code>{account}</code>\n+{round(v1 - accounts_db[account]['tokens'][k1], 5)} {k1} [{v1} {k1}]</b>"
                                
                                if round(v1 - accounts_db[account]['tokens'][k1], 6) <= 0.0001 and k1 == 'TLM':
                                    notification(
                                        f"<b>Account: {account}\n"\
                                        f"+{round(v1 - accounts_db[account]['tokens'][k1], 5)} TLM\n"\
                                        f"Seems like account was banned...</b>"
                                    )
                                accounts_db[account]['tokens'][k1] = v1
                            
                            else:    
                                log(f"{account} transfer balance: -{round(accounts_db[account]['tokens'][k1] - v1, 5)} {k1} [{v1} {k1}]")
                                text = f"<b>Account: <code>{account}</code>\n-{round(accounts_db[account]['tokens'][k1] - v1, 5)} {k1} [{v1} {k1}]</b>"
                                accounts_db[account]['tokens'][k1] = v1

                            if settings.tokens_notifications == 'true':
                                notification(text)
                                
                            base.edit_by('accounts', ['name', account], tokens=accounts_db[account]['tokens'])
        
            # check assets 
            if assets != accounts_db[account]['assets']:
                # add or delete assets
                new_assets = [str(x) for x in assets if str(x) not in accounts_db[account]['assets']]
                del_assets = [str(x) for x in accounts_db[account]['assets'] if str(x) not in assets]
                
                if new_assets:

                    text = f"<b>Account: <code>{account}</code></b>\n"
                    _price_sum = 0
                    for ass in new_assets:
                        parsed = _u.fetch_asset(ass)
                        if not parsed['success']:
                            continue
                        price = _u.get_price(parsed['template_id'], parsed['name'])
                        log(f"{account} new asset: {ass} {parsed['name']} ({price} WAX)")
                        text += f"<b>[{ass}] {parsed['name']} - {price} WAX</b>\n"
                        _price_sum += price
                    
                    text += f"\n<b>+{round(_price_sum, 2)} WAX</b>"
                        
                    if settings.nfts_notifications == 'true':
                        notification(text)
                        
                elif del_assets:
                    text = f"<b>Account: <code>{account}</code></b>\n" + '\n'.join(del_assets)
                    log(f"{account} transfer NFTs: {' '.join(del_assets)}")
                    if settings.nfts_notifications == 'true':
                        notification(text)
                
                base.edit_by('accounts', ['name', account], assets=list(assets))
            
            # check account resourses
            for _res in resourses.keys():
                if 'stake' in _res:
                    continue
                if resourses[_res] > int(settings.get(_res+'_limit')):
                    limits_notifications, is_time_res = _u.is_time_to_notif(limits_notifications, _res, account, settings['out_of_limit_timeout'])
                    if is_time_res:
                        notification(f"<b>Account {account} out of {_res.upper()} limit ({resourses[_res]}%).</b>")
                        log(f"Account {account} out of {_res.upper()} limit ({resourses[_res]}%).")
            
            if settings.timeout: 
                time.sleep(int(settings.timeout)) 
            else: 
                time.sleep(10)
                
# start thread
def start(settings, limits_notifications):
    while True:
        try:
            parser(settings, limits_notifications)
        except Exception as e:
            _log.exception("MainError: ")
            
if __name__ == '__main__':
    Thread(target=start, args=(settings, limits_notifications,)).start()
    hundlers = telegramHundlers(dp, zalupa, send_reply, _u, base, executor, settings_path, accounts_path)
    hundlers.register_all_methods()
    hundlers.run()
    
# кто прочитал тот сдохнет :)