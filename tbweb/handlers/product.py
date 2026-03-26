# handlers/product.py

from flask import Blueprint, request, current_app, render_template, redirect, url_for, flash
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from ..forms import ProductForm
from ..services import TbFile, TbMall

product = Blueprint('product', __name__, url_prefix='/products')
PRODUCTS_PER_PAGE = 24


def has_uploaded_file(field):
    file_data = getattr(field, 'data', None)
    return bool(file_data and getattr(file_data, 'filename', ''))


def get_current_user_shop():
    resp = TbMall(current_app).get_json('/shops', params={
        'user_id': current_user.get_id(),
        'limit': 1,
    }, check_code=False)
    shops = resp.get('data', {}).get('shops', [])
    return shops[0] if shops else None


@product.route('')
def index():
    """商品列表
    """
      # 添加了下面一行代码
    keywords = request.args.get('keywords', '')

    page = request.args.get('page', 1, type=int)

    limit = PRODUCTS_PER_PAGE
    offset = (page - 1) * limit
    resp = TbMall(current_app).get_json('/products', params={
            # 添加了下面一行代码
        'keywords': keywords,

        'limit': limit,
        'offset': offset
    })

     # 修改了下面这一行代码
    return render_template('product/index.html', **resp['data'], keywords=keywords, per_page=limit)



@product.route('/<int:id>')
def detail(id):
    """商品详情
    """

    # 向后台商场服务查询对应商品id的详情
    resp = TbMall(current_app).get_json('/products/{}'.format(id))
    return render_template('product/detail.html', **resp['data'])


@product.route('/mine')
@login_required
def mine():
    shop = get_current_user_shop()
    if shop is None:
        flash('你还没有店铺，先去开店吧', 'info')
        return redirect(url_for('shop.create'))

    page = request.args.get('page', 1, type=int)
    limit = current_app.config['PAGINATION_PER_PAGE']
    offset = (page - 1) * limit
    resp = TbMall(current_app).get_json('/products', params={
        'shop_id': shop['id'],
        'limit': limit,
        'offset': offset,
    })
    return render_template('product/mine.html', shop=shop, **resp['data'])


@product.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    shop = get_current_user_shop()
    if shop is None:
        flash('你还没有店铺，先去开店吧', 'info')
        return redirect(url_for('shop.create'))

    form = ProductForm()
    if form.validate_on_submit():
        cover = ''
        if has_uploaded_file(form.cover):
            f = form.cover.data
            upload_resp = TbFile(current_app).post_json('/files', files={
                'file': (secure_filename(f.filename), f, f.mimetype),
            }, check_code=False)
            if upload_resp['code'] != 0:
                flash(upload_resp['message'], 'danger')
                return render_template('product/create.html', form=form, shop=shop)
            cover = upload_resp['data']['id']

        resp = TbMall(current_app).post_json('/products', json={
            'title': form.title.data,
            'description': form.description.data,
            'price': form.price.data,
            'amount': form.amount.data,
            'cover': cover,
            'shop_id': shop['id'],
        }, check_code=False)
        if resp['code'] != 0:
            flash(resp['message'], 'danger')
            return render_template('product/create.html', form=form, shop=shop)

        flash('商品创建成功', 'success')
        return redirect(url_for('.mine'))

    return render_template('product/create.html', form=form, shop=shop)


@product.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    shop = get_current_user_shop()
    if shop is None:
        flash('你还没有店铺，先去开店吧', 'info')
        return redirect(url_for('shop.create'))

    resp = TbMall(current_app).get_json('/products/{}'.format(id), check_code=False)
    product_data = resp.get('data', {}).get('product')
    if product_data is None or product_data.get('shop_id') != shop['id']:
        flash('未找到该商品，或你无权编辑它', 'danger')
        return redirect(url_for('.mine'))

    form = ProductForm(data={
        'title': product_data.get('title'),
        'description': product_data.get('description'),
        'price': product_data.get('price'),
        'amount': product_data.get('amount'),
    })
    if form.validate_on_submit():
        payload = {
            'title': form.title.data,
            'description': form.description.data,
            'price': form.price.data,
            'amount': form.amount.data,
        }

        if has_uploaded_file(form.cover):
            f = form.cover.data
            upload_resp = TbFile(current_app).post_json('/files', files={
                'file': (secure_filename(f.filename), f, f.mimetype),
            }, check_code=False)
            if upload_resp['code'] != 0:
                flash(upload_resp['message'], 'danger')
                return render_template('product/edit.html', form=form, shop=shop, product=product_data)
            payload['cover'] = upload_resp['data']['id']

        update_resp = TbMall(current_app).post_json('/products/{}'.format(id), json=payload, check_code=False)
        if update_resp['code'] != 0:
            flash(update_resp['message'], 'danger')
            return render_template('product/edit.html', form=form, shop=shop, product=product_data)

        flash('商品更新成功', 'success')
        return redirect(url_for('.mine'))

    return render_template('product/edit.html', form=form, shop=shop, product=product_data)


@product.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    shop = get_current_user_shop()
    if shop is None:
        flash('你还没有店铺，无法删除商品', 'danger')
        return redirect(url_for('shop.create'))

    resp = TbMall(current_app).get_json('/products/{}'.format(id), check_code=False)
    product_data = resp.get('data', {}).get('product')
    if product_data is None or product_data.get('shop_id') != shop['id']:
        flash('未找到该商品，或你无权删除它', 'danger')
        return redirect(url_for('.mine'))

    delete_resp = TbMall(current_app).delete_json('/products/{}'.format(id), check_code=False)
    if delete_resp['code'] != 0:
        flash(delete_resp['message'], 'danger')
    else:
        flash('商品删除成功', 'success')

    return redirect(url_for('.mine'))
