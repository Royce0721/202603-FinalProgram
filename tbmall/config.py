import os


def env(key, default):
    return os.getenv(key, default)


class BaseConfig(object):
    # 这里涉及到数据传递，需要设置 SECRET_KEY
    SECRET_KEY = env('TBMALL_SECRET_KEY', 'dev-secret-key')

    # 设置服务监听地址：http://0.0.0.0:5020
    LISTENER = (env('TBMALL_HOST', '0.0.0.0'), int(env('TBMALL_PORT', '5020')))

    SQLALCHEMY_DATABASE_URI = env(
        'TBMALL_DATABASE_URI',
        'mysql+mysqldb://root:12345678@127.0.0.1:3306/tbmall?charset=utf8mb4'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    PAGINATION_PER_PAGE = 20

    # 👉 把 etcd 放这里（最稳）
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
