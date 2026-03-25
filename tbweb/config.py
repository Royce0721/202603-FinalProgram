import os


def env(key, default):
    return os.getenv(key, default)


class BaseConfig(object):
    # 用户访问的前端页面地址
    LISTENER = (env('TBWEB_HOST', '0.0.0.0'), int(env('TBWEB_PORT', '5050')))
    SECRET_KEY = env('TBWEB_SECRET_KEY', 'dev-secret-key')

    SQLALCHEMY_DATABASE_URI = env(
        'TBWEB_DATABASE_URI',
        'mysql+mysqldb://root:12345678@localhost:3306/tbweb?charset=utf8'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SITE_NAME = '仁爱购物网'
    PAGINATION_PER_PAGE = 20

    DOMAIN_TBFILE = env('DOMAIN_TBFILE', 'http://localhost:5040')

    SERVICE_TBBUY = {
        'addresses': [v.strip() for v in env('SERVICE_TBBUY_ADDRESSES', 'http://localhost:5030').split(',') if v.strip()],
    }
    SERVICE_TBFILE = {
        'addresses': [v.strip() for v in env('SERVICE_TBFILE_ADDRESSES', 'http://localhost:5040').split(',') if v.strip()],
    }
    SERVICE_TBMALL = {
        'addresses': [v.strip() for v in env('SERVICE_TBMALL_ADDRESSES', 'http://localhost:5020').split(',') if v.strip()],
    }
    SERVICE_TBUSER = {
        'addresses': [v.strip() for v in env('SERVICE_TBUSER_ADDRESSES', 'http://localhost:5010').split(',') if v.strip()],
    }

    REDIS_URL = env('REDIS_URL', 'redis://localhost:6379/0')

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
