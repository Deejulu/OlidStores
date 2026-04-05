import ast
import sys
source=open('orders/views.py','r',encoding='utf-8').read()
try:
    ast.parse(source)
    print('AST OK')
except SyntaxError as e:
    print('SyntaxError:', e.msg, 'at', e.lineno, e.offset)
    for i, line in enumerate(source.splitlines(), start=1):
        if i>=e.lineno-3 and i<=e.lineno+3:
            print(i, repr(line))
    sys.exit(1)
