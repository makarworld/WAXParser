# This Python file uses the following encoding: utf-8

import sqlite3
import logging
import logging.config

log = logging.getLogger("SQLite")

def ensure_connection(func):

    def inner(*args, **kwargs):
        if 'filename' in args[0].__dict__.keys():
            file = args[0].filename
        else:
            try:
                file = args[-1]
            except:
                file = kwargs['filename']    
        
        with sqlite3.connect(file) as connection:
            cursor = connection.cursor()
            res = func(*args, cursor=cursor, **kwargs)
            connection.commit()
        return res
    return inner
    

class baseUniversal():
    @ensure_connection
    def __init__(self, filename, logname="database", cursor=None):
        self.filename = filename
        self.log = logging.getLogger(logname)
        self.tables = {
                'assets': [
                    'asset_id',
                    'name',
                    'rarity',
                    'contract',
                    'collection_name',
                    'template_id'
                ],
                'accounts': [
                    'name',
                    'assets',
                    'tokens'
                ],
                'prices': [
                    'name',
                    'template_id',
                    'price',
                    'timestamp'
                ]
            }

        for table in self.tables:
            self.create(
                table=table,
                columns=self.tables[table]
            )
    @ensure_connection
    def create(self, table: str, columns: list, types: str="TEXT", cursor=None):
        command = f'CREATE TABLE IF NOT EXISTS {table} ( '
        columns = [column.upper()+" "+types for column in columns]
        command += ', '.join(columns) + ' )'
        log.debug(command)
        r = cursor.execute(command)

    @ensure_connection
    def get_table(self, table, cursor=None):
        log.debug('SELECT * FROM {}'.format(table))
        table_ = cursor.execute('SELECT * FROM {}'.format(table)).fetchall()
        response = []
        for item in table_:
            res = {}
            for i, tt in enumerate(self.tables[table]):
                res[self.tables[table][i]] = item[i]
            response.append(res)
        return response

    @ensure_connection
    def edit_by(self, table: str, edit_by: list, cursor=None, **kwargs): # base.edit_by(table, ename=values, **kwargs)
        command = 'UPDATE {} SET '.format(table)
        list_kwargs = []

        for kwarg in kwargs:
            list_kwargs.append(str(kwargs[kwarg]))
            command += kwarg + " = ?, "
        else:
            command = command[:-2]
        
        command += " WHERE "
 
        if type(edit_by[0]) == list or type(edit_by[0]) == tuple:
            for k in edit_by[0]:
                command += k + ' = ? AND '
            else:
                command = command[:-5]
        else:
            command += edit_by[0] + " = ?"

            
        if type(edit_by[1]) == list or type(edit_by[1]) == tuple:
            [list_kwargs.append(c) for c in edit_by[1]]
        else:
            list_kwargs.append(str(edit_by[1]))
        
        log.debug(str(command) + ' ' + str(list_kwargs))

        cursor.execute(command, list_kwargs)

    @ensure_connection
    def get_by(self, table: str, get_by: list, args: list, order_by: str=None, cursor=None):
        if len(get_by[0]) == 0:
            return {table: []} 
        
        command = 'SELECT '
        list_args = []
        response = {}
        response[table] = []

        if args == 'all':
            args = self.tables[table]

        for arg in args:
            command += arg + ", "
        else:
            command = command[:-2]
            
        command += f" FROM {table} WHERE "
        if type(get_by[0]) == list or type(get_by[0]) == tuple:
            for x in get_by[0]:
                if not '>' in x \
                 and not '<' in x \
                 and not 'IS' in x \
                 and not 'NOT' in x:
                    command += x + " = ? AND "
                else:
                    command += x + " ? AND "
            else:
                command = command[:-5]
        else:
            if not '>' in get_by[0] \
             and not '<' in get_by[0] \
             and not 'IS' in get_by[0] \
             and not 'NOT' in get_by[0]:
                command += get_by[0] + ' = ?'
            else:
                command += get_by[0] + ' ?'
                
            
        if type(get_by[1]) == list or type(get_by[1]) == tuple:
            [list_args.append(str(x)) for x in get_by[1]]
        else: 
            list_args.append(str(get_by[1]))
            
        if order_by:
            command += " ORDER BY " + order_by
            
        log.debug(str(command) + ' ' + str(list_args))
        r = cursor.execute(command, list_args).fetchall()
        for res in r:
            resp = {}
            for item in args:
                resp[item] = res[args.index(item)]
            response[table].append(resp)

        return response[table]

    @ensure_connection
    def add(self, table: str, cursor=None, **kwargs):
        kwargs_list = [[str(a), str(kwargs[a])] for a in kwargs]
        kwargs_name = [x[0] for x in kwargs_list]
        list_args = []
        
        command = f'INSERT INTO {table} ( '
        command += ', '.join(self.tables[table])
        command += " ) VALUES ( "
        command += ', '.join(list('?'*len(self.tables[table]))) + '?'
        command = command[:-1] + " )"
        
        for arg in self.tables[table]:
            if arg in kwargs_name:
                list_args.append(str(kwargs[arg.lower()]))
            else:
                list_args.append(None)
        log.debug(str(command) + ' ' + str(list_args))
        cursor.execute(command, list_args)
        
        return True
    
    @ensure_connection
    def add_json(self, table: str, payload: dict, cursor=None):  
        self.add(
            table=table,
            **payload
        )
    
    @ensure_connection
    def execute(self, command, args=None, cursor=None):
        log.debug(str(command) + ' ' + str(args))
        if args:
            cursor.execute(command, args)
        else:
            cursor.execute(command)
            
    
if __name__ == "__main__":
    base = baseUniversal('test.db')
    base.create(
        'test',
        ['test1', 'test2']
    )
    base.add(
        'test',
        test1='name',
        test2='value'
    )
    base.get_by('test', ['test1', 'name'], args='all')
    base.edit_by('test', ['test1', 'name'], test1='edited_name')
    
