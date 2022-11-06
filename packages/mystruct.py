
def return_to_Struct(func):
    def wrapper(self, *args, **kwargs):
        return Struct(**func(self, *args, **kwargs)) # requiare dict return
    return wrapper

class Struct:
    def __init__(self, **entries):
        self.__dict__.update(entries)
        for k, v in self.__dict__.items():
            if type(v) == dict:
                self.__dict__[k] = Struct(**v)

            if type(v) == list:
                self.__dict__[k] = []
                for i in range(len(v)):
                    if type(v[i]) == dict:
                        self.__dict__[k].append(Struct(**v[i]))
                    else:
                        self.__dict__[k].append(v[i])

    def __str__(self):
        return str(self.__dict__)
    
    def __repr__(self):
        return str(self.__dict__)
      
    def __getattr__(self, item):
        return None

    def __getitem__(self, item):
        return self.get(item)
    
    def __setitem__(self, item, value):
        self.__dict__[item] = value
    
    def keys(self):
        return self.__dict__.keys()

    def items(self):
        return self.__dict__.items()
    
    def get(self, key):
        return self.__dict__.get(key)
    

if __name__ == '__main__':
    # unit tests 
    dick = {"foo": "boo", "foos": {"boos": "foos", "fo": {"bo": "fo"}}, "test_lists": [{'foo': 'bar', 'bar': {'fo': 'bo'}, 'list_deep2': [{'_class': 'message'}]}]}
    dick = Struct(**dick)
    print("Unit tests")
    print("dict:", dick)
    print('dick.foo == "boo"', dick.foo == "boo")
    print('dick.foos.boos == "foos"', dick.foos.boos == "foos")
    print('dick.foos.fo.bo == "fo"', dick.foos.fo.bo == "fo")
    print('dick.test_lists[0].foo == "bar"', dick.test_lists[0].foo == "bar")
    print('dick.test_lists[0].bar.fo == "bo"', dick.test_lists[0].bar.fo == "bo")
    print('dick.test_lists[0].list_deep2[0]._class == "message"', dick.test_lists[0].list_deep2[0]._class == "message")
