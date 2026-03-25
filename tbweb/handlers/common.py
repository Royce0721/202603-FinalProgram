from flask import Blueprint, current_app, render_template
from tblib.redis import redis

from ..services import TbMall
from .shop import full_shop_info

common = Blueprint('common', __name__, url_prefix='/')


@common.route('')
def index():
    # 推荐商品
    #product_ids = [int(x) for x in redis.lrange('recommend.products', 0, 3)]
    product_ids = [2,3,4]


    products = []
    if product_ids:
        resp = TbMall(current_app).get_json('/products/infos', params={
            'ids': ','.join([str(v) for v in product_ids]),
        })

        for product_id in product_ids:
            product = resp['data']['products'].get(str(product_id))
            if product is not None:
                products.append(product)

    # 推荐店铺
    #shop_ids = [int(x) for x in redis.lrange('recommend.shops', 0, 2)]
    shop_ids = [5,6]

    shops = []
    if shop_ids:
        resp = TbMall(current_app).get_json('/shops/infos', params={
            'ids': ','.join([str(v) for v in shop_ids]),
        })

        for shop_id in shop_ids:
            shop = resp['data']['shops'].get(str(shop_id))
            if shop is not None:
                shops.append(shop)

        shops = full_shop_info(shops)

    return render_template('index.html', products=products, shops=shops)