from flask import Blueprint, request, current_app
from sqlalchemy import or_

from tblib.model import db
from tblib.handler import json_response, ResponseCode

from ..models import Shop, ShopSchema, Product, ProductSchema

from werkzeug.exceptions import BadRequest

shop = Blueprint('shop', __name__, url_prefix='/shops')


@shop.route('', methods=['POST'])
def create_shop():
    """创建店铺
    """
    data = request.get_json()
    existing_shop = db.session.query(Shop).filter(Shop.user_id == data.get('user_id')).first()
    if existing_shop is not None:
        return json_response(ResponseCode.ERROR, '一个用户只能创建一个店铺')

    shop = ShopSchema().load(data)
    db.session.add(shop)
    db.session.commit()

    return json_response(shop=ShopSchema().dump(shop))


@shop.route('', methods=['GET'])
def shop_list():
    """店铺列表，可根据用户 ID 等条件来筛选
    """
    user_id = request.args.get('user_id', type=int)
    keywords = request.args.get('keywords', '')

    order_direction = request.args.get('order_direction', 'desc')
    limit = request.args.get(
        'limit', current_app.config['PAGINATION_PER_PAGE'], type=int
    )
    offset = request.args.get('offset', 0, type=int)

    order_by = Shop.id.asc() if order_direction == 'asc' else Shop.id.desc()
    query = db.session.query(Shop)

    if user_id is not None:
        query = query.filter(Shop.user_id == user_id)

    if keywords != '':
        like_keywords = '%{}%'.format(keywords)
        query = query.filter(
            or_(
                Shop.name.ilike(like_keywords),
                Shop.description.ilike(like_keywords)
            )
        )

    total = query.count()
    shops = query.order_by(order_by).limit(limit).offset(offset).all()

    return json_response(shops=ShopSchema().dump(shops, many=True), total=total)


@shop.route('/<int:id>', methods=['POST'])
def update_shop(id):
    """更新店铺
    """
    data = request.get_json()

    shop = db.session.query(Shop).filter(Shop.id == id).first()
    if shop is None:
        return json_response(ResponseCode.NOT_FOUND)

    for k, v in data.items():
        setattr(shop, k, v)

    db.session.commit()

    return json_response(shop=ShopSchema().dump(shop))


@shop.route('/<int:id>', methods=['GET'])
def shop_info(id):
    """查询店铺
    """
    shop = db.session.query(Shop).filter(Shop.id == id).first()
    if shop is None:
        return json_response(ResponseCode.NOT_FOUND)

    return json_response(shop=ShopSchema().dump(shop))


@shop.route('/<int:id>', methods=['DELETE'])
def delete_shop(id):
    """删除店铺
    """
    shop = db.session.query(Shop).filter(Shop.id == id).first()
    if shop is None:
        return json_response(ResponseCode.NOT_FOUND)

    if shop.products.count() > 0:
        return json_response(ResponseCode.ERROR, '店铺下还有商品，请先删除商品后再删除店铺')

    db.session.delete(shop)
    db.session.commit()

    return json_response()

@shop.route('/infos', methods=['GET'])
def shop_infos():
    """批量查询店铺，查询指定 ID 列表里的多个店铺
    """

    ids = []
    for v in request.args.get('ids', '').split(','):
        id = int(v.strip())
        if id > 0:
            ids.append(id)
    if len(ids) == 0:
        raise BadRequest()

    query = Shop.query.filter(Shop.id.in_(ids))

    shops = {shop.id: ShopSchema().dump(shop) for shop in query}

    return json_response(shops=shops)
