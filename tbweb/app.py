from flask import Flask

from . import config

import threading
from tblib.etcd import init_etcd_client

def init_handler(app):
    from .handlers import init

    init(app)

def init_redis(app):
    from tblib.redis import init
    init(app)



app = Flask(__name__)
import os
env = os.getenv("FLASK_ENV", "development")
app.config.from_object(config.configs.get(env, config.DevelopmentConfig))

init_handler(app)
init_redis(app)

threading.Thread(
    target=init_etcd_client,
    args=(app,),
    daemon=True
).start()

if __name__ == '__main__':
    from gevent import pywsgi
    # 如果是以“python -m tbweb.app”的方式运行，则页面的访问地址应该是：http://0.0.0.0:5050
    server = pywsgi.WSGIServer(app.config['LISTENER'], app)
    print('gevent WSGIServer listen on {} ...'.format(app.config['LISTENER']))
    server.serve_forever()
