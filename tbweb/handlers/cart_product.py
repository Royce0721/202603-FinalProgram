from flask import Blueprint, request, current_app, render_template, flash, redirect, url_for
from flask_login import login_required, current_user

from tblib.handler import json_response
from tblib.money import to_money

from ..services import TbBuy, TbMall
from ..forms import CartProductForm

cart_product = Blueprint('cart_product', __name__, url_prefix='/cart_products')


@cart_product.route('')
@login_required
def index():
    """购物车商品列表
    """
    page = request.args.get('page', 1, type=int)

    limit = current_app.config['PAGINATION_PER_PAGE']
    offset = (page - 1) * limit
    resp = TbBuy(current_app).get_json('/cart_products', params={
        'user_id': current_user.get_id(),
        'limit': limit,
        'offset': offset,
    })

    cart_products = resp['data']['cart_products']
    total = resp['data']['total']

    # 如果购物车为空，直接返回页面，不再请求商品信息接口
    if not cart_products:
        return render_template(
            'cart_product/index.html',
            cart_products=[],
            total=total,
            total_amount=0,
        )

    # 批量查询购物车中的产品信息
    resp = TbMall(current_app).get_json('/products/infos', params={
        'ids': ','.join([str(v['product_id']) for v in cart_products]),
    })

    products = resp['data']['products']
    total_amount = to_money(0)
    for item in cart_products:
        item['product'] = products.get(str(item['product_id']))
        product = item.get('product')
        if product is not None:
            item['subtotal'] = to_money(product['price']) * item['amount']
            total_amount += item['subtotal']
        else:
            item['subtotal'] = to_money(0)

    return render_template(
        'cart_product/index.html',
        cart_products=cart_products,
        total=total,
        total_amount=total_amount,
    )

@cart_product.route('/<int:id>', methods=['GET', 'POST'])
@login_required
def detail(id):
    """购物车商品详情/编辑
    """

    resp = TbBuy(current_app).get_json('/cart_products/{}'.format(id))
    cart_product_data = resp['data']['cart_product']
    form = CartProductForm(data=cart_product_data)

    resp = TbMall(current_app).get_json('/products/{}'.format(cart_product_data['product_id']))
    product = resp['data']['product']

    if form.validate_on_submit():
        resp = TbBuy(current_app).post_json('/cart_products/{}'.format(id), json={
            'amount': form.amount.data,
        }, check_code=False)
        if resp['code'] != 0:
            flash(resp['message'], 'danger')
            return render_template(
                'cart_product/detail.html',
                form=form,
                cart_product=cart_product_data,
                product=product
            )

        flash('修改成功', 'success')
        return redirect(url_for('.index'))

    return render_template(
        'cart_product/detail.html',
        form=form,
        cart_product=cart_product_data,
        product=product
    )


@cart_product.route('/<int:id>/amount', methods=['POST'])
@login_required
def update_amount(id):
    """AJAX 更新购物车商品数量"""

    data = request.get_json(silent=True) or {}
    amount = data.get('amount')
    if not isinstance(amount, int):
        return json_response(code=1, message='数量不合法')
    if amount < 1:
        return json_response(code=1, message='数量不能小于 1')

    resp = TbBuy(current_app).get_json('/cart_products/{}'.format(id), check_code=False)
    cart_product_data = resp.get('data', {}).get('cart_product')
    if resp.get('code') != 0 or cart_product_data is None:
        return json_response(code=1, message='购物车商品不存在')

    if int(cart_product_data.get('user_id')) != int(current_user.get_id()):
        return json_response(code=1, message='你无权修改这条购物车记录')

    product_resp = TbMall(current_app).get_json('/products/{}'.format(cart_product_data['product_id']), check_code=False)
    product = product_resp.get('data', {}).get('product')
    if product_resp.get('code') != 0 or product is None:
        return json_response(code=1, message='商品不存在或已下架')

    if amount > product.get('amount', 0):
        return json_response(code=1, message='库存不够了')

    update_resp = TbBuy(current_app).post_json('/cart_products/{}'.format(id), json={
        'amount': amount,
    }, check_code=False)
    if update_resp.get('code') != 0:
        return json_response(code=1, message=update_resp.get('message', '数量更新失败'))

    return json_response(code=0, message='更新成功')


@cart_product.route('/add/<int:product_id>', methods=['GET', 'POST'])
@login_required
def add(product_id):
    """添加商品到购物车
    """

    resp = TbMall(current_app).get_json('/products/{}'.format(product_id))
    product = resp['data']['product']
    is_own_product = product['shop']['user_id'] == int(current_user.get_id())

    form = CartProductForm(data={
        'product_id': product_id,
        'amount': 1,
    })

    if is_own_product:
        flash('不能购买自己店铺的商品', 'danger')
        return redirect(url_for('product.detail', id=product_id))

    if form.validate_on_submit():
        resp = TbBuy(current_app).post_json('/cart_products', json={
            'user_id': current_user.get_id(),
            'product_id': int(form.product_id.data),
            'amount': form.amount.data,
        }, check_code=False)
        if resp['code'] != 0:
            flash(resp['message'], 'danger')
            return render_template('cart_product/add.html', form=form, product=product)

        flash('加入购物车成功', 'success')
        return redirect(url_for('.index'))

    return render_template('cart_product/add.html', form=form, product=product, is_own_product=is_own_product)


@cart_product.route('/<int:id>/delete', methods=['POST', 'DELETE'])
@login_required
def delete(id):
    """删除购物车商品
    """

    resp = TbBuy(current_app).delete_json('/cart_products/{}'.format(id), check_code=False)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if resp['code'] != 0:
        if is_ajax:
            return json_response(code=resp.get('code', 1), message=resp.get('message', '删除失败'))
        flash(resp['message'], 'danger')
    else:
        if is_ajax:
            return json_response(code=0, message='删除成功')
        flash('删除成功', 'success')

    return redirect(url_for('.index'))
