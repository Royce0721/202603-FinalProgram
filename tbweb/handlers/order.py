from flask import Blueprint, request, current_app, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from tblib.handler import json_response, ResponseCode

from ..forms import OrderForm
from ..services import TbBuy, TbUser, TbMall

order = Blueprint('order', __name__, url_prefix='/orders')


def _render_create_page(form, cart_products):
    return render_template('order/create.html', form=form, cart_products=cart_products)


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
