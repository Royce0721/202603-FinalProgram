from flask import Flask

from . import config

import threading
from tblib.etcd import init_etcd_service

def init_mongo(app):
    from tblib.mongo import init

    init(app)


def init_handler(app):
    from .handlers import init

    init(app)


app = Flask(__name__)
# config.from_object() 从文件中加载配置
import os

env = os.getenv("FLASK_ENV", "development")
app.config.from_object(config.configs.get(env, config.DevelopmentConfig))


# 初始化 MongoDB
init_mongo(app)
# 初始化 handler
init_handler(app)

threading.Thread(
    target=init_etcd_service,
    args=(app, 'tbfile'),
    daemon=True
).start()

if __name__ == '__main__':
    from gevent import pywsgi

    # 如果以"python -m tbfile.app"的方式运行，则tbfile服务的访问地址应该为：http://0.0.0.0:5040
    server = pywsgi.WSGIServer(app.config['LISTENER'], app)
    print('gevent WSGIServer listen on {} ...'.format(app.config['LISTENER']))
    # 开始监听http请求
    server.serve_forever()
