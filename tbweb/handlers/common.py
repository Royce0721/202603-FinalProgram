from flask import Blueprint, current_app, render_template
from tblib.redis import redis

from ..services import TbMall
from .shop import full_shop_info

common = Blueprint('common', __name__, url_prefix='/')


@common.route('')
def index():
    # 推荐商品
    product_ids = []
    for raw_id in redis.lrange('recommend.products', 0, -1):
        try:
            product_ids.append(int(raw_id))
        except (TypeError, ValueError):
            continue
    if not product_ids:
        product_ids = [2, 3, 4]

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
    shop_ids = []
    for raw_id in redis.lrange('recommend.shops', 0, -1):
        try:
            shop_ids.append(int(raw_id))
        except (TypeError, ValueError):
            continue
    if not shop_ids:
        shop_ids = [5, 6]

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
