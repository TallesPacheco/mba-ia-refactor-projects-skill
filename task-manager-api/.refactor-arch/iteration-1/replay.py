"""Repete as requisições de baseline.md e imprime status + shape. Uso: replay.py <base_url> [admin_token]"""
import json, sys, urllib.request, urllib.error

BASE = sys.argv[1]
TOKEN = sys.argv[2] if len(sys.argv) > 2 else None

def req(method, path, body=None, raw=None, ctype=True, admin=False):
    data = None
    headers = {}
    if body is not None or raw is not None:
        data = (raw if raw is not None else json.dumps(body)).encode()
        if ctype:
            headers['Content-Type'] = 'application/json'
    if admin and TOKEN:
        headers['X-Admin-Token'] = TOKEN
    r = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        resp = urllib.request.urlopen(r); status = resp.status; text = resp.read().decode()
    except urllib.error.HTTPError as e:
        status = e.code; text = e.read().decode()
    try:
        j = json.loads(text)
    except Exception:
        return status, 'NON-JSON', text[:60]
    return status, j, None

def shape(j):
    if isinstance(j, list):
        return f"list[{len(j)}] of {sorted(j[0].keys()) if j and isinstance(j[0], dict) else ''}"
    if isinstance(j, dict):
        return '{' + ','.join(sorted(j.keys())) + '}'
    return type(j).__name__

# (n, method, path, body, kwargs, expected_baseline_status)
CASES = [
 (1,'GET','/',None,{},200),(2,'GET','/health',None,{},200),(3,'GET','/tasks',None,{},200),
 (4,'GET','/tasks/1',None,{},200),(5,'GET','/tasks/999',None,{},404),
 (6,'GET','/tasks/search?q=API',None,{},200),(7,'GET','/tasks/search?status=pending&priority=1',None,{},200),
 (8,'GET','/tasks/search?priority=abc',None,{},500),(9,'GET','/tasks/stats',None,{},200),
 (10,'GET','/users',None,{},200),(11,'GET','/users/1',None,{},200),(12,'GET','/users/999',None,{},404),
 (13,'GET','/users/1/tasks',None,{},200),(14,'GET','/users/999/tasks',None,{},404),
 (15,'GET','/reports/summary',None,{},200),(16,'GET','/reports/user/1',None,{},200),(17,'GET','/reports/user/999',None,{},404),
 (18,'GET','/categories',None,{},200),
 (19,'POST','/login',{"email":"joao@email.com","password":"1234"},{},200),
 (20,'POST','/login',{"email":"joao@email.com","password":"x"},{},401),
 (21,'POST','/login',{},{},400),
 (22,'POST','/tasks',{"title":"Nova task baseline","description":"d","priority":2,"user_id":1,"category_id":1,"due_date":"2026-12-01","tags":["a","b"]},{},201),
 (23,'POST','/tasks',{"title":"ab"},{},400),
 (24,'POST','/tasks',{"title":"Prioridade str","priority":"2"},{},500),
 (25,'POST','/tasks',{"title":"user ruim","user_id":999},{},404),
 (26,'POST','/users',{"name":"Ana","email":"ana@email.com","password":"segredo"},{},201),
 (27,'POST','/users',{"name":"Ana","email":"ana@email.com","password":"segredo"},{},409),
 (28,'POST','/users',{"name":"X","email":"bad","password":"segredo"},{},400),
 (29,'POST','/categories',{"name":"QA","color":"#ffffff"},{},201),
 (30,'POST','/categories',{},{},400),
 (31,'PUT','/tasks/11',{"status":"done","title":"Nova task atualizada"},{},200),
 (32,'PUT','/tasks/11',{"status":"xx"},{},400),(33,'PUT','/tasks/999',{"status":"done"},{},404),
 (34,'PUT','/users/4',{"name":"Ana Maria","role":"manager"},{'admin':True},200),
 (35,'PUT','/users/4',{"role":"root"},{},400),(36,'PUT','/users/999',{"name":"x"},{},404),
 (37,'PUT','/categories/5',{"name":"QA2"},{},200),(38,'PUT','/categories/999',{"name":"x"},{},404),
 (39,'PUT','/categories/5',None,{'raw':'{"name":"QA2"}','ctype':False},415),
 (40,'PUT','/categories/5',None,{'raw':'null'},500),
 (41,'POST','/tasks',{"title":"Task da Ana","user_id":4},{},201),
 (42,'DELETE','/tasks/11',None,{'admin':True},200),(43,'DELETE','/tasks/999',None,{'admin':True},404),
 (44,'DELETE','/users/4',None,{'admin':True},200),(440,'GET','/tasks/12',None,{},404),
 (45,'DELETE','/users/999',None,{'admin':True},404),
 (46,'DELETE','/categories/5',None,{'admin':True},200),(47,'DELETE','/categories/999',None,{'admin':True},404),
 (48,'DELETE','/categories/4',None,{'admin':True},200),(480,'GET','/tasks/4',None,{},200),
]
for n, m, p, b, kw, exp in CASES:
    s, j, raw = req(m, p, b, **kw)
    extra = ''
    if isinstance(j, dict) and 'error' in j: extra = j['error']
    if isinstance(j, dict) and 'message' in j and len(j) == 1: extra = j['message']
    if n == 480: extra = f"category_id={j.get('category_id')}"
    if n in (11, 19, 26, 34): extra = 'password presente' if ('password' in j or 'password' in j.get('user', {})) else 'sem password'
    flag = 'OK ' if s == exp else 'DIF'
    print(f"{flag} #{n:<3} {m:6} {p:42} base={exp} now={s} {shape(j) if raw is None else 'NON-JSON '+raw} {extra}")
