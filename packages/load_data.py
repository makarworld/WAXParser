# module for load data in json, yami, txt
import os
import json

"""
# Usage: example
loadInStrings:
    ;; loadInStrings().get('test.txt') 
    ;; // return list with your txt data.

loadInJSON: 
    ;; loadInJSON().get('test.txt') 
    ;; // return dict with your json data.

"""
class Struct:
    def __init__(self, **entries):
        self.__dict__.update(entries)
        for k, v in self.__dict__.items():
            if type(v) == dict:
                self.__dict__[k].update(v)
                
    def __getattr__(self, item):
        return None

    def __getitem__(self, item):
        return self.get(item)
    
    def __setitem__(self, item, value):
        self.__dict__[item] = value
    
    def get(self, key):
        return self.__dict__.get(key)

def load_settings(settings):
    struct = Struct(**settings)
    types = {
        'timeout': [int, 30],
        'cpu_limit': [int, 100],
        'net_limit': [int, 100],
        'ram_limit': [int, 100],
        'out_of_limit_timeout': [int, 3600],
        'drops_notification_timeout': [int, 3600],
        'refresh_price': [int, 3600]
    }
    
    for k,v in types.items():
        if k in struct.__dict__.keys():
            try:
                struct[k] = v[0](struct[k])
            except:
                struct[k] = v[1]
        else:
            struct[k] = v[1]
    return struct

def check_exists(name: str, create: bool = False, create_data: str = ''):
        if not os.path.exists(name):
            if create:
                with open(name, 'w') as f:
                    f.write(create_data)
            return False
        return True
            
class LoadObj:
    def __init__(self, 
                 create: bool = True,
                 idnore_errors: bool = True, 
                 separate: bool = True,
                 separator: str = ':',
                 clear_empty: bool = True,
                 version: int = 1):
        
        self.create, self.idnore_errors, self.separate, self.separator, self.clear_empty, self.version = create, idnore_errors, separate, separator, clear_empty, version
    
    def get(self, name: str, create_data: str=''):
        if not check_exists(name, self.create, create_data=create_data) and not self.idnore_errors:
            raise ValueError("Wrong filename!")
            
            
class loadInJSON(LoadObj):
    def get(self, name: str, create_data='{}'):
        super().get(name, create_data)
        with open(name, 'r', encoding='utf-8') as f:
            return json.loads(f.read())
    
    def save(self, name: str, data: dict, indent: int=4):
        with open(name, 'w', encoding='utf-8') as f:
            return json.dump(data, f, indent=indent)

        
class loadInStrings(LoadObj):

    def get(self, name: str):
        super().get(name)
        sep = super().__dict__["separate"]
        septor = super().__dict__["separator"]
        
        with open(name, 'r', encoding='utf-8') as f:
            if super().__dict__["clear_empty"]:
                data = [x.replace('\n', '') for x in f.readlines() if x.replace('\n', '') != '']
            else:
                data = [x.replace('\n', '') for x in f.readlines()]   
            
        if sep:
            data = [x.split(septor) for x in data]
            
        return data

    def save(self, name: str, data: list):
        with open(name, 'w', encoding='utf-8') as f:
            f.write('\n'.join(data))

class loadInYami:
    pass


class loadInTxt(LoadObj):
    # txt example:
    # [login]: {logind_data}
    # [password]: {password_data}

    def get(self, name: str):
        super().get(name)
        
        with open(name, 'r', encoding='utf-8') as f:
            
            if super().__dict__['clear_empty']:
                data = [x.replace('\n', '') for x in f.readlines() if x.replace('\n', '') != '']
            else:
                data = [x.replace('\n', '') for x in f.readlines()]
        
        if super().__dict__['version'] == 1:
            res = {}
            for x in data:
                key = x.split(super().__dict__['separator'])[0]
                if key == '' or len(x.split(super().__dict__['separator'])) < 2:
                    continue
                value = x[len(key)+1:].strip()
                res[key] = value
            return res
        
        elif super().__dict__['version'] == 2:
            res = {}
            for r in data:
                if "#" in r:
                    res[r.replace("#", "").strip()] = {}
                    
            for r in data:
                if r.replace("#", "").strip() in res:
                    for k in data[data.index(r):]:
                        while not "#" in k:
                            key = k.split(super().__dict__['separator'])[0]
                            if key == '' or len(k.split(super().__dict__['separator'])) < 2:
                                continue
                            value = k[len(key)+1:].strip()
                            res[r.replace("#", "").strip()][key] = value
            return res
        
        elif super().__dict__['version'] == 3:
            res = {}
            for x in data:
                _type = x.split(' ')[0]
                key = x.split(' ')[1].split(super().__dict__['separator'])[0]
                if key == '' or len(x.split(super().__dict__['separator'])) < 2:
                    continue
                value = x[len(_type + ' ' + key)+1:].strip()
                res[key] = eval(f"{_type}('{value}')")
            return res


    def save(self, name, _dict):

        if super().__dict__['version'] == 1:
            s = super().__dict__['separator']
            with open(name, 'w', encoding='utf-8') as f:
                f.write(
                    '\n'.join([f"{x}{s} {y}" for x, y in _dict.items()])
                )
        if super().__dict__['version'] == 2:
            text = ""
            for key in _dict:
                text += "# " + key + "\n"
                if type(_dict[key]) == dict:
                    text += '\n'.join([f"{x}{super().__dict__['separator']} {y}" for x, y in _dict.items()])
                else:
                    text += str(_dict[key])
                text += '\n\n'
            
            with open(name, 'w', encoding='utf-8') as f:
                f.write(text)
        return True


def to_dict(string: str) -> dict:
    replaces = [
        ["'", '"'],
        ["False", 'false'],
        ["True", 'true'],
        ['None', 'null']
    ]
    for rep in replaces:
        string = string.replace(rep[0], rep[1])
    return json.loads(string)


def to_bool(string: str) -> bool:
    if string == "True":
        return True 
    elif string == "False":
        return False
    else:
        return bool(string)

if __name__ == '__main__':
    t = {'abs': 24, 'time': -1, 'sd': {'get': True}}
    s = Struct(**t)
    print(s.__dict__)

    #l = loadInTxt()
    #print(l.get('test.txt'))