# handlers/product.py

from flask import Blueprint, request, current_app, render_template, redirect, url_for, flash
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from tblib.money import to_money

from ..forms import ProductForm
from ..forms.product import PRODUCT_CATEGORY_CHOICES
from ..services import TbBuy, TbFile, TbMall, TbUser
from .sales import enrich_products_with_sales

product = Blueprint('product', __name__, url_prefix='/products')
PRODUCTS_PER_PAGE = 24


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


def product_gallery(product_data):
    gallery = []
    if product_data.get('cover'):
        gallery.append(product_data['cover'])
    for image_id in product_data.get('extra_images', []):
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
        if upload_resp['code'] != 0:
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
    keywords = request.args.get('keywords', '')
    category = request.args.get('category', '').strip()

    page = request.args.get('page', 1, type=int)

    limit = PRODUCTS_PER_PAGE
    offset = (page - 1) * limit
    resp = TbMall(current_app).get_json('/products', params={
        'keywords': keywords,
        'category': category,
        'limit': limit,
        'offset': offset
    })
    enrich_products_with_sales(resp.get('data', {}).get('products', []))

    category_options = [('', '全部分类')] + [
        choice for choice in PRODUCT_CATEGORY_CHOICES if choice[0] != ''
    ] + [('__uncategorized__', '未分类')]

    return render_template(
        'product/index.html',
        **resp['data'],
        keywords=keywords,
        category=category,
        category_options=category_options,
        per_page=limit,
    )



@product.route('/<int:id>')
def detail(id):
    """商品详情
    """

    # 向后台商场服务查询对应商品id的详情
    resp = TbMall(current_app).get_json('/products/{}'.format(id))
    product_data = resp['data']['product']
    enrich_products_with_sales([product_data])

    reviews_resp = TbBuy(current_app).get_json('/reviews', params={
        'product_id': id,
        'limit': 20,
        'offset': 0,
    }, check_code=False)
    reviews = reviews_resp.get('data', {}).get('reviews', [])

    user_ids = sorted({review['user_id'] for review in reviews if review.get('user_id') is not None})
    users = {}
    if user_ids:
        users_resp = TbUser(current_app).get_json('/users/infos', params={
            'ids': ','.join([str(v) for v in user_ids]),
        }, check_code=False)
        users = users_resp.get('data', {}).get('users', {})

    for review in reviews:
        review['user'] = users.get(str(review['user_id']))

    review_count = len(reviews)
    average_rating = round(sum([review.get('rating', 5) for review in reviews]) / review_count, 1) if review_count else 0

    return render_template(
        'product/detail.html',
        product=product_data,
        gallery=product_gallery(product_data),
        reviews=reviews,
        review_count=review_count,
        average_rating=average_rating,
    )


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
    enrich_products_with_sales(resp.get('data', {}).get('products', []))
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
        gallery_resp, extra_image_ids = upload_multiple_files(form.extra_images.data)
        if gallery_resp.get('code') != 0:
            flash(gallery_resp.get('message', '商品图片上传失败'), 'danger')
            return render_template('product/create.html', form=form, shop=shop)

        if has_uploaded_file(form.cover):
            f = form.cover.data
            upload_resp = upload_file(f)
            if upload_resp['code'] != 0:
                flash(upload_resp['message'], 'danger')
                return render_template('product/create.html', form=form, shop=shop)
            cover = upload_resp['data']['id']
        elif extra_image_ids:
            cover = extra_image_ids[0]
            extra_image_ids = extra_image_ids[1:]

        resp = TbMall(current_app).post_json('/products', json={
            'title': form.title.data,
            'description': form.description.data,
            'category': form.category.data,
            'sku_text': form.sku_text.data,
            'price': form.price.data,
            'amount': form.amount.data,
            'cover': cover,
            'extra_images': extra_image_ids,
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
        'category': product_data.get('category'),
        'sku_text': product_data.get('sku_text'),
        'price': to_money(product_data.get('price')),
        'amount': product_data.get('amount'),
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
            product_data,
            form.cover,
            form.extra_images.data,
            image_action,
            request.form.get('image_id', '').strip(),
        )
        if image_resp.get('code') != 0:
            flash(image_resp.get('message', '商品图片上传失败'), 'danger')
            return render_template('product/edit.html', form=form, shop=shop, product=product_data, gallery=product_gallery(product_data))
        payload.update(image_payload)

        update_resp = TbMall(current_app).post_json('/products/{}'.format(id), json=payload, check_code=False)
        if update_resp['code'] != 0:
            flash(update_resp['message'], 'danger')
            return render_template('product/edit.html', form=form, shop=shop, product=product_data, gallery=product_gallery(product_data))

        flash('商品更新成功', 'success')
        return redirect(url_for('.mine'))

    return render_template('product/edit.html', form=form, shop=shop, product=product_data, gallery=product_gallery(product_data))


@product.route('/<int:id>/images', methods=['POST'])
@login_required
def update_images(id):
    shop = get_current_user_shop()
    if shop is None:
        flash('你还没有店铺，先去开店吧', 'info')
        return redirect(url_for('shop.create'))

    resp = TbMall(current_app).get_json('/products/{}'.format(id), check_code=False)
    product_data = resp.get('data', {}).get('product')
    if product_data is None or product_data.get('shop_id') != shop['id']:
        flash('未找到该商品，或你无权编辑它', 'danger')
        return redirect(url_for('.mine'))

    image_resp, image_payload = resolve_product_images(
        product_data,
        image_action=request.form.get('image_action', '').strip(),
        image_id=request.form.get('image_id', '').strip(),
    )
    if image_resp.get('code') != 0:
        flash(image_resp.get('message', '商品图片更新失败'), 'danger')
        return redirect(url_for('.edit', id=id))

    update_resp = TbMall(current_app).post_json('/products/{}'.format(id), json=image_payload, check_code=False)
    if update_resp.get('code') != 0:
        flash(update_resp.get('message', '商品图片更新失败'), 'danger')
    else:
        flash('商品图片已更新', 'success')

    return redirect(url_for('.edit', id=id))


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
