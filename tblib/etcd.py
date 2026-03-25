import time

import etcd


def init_etcd_service(app, name):
    host, port = app.config['ETCD_ADDR'].split(':')
    port = int(port)
    client = etcd.Client(host=host, port=port)

    prefix = app.config.get('ETCD_PREFIX', '/renaishop/services')
    key = f'{prefix}/{name}'
    value = 'http://{}:{}'.format(
        app.config['LISTENER'][0], app.config['LISTENER'][1])

    while True:
        try:
            client.write(key, value, append=True, ttl=5)
        except Exception as e:
            print('etcd service error:', e)
        time.sleep(4)


def init_etcd_client(app):
    host, port = app.config['ETCD_ADDR'].split(':')
    port = int(port)
    client = etcd.Client(host=host, port=port)

    prefix = app.config.get('ETCD_PREFIX', '/renaishop/services')

    while True:
        time.sleep(1)

        try:
            client.read(prefix, recursive=True, wait=True)
            r = client.read(prefix, recursive=True, sorted=True)
        except Exception as e:
            print('etcd client error:', e)
            continue

        d = {}
        for child in r.children:
            if child.value is None:
                continue

            name = child.key.split('/')[-2].upper()
            if d.get(name) is None:
                d[name] = []

            if child.value not in d[name]:
                d[name].append(child.value)

        print('Current service addresses:')
        print(d)

        for name, addresses in d.items():
            key = f'SERVICE_{name}'
            if key in app.config:
                app.config[key]['addresses'] = addresses