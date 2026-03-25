import os


def env(key, default):
    return os.getenv(key, default)


class BaseConfig(object):
    LISTENER = (env('TBFILE_HOST', '0.0.0.0'), int(env('TBFILE_PORT', '5040')))

    MONGO_URI = env('TBFILE_MONGO_URI', 'mongodb://localhost:27017/tbfile')

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
