from pathlib import Path
path = Path(r'c:\Users\user\Documents\web proj\E-Stores\templates\base.html')
text = path.read_text(encoding='utf-8')
start = text.find('<style>')
end = text.find('</style>', start)
print('style start', start, 'end', end)
if start == -1 or end == -1:
    print('style not found')
    raise SystemExit(0)
style = text[start+7:end]
ob = style.count('{')
cb = style.count('}')
print('braces', ob, cb, 'diff', ob-cb)
print('comments', style.count('/*'), style.count('*/'))
