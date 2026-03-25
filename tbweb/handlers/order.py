from flask import Blueprint, request, current_app, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from tblib.handler import json_response, ResponseCode

from ..forms import OrderForm, ReviewForm
from ..services import TbBuy, TbUser, TbMall

order = Blueprint('order', __name__, url_prefix='/orders')


def _render_create_page(form, cart_products):
    return render_template('order/create.html', form=form, cart_products=cart_products)


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
        seller_products = []
        all_products_belong_to_shop = True
        for order_product in order_item['order_products']:
            product = order_product.get('product')
            if product is None:
                all_products_belong_to_shop = False
                continue
            if product['shop']['id'] == shop['id']:
                seller_products.append(order_product)
            else:
                all_products_belong_to_shop = False

        if seller_products:
            order_item['seller_order_products'] = seller_products
            order_item['seller_can_deliver'] = all_products_belong_to_shop and order_item['status'] == 'paied'
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
        })
        if resp['code'] != 0:
            return json_response(resp['code'], resp['message'], **resp['data'])

    resp = TbBuy(current_app).post_json('/orders/{}'.format(id), json={
        'status': 'paied',
    })

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

    resp = TbBuy(current_app).post_json('/orders/{}'.format(id), json={
        'status': 'cancelled',
    })

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
        review_note = '评价：{}'.format(form.content.data.strip())
        existing_note = (order_data.get('note') or '').strip()
        combined_note = review_note if not existing_note else '{} | {}'.format(existing_note, review_note)
        if len(combined_note) > 200:
            combined_note = combined_note[:200]

        update_resp = TbBuy(current_app).post_json('/orders/{}'.format(id), json={
            'status': 'commented',
            'note': combined_note,
        }, check_code=False)
        if update_resp['code'] != 0:
            flash(update_resp['message'], 'danger')
            return render_template('order/comment.html', form=form, order=order_data)

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
        return json_response(ResponseCode.NOT_FOUND)

    resp = TbBuy(current_app).get_json('/orders/{}'.format(id), check_code=False)
    order_data = resp.get('data', {}).get('order')
    if order_data is None:
        return json_response(ResponseCode.NOT_FOUND)

    scoped_orders = seller_order_scope(full_order_info([order_data]), shop)
    if not scoped_orders:
        return json_response(ResponseCode.NOT_FOUND)

    order_data = scoped_orders[0]
    if not order_data.get('seller_can_deliver'):
        return json_response(ResponseCode.ERROR, '当前订单状态不允许发货，或这是跨店铺订单')

    update_resp = TbBuy(current_app).post_json('/orders/{}'.format(id), json={
        'status': 'delivered',
    }, check_code=False)
    if update_resp['code'] == 0:
        flash('发货成功', 'success')
    return json_response(update_resp['code'], update_resp['message'], **update_resp['data'])
