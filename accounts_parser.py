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

defoult_account_data = {
    "nfts_count": 0,
    "assets": [],
    "tokens": {}
}

def get_notification_text(name: str, _type: str, body: str):
    return f"<b>Account: {name}</b>\n"\
           f"<b>Event type: {_type}</b>\n"\
           f"<i>{body}</i>\n"\
           f"<b>Link: {WAX_LINK}{name}</b>"

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
notification('Start')
def run():
    while True:
        accounts = loadInStrings(clear_empty=True, separate=False).get('accounts.txt')
        accounts_dumb = loadInJSON().get('accounts_dumb.json')
            
        for account in accounts:
            time.sleep(settings['timeout'])
            if account not in accounts_dumb.keys():
                accounts_dumb[account] = defoult_account_data
            
            token, nft = get_links(account)
            tokens_response = s.get(token).json()
            nfts_response = s.get(nft).json()
            _p = wax_token_payload.copy()
            _p['account'] = account
            wax_balance = s.post(WAX_TOKEN_URL, json=_p).json()
            
            
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
                                notification(text)
                                loadInJSON().save('accounts_dumb.json', accounts_dumb)
                
            if assets != accounts_dumb[account]['assets']:
                # add or delete assets
                _type = "change assets"
                new_assets = [str(x) for x in assets if x not in accounts_dumb[account]['assets']]
                del_assets = [str(x) for x in accounts_dumb[account]['assets'] if x not in assets]
                
                if new_assets:
                    body = "Add assets:\n" + '\n'.join(new_assets)
                    text = get_notification_text(
                        account, 
                        _type,
                        body
                    )
                    notification(text)
                else:
                    body = "Transfer/delete assets:\n" + '\n'.join(del_assets)
                    text = get_notification_text(
                        account, 
                        _type,
                        body
                    )
                    notification(text)
                    
                accounts_dumb[account]['assets'] = assets
                loadInJSON().save('accounts_dumb.json', accounts_dumb)

@dp.message_handler(commands=['info'])
async def log_handler(message: types.Message):
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
        
        