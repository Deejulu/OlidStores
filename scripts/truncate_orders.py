import pathlib
p = pathlib.Path(r'c:/Users/user/Documents/web proj/E-Stores/templates/admin_dashboard/orders/order_list.html')
lines = p.read_text().splitlines()
new = lines[:590] + ['{% endblock %}']
p.write_text("\n".join(new))
print('old', len(lines), 'new', len(new))
