import os


def env(key, default):
    return os.getenv(key, default)


class BaseConfig(object):
    # 把 tbuser 服务的地址设置为：http://0.0.0.0:5010
    LISTENER = (env('TBUSER_HOST', '0.0.0.0'), int(env('TBUSER_PORT', '5010')))

    SQLALCHEMY_DATABASE_URI = env(
        'TBUSER_DATABASE_URI',
        'mysql+mysqldb://root:12345678@localhost/tbuser?charset=utf8mb4'
    )

    # 禁止sqlalchemy追踪对象的修改并且发送信号
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    PAGINATION_PER_PAGE = 20

    ETCD_ADDR = env('ETCD_ADDR', 'localhost:2379')
    ETCD_PREFIX = env('ETCD_PREFIX', '/renaishop/services')


class DevelopmentConfig(BaseConfig):
    pass


class ProductionConfig(BaseConfig):
    pass


configs = {
    'development': DevelopmentConfig,
    'production': ProductionConfig
}
