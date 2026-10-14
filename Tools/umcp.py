"""Tiny client for the project's Unity MCP server (http://127.0.0.1:8080/mcp, streamable HTTP, SSE replies).
usage:  python umcp.py tools                      list tool names
        python umcp.py tool <name> '<json args>'  call a tool
        python umcp.py res <uri>                  read a resource (mcpforunity://...)
        python umcp.py code <file.cs>             run a C# method body inside the Unity Editor (return a string)
        python umcp.py reslist                    list resources"""
import json
import os
import sys
import urllib.request

URL = 'http://127.0.0.1:8080/mcp'
HERE = os.path.dirname(os.path.abspath(__file__))
SESS = os.path.join(HERE, 'umcp_session.txt')
HDR = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream'}


def _post(payload, sid=None, timeout=300):
    h = dict(HDR)
    if sid:
        h['Mcp-Session-Id'] = sid
    req = urllib.request.Request(URL, data=json.dumps(payload).encode(), headers=h, method='POST')
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read().decode('utf-8', 'replace')
        return r.headers.get('mcp-session-id'), body


def _msgs(body):
    out = []
    for line in body.splitlines():
        if line.startswith('data:'):
            try:
                out.append(json.loads(line[5:].strip()))
            except Exception:
                pass
    if not out and body.strip().startswith('{'):
        out.append(json.loads(body))
    return out


def session(force=False):
    if not force and os.path.exists(SESS):
        return open(SESS).read().strip()
    sid, _ = _post({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
                    'params': {'protocolVersion': '2025-03-26', 'capabilities': {}, 'clientInfo': {'name': 'claude-code-bash', 'version': '1'}}})
    _post({'jsonrpc': '2.0', 'method': 'notifications/initialized'}, sid)
    open(SESS, 'w').write(sid)
    return sid


def rpc(method, params=None, rid=2):
    sid = session()
    try:
        _, body = _post({'jsonrpc': '2.0', 'id': rid, 'method': method, 'params': params or {}}, sid)
    except Exception as e:                      # stale session -> new one
        sid = session(force=True)
        _, body = _post({'jsonrpc': '2.0', 'id': rid, 'method': method, 'params': params or {}}, sid)
    for m in _msgs(body):
        if m.get('id') == rid:
            return m
    return {'raw': body[:2000]}


def show(res):
    if 'error' in res:
        print('ERROR', json.dumps(res['error'])[:3000])
        return
    r = res.get('result', res)
    if isinstance(r, dict) and 'content' in r:
        for c in r['content']:
            if c.get('type') == 'text':
                print(c['text'])
            else:
                print('[%s content]' % c.get('type'))
        if r.get('isError'):
            print('(isError)')
    elif isinstance(r, dict) and 'contents' in r:
        for c in r['contents']:
            print(c.get('text', '')[:20000])
    else:
        print(json.dumps(r, indent=1)[:20000])


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a:
        print(__doc__)
    elif a[0] == 'tools':
        res = rpc('tools/list')
        for t in res.get('result', {}).get('tools', []):
            print(t['name'], '-', (t.get('description') or '').split('\n')[0][:110])
    elif a[0] == 'reslist':
        res = rpc('resources/list')
        for t in res.get('result', {}).get('resources', []):
            print(t['uri'], '-', t.get('name'))
    elif a[0] == 'tool':
        show(rpc('tools/call', {'name': a[1], 'arguments': json.loads(a[2]) if len(a) > 2 else {}}))
    elif a[0] == 'code':                       # python umcp.py code file.cs   (C# method body, use 'return')
        show(rpc('tools/call', {'name': 'execute_code', 'arguments': {'action': 'execute', 'code': open(a[1], encoding='utf-8').read(), 'safety_checks': False}}))
    elif a[0] == 'res':
        show(rpc('resources/read', {'uri': a[1]}))
