f=open('orders/views.py','rb')
lines=f.readlines()
for i in range(90,176):
    print(i+1, repr(lines[i]))
f.close()