from aiogram import types
import time

from .load_data import loadInStrings, loadInTxt, Struct
from .logger import log_handler, logger
import os

_log = logger('WAXParser_Hundlers', os.path.realpath('..') + '\\telegram_hundlers.log', 'INFO').get_logger()
log = log_handler(_log).log


def user_ids():
    path = os.path.realpath('.') + '\\settings.txt'
    settings = loadInTxt().get(path)
    ids = [int(x.strip()) for x in settings['user_id'].split(',') if x.strip() != '' and x.replace('-', '').strip().isdigit()]
    if not ids:
        return []
    return ids

def telegram_decorator(func):
    async def wrapped(self, message: types.Message):
        ids = user_ids()
        if not ids:
            _log.error('UserIDs not found :(')
        if message['from']['id'] in user_ids():
            try:
                res = await func(self, message)
                if res is not None:
                    # {'type': 'log', 'message': str}
                    # {'type': 'error', 'message': str}
                    if res['type'] == 'log':
                        log(res['message'])
                    elif res['type'] == 'error':
                        await self.send_reply(res['message'], message['from']['id'])

            except Exception as e:
                _log.exception(f"Error {func.__name__}: ")
                await message.reply(f"Error {func.__name__}: {e}")
    return wrapped
        
class telegramHundlers:
    def __init__(self, 
                 dispatcher, 
                 loop, 
                 send_reply, 
                 _u, 
                 base, 
                 executor, 
                 settings_path, 
                 accounts_path):
        self.dispatcher = dispatcher
        self.loop = loop
        self.send_reply = send_reply
        self._u = _u
        self.base = base
        self.executor = executor
        self.settings_path = settings_path
        self.accounts_path = accounts_path
    
    def reg(self, callback, commands: list):
        self.dispatcher.register_message_handler(callback, commands=commands)
        
    def register_all_methods(self):
        self.reg(self.eval_handler, commands=['eval', 'exec'])
        self.reg(self.info_handler, commands=['info'])
        self.reg(self.accs_handler, commands=['accs'])
        self.reg(self.course_handler, commands=['course', 'c'])
        self.reg(self.p_handler, commands=['p'])
        self.reg(self.onoff_handler, commands=['on', 'off'])
        self.reg(self.help_handler, commands=['help', 'h'])
        self.reg(self.i_handler, commands=['i'])
        self.reg(self.res_handler, commands=['ram', 'net', 'cpu'])
        self.reg(self.get_cost_handler, commands=['get_cost', 'gc'])
        self.reg(self.f_handler, commands=['f', 'find'])
        self.reg(self.timer_handler, commands=['timer', 't'])
        self.reg(self.sp_handler, commands=['setprice', 'sp'])
        self.reg(self.rplanetInfo_hundler, commands=['rplanet', 'rp'])
        self.reg(self.adddel_hundler, commands=['add', 'del'])
        #adddel_hundler
        
    def run(self):
        self.executor.start_polling(self.dispatcher, skip_updates=True, loop=self.loop)  

    # command /eval {some_code}
    # command /exec {some_code}
    @telegram_decorator
    async def eval_handler(self, message: types.Message):
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
        await self.send_reply(res, message['from']['id'])

    # command /info            
    @telegram_decorator
    async def info_handler(self, message: types.Message):
        whitelist = self._u.get_names(self.accounts_path)
        accounts_dumb = self._u.get_accounts(whitelist=whitelist)
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
                    
        await self.send_reply(text, message['from']['id'])

    # command /accs          
    @telegram_decorator
    async def accs_handler(self, message: types.Message):
        accounts = loadInStrings(clear_empty=True, separate=False).get(self.accounts_path)
        accounts_dumb = self._u.get_accounts(whitelist=accounts)
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
                
        await self.send_reply(text, message['from']['id'])

    # command /course        
    @telegram_decorator
    async def course_handler(self, message: types.Message):
        tlm_usd, tlm_rub = self._u.get_token_price(self._u.URL.GET_TLM_PRICE)
        wax_usd, wax_rub = self._u.get_token_price(self._u.URL.GET_WAX_PRICE)
        text = f"<b><a href=\"{self._u.URL.COINGECKO_WAX_PAGE}\">WAX</a> -> USD: {wax_usd}$</b>\n"\
                f"<b><a href=\"{self._u.URL.COINGECKO_WAX_PAGE}\">WAX</a> -> RUB: {wax_rub} руб.</b>\n"
        text += f"<b><a href=\"{self._u.URL.COINGECKO_TLM_PAGE}\">TLM</a> -> USD: {tlm_usd}$</b>\n"\
                f"<b><a href=\"{self._u.URL.COINGECKO_TLM_PAGE}\">TLM</a> -> RUB: {tlm_rub} руб.</b>\n"
        
        await self.send_reply(text, message['from']['id'])

    # command /p {wax_name}    
    @telegram_decorator
    async def p_handler(self, message: types.Message):
        if len(message["text"].split()) != 2: 
            await self.send_reply("Неверная команда.\nПример: /p namee.wam", message['from']['id'])
        else:
            c, name = message["text"].split()
            whitelist = self._u.get_names(self.accounts_path)
            accounts_dumb = self._u.get_accounts(whitelist=whitelist)
            if name not in accounts_dumb.keys():
                await self.send_reply("Нет информации.", message['from']['id'] )
            else:
                await message.reply("Загрузка...\nПодождите пока все предметы спарсятся.\nОбычно занимает от 5 секунд до 3 минут.")
                account_summ_usd = 0
                account_summ_rub = 0
                text = f"<b>Account: {name}</b>\n"\
                    f"<b>NFTs: {len(accounts_dumb[name]['assets'])}</b>\n"\
                    f"<b>Tokens:</b>\n"
                
                tlm_usd, tlm_rub = self._u.get_token_price(self._u.URL.GET_TLM_PRICE)
                wax_usd, wax_rub = self._u.get_token_price(self._u.URL.GET_WAX_PRICE)
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
                    parsed = self._u.fetch_asset(ass)
                    if not parsed['success']:
                        continue

                    if parsed['name'] not in ass_names.keys():
                        ass_names[parsed['name']] = {'count': 1, 'info': parsed}
                    else:
                        ass_names[parsed['name']]['count'] += 1
                
                for x, y in ass_names.items():
                    price = self._u.get_price( y['info']['template_id'], x )
                    if y['count'] != 1:
                        text += f"<b>{x} - {y['count']} шт. {price} WAX (~{round(price*y['count'], 2)} WAX)</b>\n"
                    else:
                        text += f"<b>{x} - {y['count']} шт. {price} WAX</b>\n"
                        
                    account_summ_usd += round(price*wax_usd, 4)
                    account_summ_rub += round(price*wax_rub, 4)
                text += "\n"
                text += f"<b>Account USD price: {round(account_summ_usd, 2)} USD</b>\n"
                text += f"<b>Account RUB price: {round(account_summ_rub, 2)} RUB</b>\n"
                
                await self.send_reply(text, message['from']['id'])

    # command /on {resourse}  
    # command /off {resourse}  
    @telegram_decorator
    async def onoff_handler(self, message: types.Message):
        settings = loadInTxt().get(self.settings_path)
        settings = Struct(**settings)
        
        if len(message['text'].split()) != 2:
            c = message['text']
            for _type in ['nfts', 'tokens', 'drops']:
                to = True if c == '/on' else False
                if settings.get(_type + "_notifications"):
                    settings.__dict__[_type + "_notifications"] = str(to).lower()
                    loadInTxt().save('settings.txt', settings.__dict__)
                    await message.reply(f'Успешно изменен тип оповещений {_type}_notifications на {str(to).lower()}.')
                else:
                    await message.reply('InvalidType: один из 2 возможных типов уведомлений nfts/tokens')
                
        else:
            c, _type = message['text'].split()
            to = True if c == '/on' else False
            if settings.get(_type + "_notifications"):
                settings.__dict__[_type + "_notifications"] = str(to).lower()
                loadInTxt().save('settings.txt', settings.__dict__)
                await message.reply(f'Успешно изменен тип оповещений {_type}_notifications на {str(to).lower()}.')
            else:
                await message.reply('InvalidType: один из 2 возможных типов уведомлений nfts/tokens')

    # command /help
    @telegram_decorator
    async def help_handler(self, message: types.Message):
        await self.send_reply(
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
            "/net число — <b>Уставить процент загрузки NET после которых присылается оповещение</b>\n"\
            "/timer start — <b>Запустить таймер для подсчета токенов</b>\n"\
            "/timer — <b>Информация о текущем таймере</b>\n"\
            "/timer clear — <b>Сбросить таймер</b>\n"\
            "/timer end — <b>Показать результат подсчета токенов и сбросить таймер</b>\n"\
            "/setprice {price} {item} — <b>Установить цену price вещи item</b>\n"\
            "/rplanet — <b>Подсчет AETHER/H</b>\n"\
            "/add xxxxx.wam — <b>Добавление аккаунта.</b>\n"\
            "/del xxxxx.wam — <b>Удаление аккаунта.</b>\n"\
            "/del all — <b>Удалить все аккаунты.</b>",
            message['from']['id'])

    # command /i {wax_name}
    @telegram_decorator
    async def i_handler(self, message: types.Message):
        c, acc = message['text'].split()
        
        whitelist = self._u.get_names(self.accounts_path)
        accounts_dumb = self._u.get_accounts(whitelist=whitelist)
        if accounts_dumb.get(acc):
            _ = 0
            _tools = []
            for asset in accounts_dumb[acc]['assets']:
                info = self._u.fetch_asset(asset)
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
            await self.send_reply(
                link,
                message['from']['id']
            )
        else:
            await message.reply('Not Found')
     
    # command /cpu {percent}
    # command /net {percent}
    # command /ram {percent}
    @telegram_decorator
    async def res_handler(self, message: types.Message):
        try:
            c, resourse = message['text'].split()
        except ValueError:
            await self.send_reply('UnpackError: command for example <code>/ram 100</code>', message['from']['id'])
            return
        _type = c[1:]
        settings = loadInTxt().get(self.settings_path)
        settings.__dict__[_type.lower() + '_limit'] = int(resourse)
        await self.send_reply(
            f'<b>Установлено оповещение при {_type.upper()} > {resourse}%</b>',    
            message['from']['id']
        )
        loadInTxt().save(self.settings_path, settings.__dict__)

            
    # command /get_cost
    @telegram_decorator
    async def get_cost_handler(self, message: types.Message):
        await message.reply('Загрузка...\nВремя вычислений зависит от количества аккаунтов, обычно около 1-3 минут.')
        whitelist = self._u.get_names(self.accounts_path)
        accounts_dumb = self._u.get_accounts(whitelist=whitelist)
        all_items = {}
        
        text = f"<b>Accounts: {len(accounts_dumb.keys())}</b>\n"
        nfts = sum([len(accounts_dumb[x]['assets']) for x in accounts_dumb.keys()])
        text += f"<b>NFTs: {nfts}</b>\n"
        text += f"<b>Tokens:</b>\n"
        
        for k, v in accounts_dumb.items():
            for asset in v['assets']:
                parsed = self._u.fetch_asset(asset)
                if not parsed['success']:
                    continue

                if all_items.get(parsed['name']):
                    all_items[parsed['name']]['count'] += 1
                else:
                    price = self._u.get_price(parsed['template_id'], parsed['name'])
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
            
        tlm_usd, tlm_rub = self._u.get_token_price(self._u.URL.GET_TLM_PRICE)
        wax_usd, wax_rub = self._u.get_token_price(self._u.URL.GET_WAX_PRICE)
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
                all_items[k]['text'] = f"<b>{k.replace('<', '〈').replace('>', '〉')}: {v['count']} шт. {v['price']} WAX ({round(v['price']*v['count'], 2)} WAX)</b>\n"
            else:
                all_items[k]['text'] = f"<b>{k.replace('<', '〈').replace('>', '〉')}: {v['count']} шт. {v['price']} WAX </b>\n"
                
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

        await self.send_reply(text, message['from']['id'])

    
    # command /i {wax_name}
    @telegram_decorator
    async def f_handler(self, message: types.Message):
        ex = message['text'][3:] if message['text'].startswith('/f') else message['text'][6:]
        if not ex:
            await message.reply('Query Not Found.')
        else:
            # {item: [accs]}
            whitelist = self._u.get_names(self.accounts_path)
            accounts_dumb = self._u.get_accounts(whitelist=whitelist)
            all_items = {}
            
            for k, v in accounts_dumb.items():
                for asset in v['assets']:
                    parsed = self._u.fetch_asset(asset)
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

                await self.send_reply(text, message['from']['id'])
            else:
                await self.send_reply('<b>Items not found</b>', message['from']['id'])

    
    @telegram_decorator
    async def timer_handler(self, message: types.Message):

        # /timer start
        # /timer 
        # /timer clear
        # /timer end
        if message['text'] == '/timer' or message['text'] == '/t':
            # return timer info
            timer = self._u.timer_to_date()
            text = f"<b>[INFO] Timer\n"\
                f"Start: {timer['strdate']}\n"\
                f"Balanses:\n"
            text += "\n".join([f"+{round(y, 2)} {x}" for x, y in timer['timer']['balances'].items()])
            text += "\n\n"
            text += f"Passed: {timer['strbetween']}</b>"
            await self.send_reply(text, message['from']['id'])

            
        else:
            # start or end
            c, cmd = message['text'].split()[:2]
            if cmd.lower() not in ['start', 'clear', 'end']:
                await message.reply('Error: Command must be start, clear or end')
            else:
                if cmd.lower() == 'start':
                    timer = self._u.get_timer()
                    if timer.get('start_timestamp') is None or timer.get('start_timestamp') == 0:
                        # create_timer
                        self._u.create_timer()
                        await message.reply('Timer created')
                    else:
                        # timer already started
                        await message.reply('Error: timer already started')

                elif cmd.lower() == 'clear':
                    # clear timer
                    self._u.zero_timer()
                    await message.reply('Timer cleared')
                    
                elif cmd.lower() == 'end':
                    timer = self._u.timer_to_date()
                    text = f"<b>[INFO] Timer\n"\
                        f"Start: {timer['strdate']}\n"\
                        f"Balanses:\n"
                    text += "\n".join([f"{round(y, 2)} {x}" for x, y in timer['timer']['balances'].items()])
                    text += "\n\n"
                    text += f"Passed: {timer['strbetween']}</b>"
                    await self.send_reply(text, message['from']['id'])

                    self._u.zero_timer()
                    await message.reply('Timer cleared')


    # command /i {wax_name}
    @telegram_decorator
    async def sp_handler(self, message: types.Message):
        if len(message.text.split()) == 1:
            await self.send_reply('Error: command for example <code>/setprice 59 Standard Drill</code>', message['from']['id'])
            return
            
        price = message.text.split()[1]
        if not price.replace('.', '').isdigit():
            await message.reply('Цена должна быть числом')
            return
        cmdlen = len(' '.join(message.text.split()[:2]))+1
        item = message.text[cmdlen:]
        inbase = self.base.get_by('prices', ['name', item], args='all')
        if not inbase:
            await message.reply(f'Вещи с названием "{item}" не найдено в базе. (Напишите /get_cost чтобы спарсить предметы')    
        else:
            self.base.edit_by('prices', ['name', item], price=price, timestamp=int(time.time()))
            await message.reply(f'Цена предмета "{item}" обновлена')


    # Check AETHER/H in RPlanet
    # /rplanet /rp
    @telegram_decorator
    async def rplanetInfo_hundler(self, message: types.Message):
        # acc: 0.0000 AETHER/H   
        # ...
        # Total: 0.0000 AETHER/H 
        accounts = loadInStrings(clear_empty=True, separate=False).get(self.accounts_path)
        await message.reply(f'Загрузка...\nВремя вычислений зависит от количества аккаунтов.\n ~{7*len(accounts)} сек.')
        text = "<b>RPlanet staking</b>\n\n"
        s = 0
        pools = self._u.get_rplanet_pools()
        for x in accounts:
            acc_info = self._u.get_rplanet_info(x, pools)
            if acc_info['total_aether_in_hour'] > 0:
                text += f"<b>{x}: {acc_info['total_aether_in_hour']} <i>AETHER/H</i></b>\n"
                s += acc_info['total_aether_in_hour']
            log(f"{x}: {acc_info['total_aether_in_hour']} AETHER/H")
        text += f"\n<b>Total: {round(s, 2)} <i>AETHER/H</i></b>"
        await self.send_reply(text, message['from']['id'])
        
    # /add /del
    @telegram_decorator
    async def adddel_hundler(self, message: types.Message):
        try:
            _, acc = message.text.split()
        except Exception as e:
            return {'type': 'error', 'message': f'fail with parse account name: {e}'}
        
            
        
        if message.text.startswith('/add'):
            l = loadInStrings(separate=False)
            accs = l.get('./db/accounts.txt')
            if acc in accs:
                return {'type': 'error', 'message': 'Account already exists'}
            else:
                accs.append(acc)
                l.save('./db/accounts.txt', accs)
                await message.reply('Account added!')
                
        elif message.text.startswith('/del'):
            l = loadInStrings(separate=False)
            accs = l.get('./db/accounts.txt')
            if acc == 'all':
                l.save('./db/accounts.txt', [])
                for a in accs:
                    self.base.edit_by('accounts', ['name', a], assets=[], tokens={})
                await message.reply('All accounts have been removed!')
                return
                
            if acc in accs:
                accs.remove(acc)
                l.save('./db/accounts.txt', accs)
                self.base.edit_by('accounts', ['name', acc], assets=[], tokens={})
                await message.reply('Account removed!')
                
            else:
                return {'type': 'error', 'message': 'Account is not exists'}
                
            
            