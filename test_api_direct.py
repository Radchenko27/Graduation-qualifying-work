import requests

# Логин
r = requests.post('http://127.0.0.1:8000/api/users/login', json={'username': 'admin', 'password': 'admin'})
if r.status_code == 200:
    sk = r.json().get('session_key')
    h = {'X-Session-Key': sk}
    
    # Список проектов
    r2 = requests.get('http://127.0.0.1:8000/api/projects/', headers=h)
    print(f'GET /api/projects/: {r2.status_code}')
    if r2.status_code == 200:
        ps = r2.json()
        pids = [p['id'] for p in ps]
        print(f'Projects IDs: {pids}')
    
    # Один проект
    if ps:
        pid = ps[0]['id']
        r3 = requests.get(f'http://127.0.0.1:8000/api/projects/{pid}', headers=h)
        print(f'GET /api/projects/{pid}: {r3.status_code}')
        if r3.status_code == 200:
            p = r3.json()
            print(f'Project: {p}')
        else:
            print(f'Error: {r3.text}')
else:
    print(f'Login failed: {r.status_code}')
