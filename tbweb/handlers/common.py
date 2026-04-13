from flask import Blueprint, current_app, render_template
from flask_login import current_user

from ..services import TbBuy, TbMall
from .sales import enrich_products_with_sales
from .shop import full_shop_info

common = Blueprint('common', __name__, url_prefix='/')


def fetch_products_by_ids(product_ids):
    if not product_ids:
        return []
    resp = TbMall(current_app).get_json('/products/infos', params={
        'ids': ','.join([str(v) for v in product_ids]),
    }, check_code=False)
    products = []
    for product_id in product_ids:
        product = resp.get('data', {}).get('products', {}).get(str(product_id))
        if product is not None:
            products.append(product)
    return products


def fetch_product_sales_rows(limit=20, user_id=None):
    params = {'limit': limit}
    if user_id is not None:
        params['user_id'] = user_id
    resp = TbBuy(current_app).get_json('/order_products/sales', params=params, check_code=False)
    return resp.get('data', {}).get('product_sales', [])


def fetch_hot_product_ids(limit=4, user_id=None):
    rows = fetch_product_sales_rows(limit=limit, user_id=user_id)
    product_ids = [row['product_id'] for row in rows if row.get('product_id')]
    if product_ids:
        return product_ids

    resp = TbMall(current_app).get_json('/products', params={
        'limit': limit,
        'offset': 0,
    }, check_code=False)
    return [product['id'] for product in resp.get('data', {}).get('products', [])]


def rank_categories_for_user(user_id):
    sales_rows = fetch_product_sales_rows(limit=100, user_id=user_id)
    history_ids = [row['product_id'] for row in sales_rows if row.get('product_id')]
    products = fetch_products_by_ids(history_ids)
    product_sales = {
        int(row['product_id']): int(row.get('sales') or 0)
        for row in sales_rows
        if row.get('product_id') is not None
    }
    category_sales = {}
    for product in products:
        category = (product.get('category') or '').strip()
        if not category:
            continue
        product_id = int(product.get('id'))
        category_sales[category] = category_sales.get(category, 0) + product_sales.get(product_id, 0)
    return [name for name, _count in sorted(category_sales.items(), key=lambda item: (-item[1], item[0]))]


def fetch_personalized_products(user_id, limit=4):
    categories = rank_categories_for_user(user_id)
    if not categories:
        return [], []

    hot_ids = set(fetch_hot_product_ids(limit=50))
    selected = []
    selected_ids = set()

    for category in categories:
        resp = TbMall(current_app).get_json('/products', params={
            'category': category,
            'limit': 20,
            'offset': 0,
        }, check_code=False)
        products = resp.get('data', {}).get('products', [])
        products.sort(key=lambda item: (item['id'] not in hot_ids, -item['id']))
        for product in products:
            product_id = int(product['id'])
            if product_id in selected_ids:
                continue
            selected.append(product)
            selected_ids.add(product_id)
            if len(selected) >= limit:
                return selected, categories

    return selected, categories


def fetch_hot_shops(limit=4):
    sales_rows = fetch_product_sales_rows(limit=100)
    product_ids = [row['product_id'] for row in sales_rows if row.get('product_id')]
    products = fetch_products_by_ids(product_ids)
    product_map = {int(product['id']): product for product in products}
    shop_sales = {}
    for row in sales_rows:
        product_id = row.get('product_id')
        if product_id is None:
            continue
        product = product_map.get(int(product_id))
        if product is None:
            continue
        shop = product.get('shop') or {}
        shop_id = shop.get('id')
        if shop_id is None:
            continue
        shop_sales[shop_id] = shop_sales.get(shop_id, 0) + int(row.get('sales') or 0)

    hot_shop_ids = [shop_id for shop_id, _ in sorted(shop_sales.items(), key=lambda item: (-item[1], item[0]))[:limit]]
    if not hot_shop_ids:
        resp = TbMall(current_app).get_json('/shops', params={'limit': limit, 'offset': 0}, check_code=False)
        return full_shop_info(resp.get('data', {}).get('shops', []))

    resp = TbMall(current_app).get_json('/shops/infos', params={
        'ids': ','.join([str(v) for v in hot_shop_ids]),
    }, check_code=False)
    shops = []
    for shop_id in hot_shop_ids:
        shop = resp.get('data', {}).get('shops', {}).get(str(shop_id))
        if shop is not None:
            shops.append(shop)
    return full_shop_info(shops)


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

    recommendation_title = '猜你喜欢'
    products = fetch_products_by_ids(fetch_hot_product_ids(limit=4))

    if current_user.is_authenticated:
        personalized_products, _categories = fetch_personalized_products(int(current_user.get_id()), limit=4)
        if personalized_products:
            products = personalized_products
    enrich_products_with_sales(products)

    shops = fetch_hot_shops(limit=4)

    return render_template(
        'index.html',
        products=products,
        shops=shops,
        product_total=product_total,
        shop_total=shop_total,
        order_total=order_total,
        recommendation_title=recommendation_title,
    )
