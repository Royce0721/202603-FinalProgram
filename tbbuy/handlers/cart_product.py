from flask import Blueprint, request, current_app
from sqlalchemy import and_

from tblib.model import session
from tblib.handler import json_response, ResponseCode

from ..models import CartProduct, CartProductSchema

cart_product = Blueprint('cart_product', __name__, url_prefix='/cart_products')


@cart_product.route('', methods=['POST'])
def create_cart_product():
    """添加购物车商品
    """

    data = request.get_json()

    cart_product = CartProductSchema().load(data)

    # 查询某用户对应的所有购物车商品
    cart_products = CartProduct.query.filter(
        CartProduct.user_id == cart_product.user_id).all()

    # 商品是否已在购物车
    # 先默认为不存在
    existed = None
    # 循环遍历用户的所有购物车商品
    for v in cart_products:
        # 如果用户的购物车商品id等于待添加的商品id就记录下这个商品id并退出循环
        if v.product_id == cart_product.product_id:
            existed = v
            break

    # 购物车商品数量不能超过限制
    # 如果现在的购物车商品数量已经大于规定的限制并且要添加的商品是一个新商品，就返回“数量超过限制”
    if len(cart_products) >= current_app.config['CART_PRODUCT_LIMIT'] and existed is None:
        return json_response(ResponseCode.QUANTITY_EXCEEDS_LIMIT)

    # 商品已在购物车则更新数量，否则添加一条新纪录
    if existed is None:
        # 给购物车添加该商品
        session.add(cart_product)
    else:
        # 更新该商品的数量
        existed.amount += cart_product.amount
    session.commit()
    # 序列化并返回响应
    return json_response(cart_product=CartProductSchema().dump(cart_product if existed is None else existed))


@cart_product.route('', methods=['GET'])
def cart_product_list():
    """购物车商品列表
    """

    user_id = request.args.get('user_id', type=int)
    product_id = request.args.get('product_id', type=int)
    order_direction = request.args.get('order_direction', 'desc')

    order_by = CartProduct.id.asc(
    ) if order_direction == 'asc' else CartProduct.id.desc()
    query = CartProduct.query
    if user_id is not None:
        query = query.filter(CartProduct.user_id == user_id)
    if product_id is not None:
        query = query.filter(CartProduct.product_id == product_id)
    total = query.count()
    query = query.order_by(order_by)

    return json_response(cart_products=CartProductSchema().dump(query, many=True), total=total)


@cart_product.route('', methods=['DELETE'])
def delete_cart_products():
    """清空某个用户的购物车商品
    """

    user_id = request.args.get('user_id', type=int)
    # 根据 user_id 删除该用户对应的所有购物车商品
    CartProduct.query.filter(CartProduct.user_id == user_id).delete()
    session.commit()

    return json_response()


@cart_product.route('/<int:id>', methods=['POST'])
def update_cart_product(id):
    """更新购物车商品，比如数量
    """

    data = request.get_json()

    # 根据传入的购物车id更新数据
    count = CartProduct.query.filter(CartProduct.id == id).update(data)
    # 如果未成功更新，返回响应“未发现”
    if count == 0:
        return json_response(ResponseCode.NOT_FOUND)
    cart_product = CartProduct.query.get(id)
    session.commit()

    return json_response(cart_product=CartProductSchema().dump(cart_product))

@cart_product.route('/', methods=['GET'])
def index():
    """购物车列表"""
    cart_products = CartProduct.query.all()
    return json_response(
        total=len(cart_products),
        cart_products=CartProductSchema(many=True).dump(cart_products)
    )


@cart_product.route('/<int:id>', methods=['GET'])
def cart_product_info(id):
    """查询购物车商品"""
    cart_product = CartProduct.query.filter(CartProduct.id == id).first()
    if cart_product is None:
        return json_response(ResponseCode.NOT_FOUND)

    return json_response(cart_product=CartProductSchema().dump(cart_product))

"""查询购物车商品
    """

@cart_product.route('/<int:id>', methods=['DELETE'])
def delete_cart_product(id):
    """删除购物车商品
    """

    cart_product = CartProduct.query.filter(CartProduct.id == id).first()
    if cart_product is None:
        return json_response(ResponseCode.NOT_FOUND)

    # 删除对应的购物车商品
    session.delete(cart_product)
    session.commit()

    return json_response(cart_product=CartProductSchema().dump(cart_product))
