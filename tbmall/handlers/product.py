from flask import Blueprint, request, current_app
from sqlalchemy import or_
from werkzeug.exceptions import BadRequest

from tblib.model import db
from tblib.handler import json_response, ResponseCode

from ..models import Product, ProductExtra, ProductSchema, Shop, ShopSchema
from ..services import TbBuy

product = Blueprint('product', __name__, url_prefix='/products')


def normalize_gallery(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [item for item in value.split(',') if item]
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return []


def ensure_product_extra(product):
    if product.extra is None:
        product.extra = ProductExtra(product_id=product.id)
    return product.extra


@product.route('', methods=['POST'])
def create_product():
    """创建商品
    """
    data = request.get_json()
    shop = db.session.query(Shop).filter(Shop.id == data.get('shop_id')).first()
    if shop is None:
        return json_response(ResponseCode.NOT_FOUND, '店铺不存在')

    product_data = {
        'title': data.get('title'),
        'description': data.get('description'),
        'cover': data.get('cover') or '',
        'price': data.get('price'),
        'amount': data.get('amount'),
        'shop_id': data.get('shop_id'),
    }
    product = ProductSchema().load(product_data)
    db.session.add(product)
    db.session.commit()

    extra = ensure_product_extra(product)
    extra.gallery = ','.join(normalize_gallery(data.get('extra_images')))
    extra.sku_text = (data.get('sku_text') or '').strip()
    extra.category = (data.get('category') or '').strip()
    db.session.commit()

    return json_response(product=ProductSchema().dump(product))


@product.route('', methods=['GET'])
def product_list():
    """查询商品列表，可根据店铺 ID等条件来筛选
    """
    shop_id = request.args.get('shop_id', type=int)
    keywords = request.args.get('keywords', '')
    category = request.args.get('category', '').strip()

    order_direction = request.args.get('order_direction', 'desc')
    limit = request.args.get(
        'limit', current_app.config['PAGINATION_PER_PAGE'], type=int
    )
    offset = request.args.get('offset', 0, type=int)

    order_by = Product.id.asc() if order_direction == 'asc' else Product.id.desc()
    query = db.session.query(Product)

    if shop_id is not None:
        query = query.filter(Product.shop_id == shop_id)

    if keywords != '':
        like_keywords = '%{}%'.format(keywords)
        query = query.filter(
            or_(
                Product.title.ilike(like_keywords),
                Product.description.ilike(like_keywords)
            )
        )

    if category == '__uncategorized__':
        query = query.outerjoin(ProductExtra, Product.extra).filter(
            or_(ProductExtra.id.is_(None), ProductExtra.category == '')
        )
    elif category != '':
        query = query.join(ProductExtra, Product.extra).filter(ProductExtra.category == category)

    total = query.count()
    products = query.order_by(order_by).limit(limit).offset(offset).all()

    return json_response(products=ProductSchema().dump(products, many=True), total=total)


@product.route('/<int:id>', methods=['POST'])
def update_product(id):
    """更新商品
    """
    data = request.get_json()

    product = db.session.query(Product).filter(Product.id == id).first()
    if product is None:
        return json_response(ResponseCode.NOT_FOUND)

    allowed_fields = {'title', 'description', 'cover', 'price', 'amount'}
    for k, v in data.items():
        if k not in allowed_fields:
            continue
        setattr(product, k, v)

    if 'extra_images' in data or 'sku_text' in data:
        extra = ensure_product_extra(product)
        if 'extra_images' in data:
            extra.gallery = ','.join(normalize_gallery(data.get('extra_images')))
        if 'sku_text' in data:
            extra.sku_text = (data.get('sku_text') or '').strip()
    if 'category' in data:
        extra = ensure_product_extra(product)
        extra.category = (data.get('category') or '').strip()

    db.session.commit()

    return json_response(product=ProductSchema().dump(product))


@product.route('/<int:id>', methods=['GET'])
def product_info(id):
    """查询商品
    """
    product = db.session.query(Product).filter(Product.id == id).first()
    if product is None:
        return json_response(ResponseCode.NOT_FOUND)

    return json_response(product=ProductSchema().dump(product))


@product.route('/<int:id>', methods=['DELETE'])
def delete_product(id):
    """删除商品
    """
    product = db.session.query(Product).filter(Product.id == id).first()
    if product is None:
        return json_response(ResponseCode.NOT_FOUND)

    db.session.delete(product)
    db.session.commit()

    return json_response()


@product.route('/infos', methods=['GET'])
def product_infos():
    """批量查询商品，查询指定 ID 列表里的多个商品
    """
    ids = []
    for v in request.args.get('ids', '').split(','):
        v = v.strip()
        if not v:
            continue
        pid = int(v)
        if pid > 0:
            ids.append(pid)

    if len(ids) == 0:
        return json_response(products={})

    query = db.session.query(Product).filter(Product.id.in_(ids))
    products = {product.id: ProductSchema().dump(product) for product in query.all()}

    return json_response(products=products)
