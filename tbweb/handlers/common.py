import random

from flask import Blueprint, current_app, render_template
from tblib.redis import redis

from ..services import TbBuy, TbMall
from .shop import full_shop_info

common = Blueprint('common', __name__, url_prefix='/')


def pick_random_ids(ids, limit=4):
    if len(ids) <= limit:
        return ids
    return random.sample(ids, limit)


@common.route('')
def index():
    product_total_resp = TbMall(current_app).get_json('/products', params={
        'limit': 1,
        'offset': 0,
    }, check_code=False)
    shop_total_resp = TbMall(current_app).get_json('/shops', params={
        'limit': 1,
        'offset': 0,
    }, check_code=False)
    order_total_resp = TbBuy(current_app).get_json('/orders', params={
        'limit': 1,
        'offset': 0,
    }, check_code=False)

    product_total = product_total_resp.get('data', {}).get('total', 0)
    shop_total = shop_total_resp.get('data', {}).get('total', 0)
    order_total = order_total_resp.get('data', {}).get('total', 0)

    # 推荐商品
    product_ids = []
    for raw_id in redis.lrange('recommend.products', 0, -1):
        try:
            product_ids.append(int(raw_id))
        except (TypeError, ValueError):
            continue
    if not product_ids:
        product_ids = [2, 3, 4]
    product_ids = pick_random_ids(product_ids, limit=4)

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
    shop_ids = pick_random_ids(shop_ids, limit=4)

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

    return render_template(
        'index.html',
        products=products,
        shops=shops,
        product_total=product_total,
        shop_total=shop_total,
        order_total=order_total,
    )
