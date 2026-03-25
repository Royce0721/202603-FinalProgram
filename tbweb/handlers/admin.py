from functools import wraps

from flask import Blueprint, abort, current_app, render_template, request
from flask_login import current_user, login_required

from ..services import TbBuy, TbMall, TbUser

admin = Blueprint('admin', __name__, url_prefix='/admin')


def is_admin_user():
    if not current_user.is_authenticated:
        return False

    admin_usernames = current_app.config.get('ADMIN_USERNAMES', [])
    admin_user_ids = current_app.config.get('ADMIN_USER_IDS', [])
    try:
        current_user_id = int(current_user.get_id())
    except (TypeError, ValueError):
        current_user_id = None

    return current_user.username in admin_usernames or current_user_id in admin_user_ids


def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped_view(*args, **kwargs):
        if not is_admin_user():
            abort(403)
        return view(*args, **kwargs)

    return wrapped_view


def paginate_params():
    page = request.args.get('page', 1, type=int)
    limit = current_app.config['PAGINATION_PER_PAGE']
    offset = (page - 1) * limit
    return page, limit, offset


def enrich_shops_with_users(shops):
    user_ids = sorted({shop['user_id'] for shop in shops if shop.get('user_id') is not None})
    users = {}
    if user_ids:
        resp = TbUser(current_app).get_json('/users/infos', params={
            'ids': ','.join([str(v) for v in user_ids]),
        }, check_code=False)
        users = resp.get('data', {}).get('users', {})

    for shop in shops:
        shop['owner'] = users.get(str(shop['user_id']))

    return shops


def enrich_products_with_shops(products):
    shop_ids = sorted({product['shop_id'] for product in products if product.get('shop_id') is not None})
    shops = {}
    if shop_ids:
        resp = TbMall(current_app).get_json('/shops/infos', params={
            'ids': ','.join([str(v) for v in shop_ids]),
        }, check_code=False)
        shops = resp.get('data', {}).get('shops', {})

    for product in products:
        product['shop'] = shops.get(str(product['shop_id']))

    return products


def enrich_orders(orders):
    user_ids = sorted({order['user_id'] for order in orders if order.get('user_id') is not None})
    address_ids = sorted({order['address_id'] for order in orders if order.get('address_id') is not None})

    users = {}
    addresses = {}
    if user_ids:
        resp = TbUser(current_app).get_json('/users/infos', params={
            'ids': ','.join([str(v) for v in user_ids]),
        }, check_code=False)
        users = resp.get('data', {}).get('users', {})
    if address_ids:
        resp = TbUser(current_app).get_json('/addresses/infos', params={
            'ids': ','.join([str(v) for v in address_ids]),
        }, check_code=False)
        addresses = resp.get('data', {}).get('addresses', {})

    for order in orders:
        order['user'] = users.get(str(order['user_id']))
        order['address'] = addresses.get(str(order['address_id']))

    return orders


@admin.route('')
@admin_required
def index():
    users_resp = TbUser(current_app).get_json('/users', params={'limit': 1, 'offset': 0}, check_code=False)
    shops_resp = TbMall(current_app).get_json('/shops', params={'limit': 1, 'offset': 0}, check_code=False)
    products_resp = TbMall(current_app).get_json('/products', params={'limit': 1, 'offset': 0}, check_code=False)
    orders_resp = TbBuy(current_app).get_json('/orders', params={'limit': 1, 'offset': 0}, check_code=False)
    transactions_resp = TbUser(current_app).get_json('/wallet_transactions', params={'limit': 1, 'offset': 0}, check_code=False)

    stats = {
        'users': users_resp.get('data', {}).get('total', 0),
        'shops': shops_resp.get('data', {}).get('total', 0),
        'products': products_resp.get('data', {}).get('total', 0),
        'orders': orders_resp.get('data', {}).get('total', 0),
        'transactions': transactions_resp.get('data', {}).get('total', 0),
    }

    recent_users = users_resp.get('data', {}).get('users', [])
    recent_shops = shops_resp.get('data', {}).get('shops', [])
    recent_products = products_resp.get('data', {}).get('products', [])

    return render_template(
        'admin/index.html',
        stats=stats,
        recent_users=recent_users,
        recent_shops=recent_shops,
        recent_products=recent_products,
    )


@admin.route('/users')
@admin_required
def users():
    page, limit, offset = paginate_params()
    resp = TbUser(current_app).get_json('/users', params={
        'limit': limit,
        'offset': offset,
    }, check_code=False)
    users = resp.get('data', {}).get('users', [])
    total = resp.get('data', {}).get('total', 0)

    for user in users:
        shop_resp = TbMall(current_app).get_json('/shops', params={
            'user_id': user['id'],
            'limit': 1,
            'offset': 0,
        }, check_code=False)
        user_shops = shop_resp.get('data', {}).get('shops', [])
        user['shop'] = user_shops[0] if user_shops else None

    return render_template('admin/users.html', users=users, total=total, page=page)


@admin.route('/shops')
@admin_required
def shops():
    page, limit, offset = paginate_params()
    resp = TbMall(current_app).get_json('/shops', params={
        'limit': limit,
        'offset': offset,
    }, check_code=False)
    shops = enrich_shops_with_users(resp.get('data', {}).get('shops', []))
    total = resp.get('data', {}).get('total', 0)

    for shop in shops:
        products_resp = TbMall(current_app).get_json('/products', params={
            'shop_id': shop['id'],
            'limit': 1,
            'offset': 0,
        }, check_code=False)
        shop['product_total'] = products_resp.get('data', {}).get('total', 0)

    return render_template('admin/shops.html', shops=shops, total=total, page=page)


@admin.route('/products')
@admin_required
def products():
    page, limit, offset = paginate_params()
    resp = TbMall(current_app).get_json('/products', params={
        'limit': limit,
        'offset': offset,
    }, check_code=False)
    products = enrich_products_with_shops(resp.get('data', {}).get('products', []))
    total = resp.get('data', {}).get('total', 0)
    return render_template('admin/products.html', products=products, total=total, page=page)


@admin.route('/orders')
@admin_required
def orders():
    page, limit, offset = paginate_params()
    resp = TbBuy(current_app).get_json('/orders', params={
        'limit': limit,
        'offset': offset,
    }, check_code=False)
    orders = enrich_orders(resp.get('data', {}).get('orders', []))
    total = resp.get('data', {}).get('total', 0)
    return render_template('admin/orders.html', orders=orders, total=total, page=page)


@admin.route('/transactions')
@admin_required
def transactions():
    page, limit, offset = paginate_params()
    resp = TbUser(current_app).get_json('/wallet_transactions', params={
        'limit': limit,
        'offset': offset,
    }, check_code=False)
    transactions = resp.get('data', {}).get('wallet_transactions', [])
    total = resp.get('data', {}).get('total', 0)
    return render_template('admin/transactions.html', transactions=transactions, total=total, page=page)
