from functools import wraps

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from tblib.money import to_money

from ..forms import AdminOrderForm, AdminUserForm, ProductForm, ShopForm
from ..services import TbBuy, TbFile, TbMall, TbUser

admin = Blueprint('admin', __name__, url_prefix='/admin')


def has_uploaded_file(field):
    file_data = getattr(field, 'data', None)
    return bool(file_data and getattr(file_data, 'filename', ''))


def upload_file(file_storage):
    return TbFile(current_app).post_json('/files', files={
        'file': (secure_filename(file_storage.filename), file_storage, file_storage.mimetype),
    }, check_code=False)


def upload_multiple_files(files):
    uploaded_ids = []
    for file_storage in files or []:
        if not getattr(file_storage, 'filename', ''):
            continue
        upload_resp = upload_file(file_storage)
        if upload_resp.get('code') != 0:
            return upload_resp, uploaded_ids
        uploaded_ids.append(upload_resp['data']['id'])
    return {'code': 0, 'data': {}}, uploaded_ids


def product_gallery(product):
    gallery = []
    if product.get('cover'):
        gallery.append(product['cover'])
    for image_id in product.get('extra_images', []):
        if image_id and image_id not in gallery:
            gallery.append(image_id)
    return gallery


def unique_image_ids(image_ids):
    ordered = []
    for image_id in image_ids:
        if image_id and image_id not in ordered:
            ordered.append(image_id)
    return ordered


def resolve_product_images(product_data, new_cover_field=None, new_extra_image_fields=None, image_action='', image_id=''):
    cover_id = product_data.get('cover') or ''
    extra_images = unique_image_ids(product_data.get('extra_images', []))
    extra_images = [value for value in extra_images if value != cover_id]

    if image_action == 'delete' and image_id:
        if image_id == cover_id:
            cover_id = ''
        extra_images = [value for value in extra_images if value != image_id]
    elif image_action == 'set_cover' and image_id and image_id != cover_id and image_id in extra_images:
        extra_images = [value for value in extra_images if value != image_id]
        if cover_id:
            extra_images.insert(0, cover_id)
        cover_id = image_id

    gallery_resp, uploaded_image_ids = upload_multiple_files(new_extra_image_fields or [])
    if gallery_resp.get('code') != 0:
        return gallery_resp, None

    if new_cover_field is not None and has_uploaded_file(new_cover_field):
        f = new_cover_field.data
        upload_resp = upload_file(f)
        if upload_resp.get('code') != 0:
            return upload_resp, None
        if cover_id:
            extra_images.insert(0, cover_id)
        cover_id = upload_resp['data']['id']

    for uploaded_image_id in uploaded_image_ids:
        if uploaded_image_id and uploaded_image_id != cover_id and uploaded_image_id not in extra_images:
            extra_images.append(uploaded_image_id)

    if not cover_id and extra_images:
        cover_id = extra_images[0]
        extra_images = extra_images[1:]

    return {'code': 0, 'data': {}}, {
        'cover': cover_id,
        'extra_images': extra_images,
    }


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


def fetch_user_or_404(id):
    resp = TbUser(current_app).get_json(f'/users/{id}', check_code=False)
    user = resp.get('data', {}).get('user')
    if resp.get('code') != 0 or user is None:
        abort(404)
    return user


def fetch_shop_or_404(id):
    resp = TbMall(current_app).get_json(f'/shops/{id}', check_code=False)
    shop = resp.get('data', {}).get('shop')
    if resp.get('code') != 0 or shop is None:
        abort(404)
    return shop


def fetch_product_or_404(id):
    resp = TbMall(current_app).get_json(f'/products/{id}', check_code=False)
    product = resp.get('data', {}).get('product')
    if resp.get('code') != 0 or product is None:
        abort(404)
    return product


def fetch_order_or_404(id):
    resp = TbBuy(current_app).get_json(f'/orders/{id}', check_code=False)
    order = resp.get('data', {}).get('order')
    if resp.get('code') != 0 or order is None:
        abort(404)
    return order


@admin.route('')
@admin_required
def index():
    users_resp = TbUser(current_app).get_json('/users', params={'limit': 1, 'offset': 0}, check_code=False)
    shops_resp = TbMall(current_app).get_json('/shops', params={'limit': 1, 'offset': 0}, check_code=False)
    products_resp = TbMall(current_app).get_json('/products', params={'limit': 1, 'offset': 0}, check_code=False)
    orders_resp = TbBuy(current_app).get_json('/orders', params={'limit': 1, 'offset': 0}, check_code=False)
    transactions_resp = TbUser(current_app).get_json('/wallet_transactions', params={'limit': 1, 'offset': 0}, check_code=False)
    recent_users_resp = TbUser(current_app).get_json('/users', params={'limit': 5, 'offset': 0}, check_code=False)
    recent_shops_resp = TbMall(current_app).get_json('/shops', params={'limit': 5, 'offset': 0}, check_code=False)
    recent_products_resp = TbMall(current_app).get_json('/products', params={'limit': 5, 'offset': 0}, check_code=False)

    stats = {
        'users': users_resp.get('data', {}).get('total', 0),
        'shops': shops_resp.get('data', {}).get('total', 0),
        'products': products_resp.get('data', {}).get('total', 0),
        'orders': orders_resp.get('data', {}).get('total', 0),
        'transactions': transactions_resp.get('data', {}).get('total', 0),
    }

    recent_users = recent_users_resp.get('data', {}).get('users', [])
    recent_shops = recent_shops_resp.get('data', {}).get('shops', [])
    recent_products = recent_products_resp.get('data', {}).get('products', [])

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
    username = request.args.get('username', '').strip()
    mobile = request.args.get('mobile', '').strip()
    resp = TbUser(current_app).get_json('/users', params={
        'username': username or None,
        'mobile': mobile or None,
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

    return render_template(
        'admin/users.html',
        users=users,
        total=total,
        page=page,
        username=username,
        mobile=mobile,
    )


@admin.route('/shops')
@admin_required
def shops():
    page, limit, offset = paginate_params()
    keywords = request.args.get('keywords', '').strip()
    user_id = request.args.get('user_id', type=int)
    resp = TbMall(current_app).get_json('/shops', params={
        'keywords': keywords,
        'user_id': user_id,
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

    return render_template(
        'admin/shops.html',
        shops=shops,
        total=total,
        page=page,
        keywords=keywords,
        user_id=user_id,
    )


@admin.route('/products')
@admin_required
def products():
    page, limit, offset = paginate_params()
    keywords = request.args.get('keywords', '').strip()
    shop_id = request.args.get('shop_id', type=int)
    resp = TbMall(current_app).get_json('/products', params={
        'keywords': keywords,
        'shop_id': shop_id,
        'limit': limit,
        'offset': offset,
    }, check_code=False)
    products = enrich_products_with_shops(resp.get('data', {}).get('products', []))
    total = resp.get('data', {}).get('total', 0)
    return render_template(
        'admin/products.html',
        products=products,
        total=total,
        page=page,
        keywords=keywords,
        shop_id=shop_id,
    )


@admin.route('/orders')
@admin_required
def orders():
    page, limit, offset = paginate_params()
    user_id = request.args.get('user_id', type=int)
    status = request.args.get('status', '').strip()
    keywords = request.args.get('keywords', '').strip()
    resp = TbBuy(current_app).get_json('/orders', params={
        'user_id': user_id,
        'status': status,
        'keywords': keywords,
        'limit': limit,
        'offset': offset,
    }, check_code=False)
    orders = enrich_orders(resp.get('data', {}).get('orders', []))
    total = resp.get('data', {}).get('total', 0)
    return render_template(
        'admin/orders.html',
        orders=orders,
        total=total,
        page=page,
        user_id=user_id,
        status=status,
        keywords=keywords,
    )


@admin.route('/transactions')
@admin_required
def transactions():
    page, limit, offset = paginate_params()
    user_id = request.args.get('user_id', type=int)
    keywords = request.args.get('keywords', '').strip()
    resp = TbUser(current_app).get_json('/wallet_transactions', params={
        'user_id': user_id,
        'keywords': keywords,
        'limit': limit,
        'offset': offset,
    }, check_code=False)
    transactions = resp.get('data', {}).get('wallet_transactions', [])
    total = resp.get('data', {}).get('total', 0)
    return render_template(
        'admin/transactions.html',
        transactions=transactions,
        total=total,
        page=page,
        user_id=user_id,
        keywords=keywords,
    )


@admin.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(id):
    user = fetch_user_or_404(id)
    form = AdminUserForm(data={
        'username': user.get('username'),
        'gender': user.get('gender') or '',
        'mobile': user.get('mobile') or '',
        'wallet_money': to_money(user.get('wallet_money') or 0),
    })

    if form.validate_on_submit():
        resp = TbUser(current_app).post_json(f'/users/{id}', json={
            'username': form.username.data,
            'gender': form.gender.data,
            'mobile': form.mobile.data,
            'wallet_money': form.wallet_money.data,
        }, check_code=False)
        if resp.get('code') != 0:
            flash(resp.get('message', '用户更新失败'), 'danger')
        else:
            flash('用户信息已更新', 'success')
            return redirect(url_for('.users'))

    return render_template('admin/user_edit.html', form=form, user=user)


@admin.route('/shops/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_shop(id):
    shop = fetch_shop_or_404(id)
    form = ShopForm(data={
        'name': shop.get('name'),
        'description': shop.get('description'),
    })

    if form.validate_on_submit():
        payload = {
            'name': form.name.data,
            'description': form.description.data,
        }
        if has_uploaded_file(form.cover):
            f = form.cover.data
            upload_resp = TbFile(current_app).post_json('/files', files={
                'file': (secure_filename(f.filename), f, f.mimetype),
            }, check_code=False)
            if upload_resp.get('code') != 0:
                flash(upload_resp.get('message', '店铺封面上传失败'), 'danger')
                return render_template('admin/shop_edit.html', form=form, shop=shop)
            payload['cover'] = upload_resp['data']['id']
        resp = TbMall(current_app).post_json(f'/shops/{id}', json=payload, check_code=False)
        if resp.get('code') != 0:
            flash(resp.get('message', '店铺更新失败'), 'danger')
        else:
            flash('店铺信息已更新', 'success')
            return redirect(url_for('.shops'))

    return render_template('admin/shop_edit.html', form=form, shop=shop)


@admin.route('/shops/<int:id>/delete', methods=['POST'])
@admin_required
def delete_shop(id):
    resp = TbMall(current_app).delete_json(f'/shops/{id}', check_code=False)
    if resp.get('code') != 0:
        flash(resp.get('message', '店铺删除失败'), 'danger')
        return redirect(url_for('.edit_shop', id=id))

    flash('店铺已删除', 'success')
    return redirect(url_for('.shops'))


@admin.route('/products/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_product(id):
    product = fetch_product_or_404(id)
    form = ProductForm(data={
        'title': product.get('title'),
        'description': product.get('description'),
        'category': product.get('category'),
        'sku_text': product.get('sku_text'),
        'price': to_money(product.get('price')),
        'amount': product.get('amount'),
    })

    if form.validate_on_submit():
        image_action = request.form.get('image_action', '').strip()
        payload = {
            'title': form.title.data,
            'description': form.description.data,
            'category': form.category.data,
            'sku_text': form.sku_text.data,
            'price': form.price.data,
            'amount': form.amount.data,
        }
        image_resp, image_payload = resolve_product_images(
            product,
            form.cover,
            form.extra_images.data,
            image_action,
            request.form.get('image_id', '').strip(),
        )
        if image_resp.get('code') != 0:
            flash(image_resp.get('message', '商品图片上传失败'), 'danger')
            return render_template('admin/product_edit.html', form=form, product=product, gallery=product_gallery(product))
        payload.update(image_payload)
        resp = TbMall(current_app).post_json(f'/products/{id}', json=payload, check_code=False)
        if resp.get('code') != 0:
            flash(resp.get('message', '商品更新失败'), 'danger')
        else:
            flash('商品信息已更新', 'success')
            return redirect(url_for('.products'))

    return render_template('admin/product_edit.html', form=form, product=product, gallery=product_gallery(product))


@admin.route('/products/<int:id>/images', methods=['POST'])
@admin_required
def update_product_images(id):
    product = fetch_product_or_404(id)
    image_resp, image_payload = resolve_product_images(
        product,
        image_action=request.form.get('image_action', '').strip(),
        image_id=request.form.get('image_id', '').strip(),
    )
    if image_resp.get('code') != 0:
        flash(image_resp.get('message', '商品图片更新失败'), 'danger')
        return redirect(url_for('.edit_product', id=id))

    resp = TbMall(current_app).post_json(f'/products/{id}', json=image_payload, check_code=False)
    if resp.get('code') != 0:
        flash(resp.get('message', '商品图片更新失败'), 'danger')
    else:
        flash('商品图片已更新', 'success')

    return redirect(url_for('.edit_product', id=id))


@admin.route('/products/<int:id>/delete', methods=['POST'])
@admin_required
def delete_product(id):
    resp = TbMall(current_app).delete_json(f'/products/{id}', check_code=False)
    if resp.get('code') != 0:
        flash(resp.get('message', '商品删除失败'), 'danger')
        return redirect(url_for('.edit_product', id=id))

    flash('商品已删除', 'success')
    return redirect(url_for('.products'))


@admin.route('/orders/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_order(id):
    order = fetch_order_or_404(id)
    form = AdminOrderForm(data={
        'status': order.get('status'),
        'note': order.get('note') or '',
    })

    if form.validate_on_submit():
        resp = TbBuy(current_app).post_json(f'/orders/{id}', json={
            'status': form.status.data,
            'note': form.note.data,
        }, check_code=False)
        if resp.get('code') != 0:
            flash(resp.get('message', '订单更新失败'), 'danger')
        else:
            flash('订单信息已更新', 'success')
            return redirect(url_for('.orders'))

    return render_template('admin/order_edit.html', form=form, order=order)
