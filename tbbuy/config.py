import os


def env(key, default):
    return os.getenv(key, default)


class BaseConfig(object):
    # 服务的访问地址应该为：http://0.0.0.0:5030
    LISTENER = (env('TBBUY_HOST', '0.0.0.0'), int(env('TBBUY_PORT', '5030')))

    SQLALCHEMY_DATABASE_URI = env(
        'TBBUY_DATABASE_URI',
        'mysql+mysqldb://root:12345678@localhost:3306/tbbuy?charset=utf8'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    PAGINATION_PER_PAGE = 20
    CART_PRODUCT_LIMIT = 10

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
