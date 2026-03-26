from flask import Blueprint, request, current_app, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from tblib.handler import json_response, ResponseCode
from tblib.redis import redis

from ..forms import OrderForm, ReviewForm
from ..services import TbBuy, TbUser, TbMall

order = Blueprint('order', __name__, url_prefix='/orders')


def delivered_shops_key(order_id):
    return f'order:{order_id}:delivered_shops'


def get_delivered_shop_ids(order_id):
    delivered_shop_ids = set()
    for raw_shop_id in redis.smembers(delivered_shops_key(order_id)):
        try:
            delivered_shop_ids.add(int(raw_shop_id))
        except (TypeError, ValueError):
            continue
    return delivered_shop_ids


def clear_delivered_shop_ids(order_id):
    redis.delete(delivered_shops_key(order_id))


def seller_deliver_response(resp):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return json_response(resp.get('code', 0), resp.get('message', ''), **resp.get('data', {}))
    if resp.get('code', 0) != 0:
        flash(resp.get('message', '发货失败'), 'danger')
    return redirect(url_for('.seller_detail', id=request.view_args['id']))


def _render_create_page(form, cart_products):
    return render_template('order/create.html', form=form, cart_products=cart_products)


def rollback_payment_transactions(order_id, successful_transfers):
    rollback_failed = False
    for transfer in reversed(successful_transfers):
        rollback_resp = TbUser(current_app).post_json('/wallet_transactions', json={
            'amount': transfer['amount'],
            'note': '回滚订单({})商品({})支付'.format(order_id, transfer['product_id']),
            'payer_id': transfer['payee_id'],
            'payee_id': transfer['payer_id'],
        }, check_code=False)
        if rollback_resp.get('code') != 0:
            rollback_failed = True
    return rollback_failed


def get_current_user_shop():
    resp = TbMall(current_app).get_json('/shops', params={
        'user_id': current_user.get_id(),
        'limit': 1,
    }, check_code=False)
    shops = resp.get('data', {}).get('shops', [])
    return shops[0] if shops else None


@order.route('')
@login_required
def index():
    """当前用户的订单列表
    """

    page = request.args.get('page', 1, type=int)

    limit = current_app.config['PAGINATION_PER_PAGE']
    offset = (page - 1) * limit
    resp = TbBuy(current_app).get_json('/orders', params={
        'user_id': current_user.get_id(),
        'limit': limit,
        'offset': offset,
    })

    orders = resp['data']['orders']
    total = resp['data']['total']

    orders = full_order_info(orders)

    return render_template('order/index.html', orders=orders, total=total)


def full_order_info(orders):
    """查询多个订单的详细信息，尽可能使用批量查询来优化性能
    """

    address_ids = []
    product_ids = []
    for order_item in orders:
        address_ids.append(order_item['address_id'])
        product_ids.extend([v['product_id'] for v in order_item['order_products']])

    addresses = {}
    if len(address_ids) > 0:
        resp = TbUser(current_app).get_json('/addresses/infos', params={
            'ids': ','.join([str(v) for v in address_ids]),
        })
        addresses = resp['data']['addresses']

    products = {}
    if len(product_ids) > 0:
        resp = TbMall(current_app).get_json('/products/infos', params={
            'ids': ','.join([str(v) for v in product_ids]),
        })
        products = resp['data']['products']

    for order_item in orders:
        order_item['address'] = addresses.get(str(order_item['address_id']))
        for order_product in order_item['order_products']:
            order_product['product'] = products.get(str(order_product['product_id']))

    return orders


def seller_order_scope(orders, shop):
    scoped_orders = []
    for order_item in orders:
        delivered_shop_ids = get_delivered_shop_ids(order_item['id'])
        all_shop_ids = set()
        seller_products = []
        for order_product in order_item['order_products']:
            product = order_product.get('product')
            if product is None:
                continue
            product_shop_id = product['shop']['id']
            all_shop_ids.add(product_shop_id)
            if product_shop_id == shop['id']:
                seller_products.append(order_product)

        if seller_products:
            order_item['seller_order_products'] = seller_products
            order_item['seller_delivered'] = shop['id'] in delivered_shop_ids
            order_item['seller_can_deliver'] = (
                order_item['status'] == 'paied' and shop['id'] not in delivered_shop_ids
            )
            order_item['all_shop_ids'] = sorted(all_shop_ids)
            order_item['delivered_shop_ids'] = sorted(delivered_shop_ids)
            scoped_orders.append(order_item)

    return scoped_orders


def fetch_all_orders():
    limit = 100
    offset = 0
    total = None
    orders = []

    while total is None or offset < total:
        resp = TbBuy(current_app).get_json('/orders', params={
            'limit': limit,
            'offset': offset,
        }, check_code=False)
        batch = resp.get('data', {}).get('orders', [])
        total = resp.get('data', {}).get('total', 0)
        orders.extend(batch)
        if not batch:
            break
        offset += limit

    return orders


@order.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """创建订单
    """

    form = OrderForm()

    resp = TbUser(current_app).get_json('/addresses', params={
        'user_id': current_user.get_id(),
    })
    addresses = resp['data']['addresses']

    form.address_id.choices = [(str(v['id']), v['address']) for v in addresses]
    for address in addresses:
        if address['is_default']:
            form.address_id.data = str(address['id'])

    resp = TbBuy(current_app).get_json('/cart_products', params={
        'user_id': current_user.get_id(),
    })
    cart_products = resp['data']['cart_products']
    if len(cart_products) == 0:
        flash('购物车为空', 'danger')
        return redirect(url_for('cart_product.index'))

    resp = TbMall(current_app).get_json('/products/infos', params={
        'ids': ','.join([str(v['product_id']) for v in cart_products]),
    })
    for item in cart_products:
        item['product'] = resp['data']['products'].get(str(item['product_id']))

    if form.validate_on_submit():
        if len(addresses) == 0:
            flash('请先添加收货地址', 'danger')
            return redirect(url_for('address.create'))

        for item in cart_products:
            if item.get('product') is None:
                flash('购物车中存在已失效商品，请刷新后重试', 'danger')
                return redirect(url_for('cart_product.index'))
            if item['product']['shop']['user_id'] == int(current_user.get_id()):
                flash('不能购买自己店铺的商品，请先从购物车中移除', 'danger')
                return redirect(url_for('cart_product.index'))
            if item['amount'] > item['product']['amount']:
                flash('商品“{}”数量不足'.format(item['product']['title']), 'danger')
                return _render_create_page(form, cart_products)

        resp = TbBuy(current_app).post_json('/orders', json={
            'address_id': form.address_id.data,
            'note': form.note.data,
            'order_products': [
                {
                    'product_id': v['product_id'],
                    'amount': v['amount'],
                    'price': v['product']['price'],
                } for v in cart_products
            ],
            'user_id': current_user.get_id(),
        }, check_code=False)
        if resp['code'] != 0:
            flash(resp['message'], 'danger')
            return _render_create_page(form, cart_products)

        for item in cart_products:
            resp = TbMall(current_app).post_json(
                '/products/{}'.format(item['product_id']),
                json={
                    'amount': item['product']['amount'] - item['amount'],
                }
            )
            if resp['code'] != 0:
                flash(resp['message'], 'danger')
                return _render_create_page(form, cart_products)

        resp = TbBuy(current_app).delete_json('/cart_products', params={
            'user_id': current_user.get_id(),
        })
        if resp['code'] != 0:
            flash(resp['message'], 'danger')
            return _render_create_page(form, cart_products)

        return redirect(url_for('.index'))

    return render_template('order/create.html', form=form, cart_products=cart_products)


@order.route('/<int:id>', methods=['GET', 'POST'])
@login_required
def detail(id):
    """订单详情
    """

    resp = TbBuy(current_app).get_json('/orders/{}'.format(id))
    order_data = resp['data']['order']
    form = OrderForm(data=order_data)

    resp = TbUser(current_app).get_json('/addresses', params={
        'user_id': current_user.get_id(),
    })
    form.address_id.choices = [(str(v['id']), v['address']) for v in resp['data']['addresses']]

    resp = TbMall(current_app).get_json('/products/infos', params={
        'ids': ','.join([str(v['product_id']) for v in order_data['order_products']]),
    })
    for order_product in order_data['order_products']:
        order_product['product'] = resp['data']['products'].get(str(order_product['product_id']))

    if form.validate_on_submit():
        resp = TbBuy(current_app).post_json('/orders/{}'.format(id), json={
            'address_id': form.address_id.data,
            'note': form.note.data,
        }, check_code=False)
        if resp['code'] != 0:
            flash(resp['message'], 'danger')
            return render_template('order/detail.html', form=form, order=order_data)

        return redirect(url_for('.index'))

    return render_template('order/detail.html', form=form, order=order_data)


@order.route('/<int:id>/pay', methods=['POST'])
@login_required
def pay(id):
    """支付订单
    """

    current_user_id = int(current_user.get_id())
    resp = TbBuy(current_app).get_json('/orders/{}'.format(id))
    order_data = resp['data']['order']
    if order_data['user_id'] != current_user_id:
        return json_response(ResponseCode.NOT_FOUND)
    if order_data['status'] != 'new':
        return json_response(ResponseCode.ERROR, '订单状态不允许支付')

    resp = TbUser(current_app).get_json('/users/{}'.format(order_data['user_id']))
    user = resp['data']['user']
    if user['wallet_money'] < order_data['pay_amount']:
        return json_response(ResponseCode.NO_ENOUGH_MONEY)

    resp = TbMall(current_app).get_json('/products/infos', params={
        'ids': ','.join([str(v['product_id']) for v in order_data['order_products']]),
    })
    products = resp['data']['products']
    successful_transfers = []

    for order_product in order_data['order_products']:
        product = products.get(str(order_product['product_id']))
        if product is None:
            return json_response(ResponseCode.NOT_FOUND, '订单商品不存在')
        if product['shop']['user_id'] == current_user_id:
            return json_response(ResponseCode.ERROR, '不能购买自己店铺的商品')
        if product['amount'] < order_product['amount']:
            return json_response(ResponseCode.QUANTITY_EXCEEDS_LIMIT, '商品库存不足')
        resp = TbUser(current_app).post_json('/wallet_transactions', json={
            'amount': order_product['amount'] * order_product['price'],
            'note': '支付订单({})商品({})'.format(order_data['id'], product['id']),
            'payer_id': order_data['user_id'],
            'payee_id': product['shop']['user_id'],
        }, check_code=False)
        if resp['code'] != 0:
            rollback_failed = rollback_payment_transactions(order_data['id'], successful_transfers)
            if rollback_failed:
                return json_response(ResponseCode.ERROR, '支付失败，且回滚异常，请检查钱包流水')
            return json_response(resp['code'], resp['message'], **resp['data'])
        successful_transfers.append({
            'amount': order_product['amount'] * order_product['price'],
            'payer_id': order_data['user_id'],
            'payee_id': product['shop']['user_id'],
            'product_id': product['id'],
        })

    resp = TbBuy(current_app).post_json('/orders/{}'.format(id), json={
        'status': 'paied',
    }, check_code=False)
    if resp['code'] != 0:
        rollback_failed = rollback_payment_transactions(order_data['id'], successful_transfers)
        if rollback_failed:
            return json_response(ResponseCode.ERROR, '订单状态更新失败，且回滚异常，请检查钱包流水')
        return json_response(resp['code'], resp['message'], **resp['data'])

    clear_delivered_shop_ids(id)
    flash('支付成功', 'success')
    return json_response(resp['code'], resp['message'], **resp['data'])


@order.route('/<int:id>/cancel', methods=['POST'])
@login_required
def cancel(id):
    """取消订单
    """

    current_user_id = int(current_user.get_id())
    resp = TbBuy(current_app).get_json('/orders/{}'.format(id))
    order_data = resp['data']['order']
    if order_data['user_id'] != current_user_id:
        return json_response(ResponseCode.NOT_FOUND)
    if order_data['status'] != 'new':
        return json_response(ResponseCode.ERROR, '订单状态不允许取消')

    resp = TbMall(current_app).get_json('/products/infos', params={
        'ids': ','.join([str(v['product_id']) for v in order_data['order_products']]),
    }, check_code=False)
    products = resp.get('data', {}).get('products', {})

    for order_product in order_data['order_products']:
        product = products.get(str(order_product['product_id']))
        if product is None:
            return json_response(ResponseCode.NOT_FOUND, '订单商品不存在，无法恢复库存')
        restore_resp = TbMall(current_app).post_json('/products/{}'.format(order_product['product_id']), json={
            'amount': product['amount'] + order_product['amount'],
        }, check_code=False)
        if restore_resp['code'] != 0:
            return json_response(restore_resp['code'], restore_resp['message'], **restore_resp['data'])

    resp = TbBuy(current_app).post_json('/orders/{}'.format(id), json={
        'status': 'cancelled',
    }, check_code=False)
    if resp['code'] == 0:
        clear_delivered_shop_ids(id)
        flash('订单已取消，库存已恢复', 'success')

    return json_response(resp['code'], resp['message'], **resp['data'])


@order.route('/<int:id>/receive', methods=['POST'])
@login_required
def receive(id):
    """确认收货
    """

    current_user_id = int(current_user.get_id())
    resp = TbBuy(current_app).get_json('/orders/{}'.format(id), check_code=False)
    order_data = resp.get('data', {}).get('order')
    if order_data is None or order_data['user_id'] != current_user_id:
        return json_response(ResponseCode.NOT_FOUND)
    if order_data['status'] != 'delivered':
        return json_response(ResponseCode.ERROR, '订单状态不允许确认收货')

    resp = TbBuy(current_app).post_json('/orders/{}'.format(id), json={
        'status': 'received',
    }, check_code=False)
    if resp['code'] == 0:
        clear_delivered_shop_ids(id)
        flash('确认收货成功', 'success')

    return json_response(resp['code'], resp['message'], **resp['data'])


@order.route('/<int:id>/comment', methods=['GET', 'POST'])
@login_required
def comment(id):
    """评价订单
    """

    current_user_id = int(current_user.get_id())
    resp = TbBuy(current_app).get_json('/orders/{}'.format(id), check_code=False)
    order_data = resp.get('data', {}).get('order')
    if order_data is None or order_data['user_id'] != current_user_id:
        flash('订单不存在', 'danger')
        return redirect(url_for('.index'))
    if order_data['status'] != 'received':
        flash('当前订单状态不允许评价', 'danger')
        return redirect(url_for('.index'))

    order_data = full_order_info([order_data])[0]
    form = ReviewForm()
    if form.validate_on_submit():
        review_resp = TbBuy(current_app).post_json('/reviews', json={
            'order_id': id,
            'user_id': current_user_id,
            'content': form.content.data.strip(),
        }, check_code=False)
        if review_resp['code'] != 0:
            flash(review_resp['message'], 'danger')
            return render_template('order/comment.html', form=form, order=order_data)

        update_resp = TbBuy(current_app).post_json('/orders/{}'.format(id), json={
            'status': 'commented',
        }, check_code=False)
        if update_resp['code'] != 0:
            flash('评价已写入，但订单状态更新失败，请检查订单状态', 'danger')
            return render_template('order/comment.html', form=form, order=order_data)

        clear_delivered_shop_ids(id)
        flash('评价成功', 'success')
        return redirect(url_for('.index'))

    return render_template('order/comment.html', form=form, order=order_data)


@order.route('/seller')
@login_required
def seller_index():
    shop = get_current_user_shop()
    if shop is None:
        flash('你还没有店铺，先去开店吧', 'info')
        return redirect(url_for('shop.create'))

    all_orders = fetch_all_orders()
    all_orders = full_order_info(all_orders)
    seller_orders = seller_order_scope(all_orders, shop)

    page = request.args.get('page', 1, type=int)
    limit = current_app.config['PAGINATION_PER_PAGE']
    offset = (page - 1) * limit
    total = len(seller_orders)
    page_orders = seller_orders[offset: offset + limit]

    return render_template('order/seller_index.html', shop=shop, orders=page_orders, total=total)


@order.route('/seller/<int:id>')
@login_required
def seller_detail(id):
    shop = get_current_user_shop()
    if shop is None:
        flash('你还没有店铺，先去开店吧', 'info')
        return redirect(url_for('shop.create'))

    resp = TbBuy(current_app).get_json('/orders/{}'.format(id), check_code=False)
    order_data = resp.get('data', {}).get('order')
    if order_data is None:
        flash('订单不存在', 'danger')
        return redirect(url_for('.seller_index'))

    scoped_orders = seller_order_scope(full_order_info([order_data]), shop)
    if not scoped_orders:
        flash('你无权查看该订单', 'danger')
        return redirect(url_for('.seller_index'))

    return render_template('order/seller_detail.html', shop=shop, order=scoped_orders[0])


@order.route('/seller/<int:id>/deliver', methods=['POST'])
@login_required
def seller_deliver(id):
    shop = get_current_user_shop()
    if shop is None:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return json_response(ResponseCode.NOT_FOUND)
        flash('店铺不存在', 'danger')
        return redirect(url_for('shop.create'))

    resp = TbBuy(current_app).get_json('/orders/{}'.format(id), check_code=False)
    order_data = resp.get('data', {}).get('order')
    if order_data is None:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return json_response(ResponseCode.NOT_FOUND)
        flash('订单不存在', 'danger')
        return redirect(url_for('.seller_index'))

    scoped_orders = seller_order_scope(full_order_info([order_data]), shop)
    if not scoped_orders:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return json_response(ResponseCode.NOT_FOUND)
        flash('你无权操作该订单', 'danger')
        return redirect(url_for('.seller_index'))

    order_data = scoped_orders[0]
    if not order_data.get('seller_can_deliver'):
        resp = {
            'code': ResponseCode.ERROR,
            'message': '当前订单状态不允许发货，或你这部分已经发过了',
            'data': {},
        }
        return seller_deliver_response(resp)

    shop_id = shop['id']
    redis.sadd(delivered_shops_key(id), shop_id)

    delivered_shop_ids = get_delivered_shop_ids(id)
    all_shop_ids = set(order_data.get('all_shop_ids', []))
    if all_shop_ids and all_shop_ids.issubset(delivered_shop_ids):
        update_resp = TbBuy(current_app).post_json('/orders/{}'.format(id), json={
            'status': 'delivered',
        }, check_code=False)
        if update_resp['code'] == 0:
            flash('这张订单已全部发货', 'success')
        else:
            redis.srem(delivered_shops_key(id), shop_id)
        return seller_deliver_response(update_resp)

    flash('你店铺这部分已经发货，等其他店铺也发完后，订单会进入待收货', 'success')
    return seller_deliver_response({
        'code': 0,
        'message': '当前店铺商品已发货',
        'data': {},
    })
