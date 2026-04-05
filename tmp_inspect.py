with open('orders/views.py','rb') as f:
    lines = f.readlines()
for i in range(156,168):
    print(i+1, lines[i])
