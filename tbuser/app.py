from flask import Flask

from . import config

import threading
from tblib.etcd import init_etcd_service

def init_model(app):
    from importlib import import_module
    from tblib import model

    model.init(app)

    # 这个等价于：from . import models
    import_module('.models', __package__)


def init_handler(app):
    from .handlers import init

    init(app)


app = Flask(__name__)
import os

env = os.getenv("FLASK_ENV", "development")
app.config.from_object(config.configs.get(env, config.DevelopmentConfig))


init_model(app)

init_handler(app)

threading.Thread(
    target=init_etcd_service,
    args=(app, 'tbuser'),
    daemon=True
).start()

if __name__ == '__main__':
    from gevent import pywsgi

    # 如果是以“python -m tbuser.app”的方式运行，就应当访问地址：http://0.0.0.0:5010
    server = pywsgi.WSGIServer(app.config['LISTENER'], app)
    print('gevent WSGIServer listen on {} ...'.format(app.config['LISTENER']))
    server.serve_forever()
