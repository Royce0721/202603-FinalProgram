
from flask import Flask

from . import config

import threading
from tblib.etcd import init_etcd_service


def init_model(app):
    from importlib import import_module
    from tblib import model

    model.init(app)
    # 等价于: from . import models
    import_module('.models', __package__)
    with app.app_context():
        model.db.create_all()


def init_handler(app):
    from .handlers import init

    init(app)


app = Flask(__name__)
import os

env = os.getenv('FLASK_ENV', 'development')
app.config.from_object(config.configs.get(env))

init_model(app)

init_handler(app)

threading.Thread(
    target=init_etcd_service,
    args=(app, 'tbbuy'),
    daemon=True
).start()

if __name__ == '__main__':
    from gevent import pywsgi
    # 如果以“python -m tbbuy.app”的方式运行服务，服务的监听地址为：http:0.0.0.0:5030
    server = pywsgi.WSGIServer(app.config['LISTENER'], app)
    print('gevent WSGIServer listen on {} ...'.format(app.config['LISTENER']))
    server.serve_forever()
