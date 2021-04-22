import logging
from datetime import datetime

class logger:
    def __init__(self, name: str, file: str='teleapp.log', level: str='INFO'):
        self.name = name
        self.level = level
        self.file = file
    
    def get_logger(self):
        self.log = logging.getLogger(self.name)
        _level = eval(f"logging.{self.level}")
        logging.basicConfig(level=_level)
        if self.file is not None:
            formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', 
                                        '%m-%d-%Y %H:%M:%S')

            file_handler = logging.FileHandler(self.file)
            file_handler.setLevel(_level)
            file_handler.setFormatter(formatter)
            self.log.addHandler(file_handler)
        return self.log

class log_handler:
    def __init__(self, logger: logging.Logger):
        self._log = logger
    
    def log(self, *args,  w=True):
        text = ' '.join([str(a) for a in args])
        if w == True:
            self._log.info(text)
        else:
            path = self._log.handlers[0].__dict__['baseFilename']
            if not text.endswith('\n'):
                text += '\n'
            text = datetime.now().strftime("%m-%d-%Y %H:%M:%S") + ' | INFO | ' + text
            with open(path, 'a', encoding='utf-8') as f:
                f.write(text)
    