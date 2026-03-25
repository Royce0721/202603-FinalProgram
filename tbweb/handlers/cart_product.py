from flask import Blueprint, request, current_app, render_template, flash, redirect, url_for
from flask_login import login_required, current_user

from tblib.handler import json_response

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
            total=total
        )

    # 批量查询购物车中的产品信息
    resp = TbMall(current_app).get_json('/products/infos', params={
        'ids': ','.join([str(v['product_id']) for v in cart_products]),
    })

    products = resp['data']['products']
    for item in cart_products:
        item['product'] = products.get(str(item['product_id']))

    return render_template(
        'cart_product/index.html',
        cart_products=cart_products,
        total=total
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


@cart_product.route('/add/<int:product_id>', methods=['GET', 'POST'])
@login_required
def add(product_id):
    """添加商品到购物车
    """

    resp = TbMall(current_app).get_json('/products/{}'.format(product_id))
    product = resp['data']['product']

    form = CartProductForm(data={
        'product_id': product_id,
        'amount': 1,
    })

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

    return render_template('cart_product/add.html', form=form, product=product)


@cart_product.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    """删除购物车商品
    """

    resp = TbBuy(current_app).delete_json('/cart_products/{}'.format(id), check_code=False)
    if resp['code'] != 0:
        flash(resp['message'], 'danger')
    else:
        flash('删除成功', 'success')

    return redirect(url_for('.index'))