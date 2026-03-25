# handlers/shop.py

from flask import Blueprint, request, current_app, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from ..forms import ShopForm
from ..services import TbMall, TbUser, TbFile

shop = Blueprint('shop', __name__, url_prefix='/shops')


def get_current_user_shop():
    resp = TbMall(current_app).get_json('/shops', params={
        'user_id': current_user.get_id(),
        'limit': 1,
    }, check_code=False)
    shops = resp.get('data', {}).get('shops', [])
    return shops[0] if shops else None


@shop.route('')
def index():
    """店铺列表
    """
      # 添加了下面一行代码
    keywords = request.args.get('keywords', '')

    page = request.args.get('page', 1, type=int)

    limit = current_app.config['PAGINATION_PER_PAGE']
    offset = (page - 1) * limit
    resp = TbMall(current_app).get_json('/shops', params={
            # 添加了下面一行代码
        'keywords': keywords,

        'limit': limit,
        'offset': offset
    })
    shops = resp['data']['shops']
    total = resp['data']['total']

    user_ids = [shop['user_id'] for shop in shops]
    if len(user_ids) > 0:
        # 批量查询多个店铺的店主信息
        resp = TbUser(current_app).get_json('/users/infos', params={
            'ids': ','.join([str(v) for v in user_ids]),
        })
        for shop in shops:
            shop['user'] = resp['data']['users'].get(str(shop['user_id']))

    # 每个店铺选取三个商品来展示
    for shop in shops:
        r = TbMall(current_app).get_json('/products', params={
            'shop_id': shop['id'],
            'limit': 3
        })
        shop['products'] = r['data']['products']

    # 修改了下面这一行代码
    return render_template('shop/index.html', shops=shops, total=total, keywords=keywords)



@shop.route('/<int:id>')
def detail(id):
    """店铺详情
    """

    # 获取当前页码的编号
    page = request.args.get('page', 1, type=int)

    # 使用 get 方法向后台商场服务查询店铺id对应的店铺信息
    resp = TbMall(current_app).get_json('/shops/{}'.format(id))
    shop = resp['data']['shop']

    # 使用 get 方法向后台用户服务店铺id对应用户信息
    resp = TbUser(current_app).get_json('/users/{}'.format(shop['user_id']))
    shop['user'] = resp['data']['user']

    limit = current_app.config['PAGINATION_PER_PAGE']
    offset = (page - 1) * limit
    # 查询当前页该店铺对应的商品信息
    resp = TbMall(current_app).get_json('/products', params={
        'shop_id': id,
        'limit': limit,
        'offset': offset
    })

    return render_template('shop/detail.html', shop=shop, **resp['data'])


@shop.route('/entry')
@login_required
def entry():
    user_shop = get_current_user_shop()
    if user_shop is None:
        return redirect(url_for('.create'))
    return redirect(url_for('.mine'))


@shop.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    user_shop = get_current_user_shop()
    if user_shop is not None:
        flash('你已经拥有自己的店铺了', 'info')
        return redirect(url_for('.mine'))

    form = ShopForm()
    if form.validate_on_submit():
        cover = ''
        if form.cover.data and form.cover.data.filename:
            f = form.cover.data
            resp = TbFile(current_app).post_json('/files', files={
                'file': (secure_filename(f.filename), f, f.mimetype),
            }, check_code=False)
            if resp['code'] != 0:
                flash(resp['message'], 'danger')
                return render_template('shop/create.html', form=form)
            cover = resp['data']['id']

        resp = TbMall(current_app).post_json('/shops', json={
            'name': form.name.data,
            'description': form.description.data,
            'cover': cover,
            'user_id': current_user.get_id(),
        }, check_code=False)
        if resp['code'] != 0:
            flash(resp['message'], 'danger')
            return render_template('shop/create.html', form=form)

        flash('开店成功', 'success')
        return redirect(url_for('.mine'))

    return render_template('shop/create.html', form=form)


@shop.route('/mine', methods=['GET', 'POST'])
@login_required
def mine():
    shop_data = get_current_user_shop()
    if shop_data is None:
        flash('你还没有店铺，先去开店吧', 'info')
        return redirect(url_for('.create'))

    resp = TbUser(current_app).get_json('/users/{}'.format(shop_data['user_id']))
    shop_data['user'] = resp['data']['user']

    products_resp = TbMall(current_app).get_json('/products', params={
        'shop_id': shop_data['id'],
        'limit': current_app.config['PAGINATION_PER_PAGE'],
        'offset': 0,
    })
    products = products_resp['data']['products']

    form = ShopForm(data={
        'name': shop_data['name'],
        'description': shop_data['description'],
    })
    if form.validate_on_submit():
        payload = {
            'name': form.name.data,
            'description': form.description.data,
        }

        if form.cover.data and form.cover.data.filename:
            f = form.cover.data
            upload_resp = TbFile(current_app).post_json('/files', files={
                'file': (secure_filename(f.filename), f, f.mimetype),
            }, check_code=False)
            if upload_resp['code'] != 0:
                flash(upload_resp['message'], 'danger')
                return render_template('shop/mine.html', form=form, shop=shop_data, products=products)
            payload['cover'] = upload_resp['data']['id']

        update_resp = TbMall(current_app).post_json('/shops/{}'.format(shop_data['id']), json=payload, check_code=False)
        if update_resp['code'] != 0:
            flash(update_resp['message'], 'danger')
            return render_template('shop/mine.html', form=form, shop=shop_data, products=products)

        flash('店铺信息更新成功', 'success')
        return redirect(url_for('.mine'))

    return render_template('shop/mine.html', form=form, shop=shop_data, products=products)


@shop.route('/mine/delete', methods=['POST'])
@login_required
def delete_mine():
    shop_data = get_current_user_shop()
    if shop_data is None:
        flash('你还没有店铺', 'danger')
        return redirect(url_for('.create'))

    products_resp = TbMall(current_app).get_json('/products', params={
        'shop_id': shop_data['id'],
        'limit': 1,
        'offset': 0,
    }, check_code=False)
    if products_resp.get('data', {}).get('total', 0) > 0:
        flash('店铺下还有商品，请先删除商品后再删除店铺', 'danger')
        return redirect(url_for('.mine'))

    delete_resp = TbMall(current_app).delete_json('/shops/{}'.format(shop_data['id']), check_code=False)
    if delete_resp['code'] != 0:
        flash(delete_resp['message'], 'danger')
        return redirect(url_for('.mine'))

    flash('店铺删除成功', 'success')
    return redirect(url_for('common.index'))


def full_shop_info(shops):
    user_ids = [shop['user_id'] for shop in shops]
    if len(user_ids) > 0:
        # 批量查询多个店铺的店主信息
        resp = TbUser(current_app).get_json('/users/infos', params={
            'ids': ','.join([str(v) for v in user_ids]),
        })
        for shop in shops:
            shop['user'] = resp['data']['users'].get(str(shop['user_id']))

    # 每个店铺选取三个商品来展示
    for shop in shops:
        r = TbMall(current_app).get_json('/products', params={
            'shop_id': shop['id'],
            'limit': 3
        })
        shop['products'] = r['data']['products']

    return shops
