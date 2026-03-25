from flask import Blueprint, request, current_app
from sqlalchemy import or_

from tblib.model import session
from tblib.handler import json_response, ResponseCode

from ..models import Order, OrderSchema, OrderProduct, OrderProductSchema

order = Blueprint('order', __name__, url_prefix='/orders')


@order.route('', methods=['POST'])
def create_order():
    """创建订单，订单商品需要一起提交
    """

    data = request.get_json()
    # 如果没有金额就计算并添加总金额数据
    if data.get('pay_amount') is None:
        # 循环遍历订单商品，取出每个商品的价格和数量进行相乘并求和
        data['pay_amount'] = sum([x['price'] * x['amount']
                                  for x in data['order_products']])

    order = OrderSchema().load(data)
    session.add(order)
    session.commit()

    return json_response(order=OrderSchema().dump(order))


@order.route('', methods=['GET'])
def order_list():
    """订单列表
    """

    user_id = request.args.get('user_id', type=int)
    order_direction = request.args.get('order_direction', 'desc')
    limit = request.args.get(
        'limit', current_app.config['PAGINATION_PER_PAGE'], type=int)
    offset = request.args.get('offset', 0, type=int)

    order_by = Order.id.asc() if order_direction == 'asc' else Order.id.desc()
    query = Order.query
    # 如果 user_id 非空，就根据 user_id 查询订单列表
    if user_id is not None:
        query = query.filter(Order.user_id == user_id)
    total = query.count()
    query = query.order_by(order_by).limit(limit).offset(offset)

    return json_response(orders=OrderSchema().dump(query, many=True), total=total)


@order.route('/<int:id>', methods=['POST'])
def update_order(id):
    """更新订单，支持部分更新，但只能更新地址、备注、状态等信息
    注意订单商品要么不更新，要么整体一起更新
    """

    data = request.get_json()
    # 根据 id 号查询对应的订单
    order = Order.query.get(id)
    # 如果订单不存在，响应“未发现”
    if order is None:
        return json_response(ResponseCode.NOT_FOUND)
    # 修改地址
    if data.get('address_id') is not None:
        order.address_id = data.get('address_id')
    # 修改备注
    if data.get('note') is not None:
        order.note = data.get('note')
    # 修改订单状态
    if data.get('status') is not None:
        order.status = data.get('status')

    # 如果商品订单不为空：
    if data.get('order_products') is not None:
        order_products = []
        # 循环遍历商品订单
        for op in data.get('order_products'):
            # 根据 id 获取商品订单
            order_product = OrderProduct.query.get(op.get('id'))
            # 如果商品订单为空，返回响应“未找到”
            if order_product is None:
                return json_response(ResponseCode.NOT_FOUND)
            # 更新商品的数量
            if op.get('amount') is not None:
                order_product.amount = op.get('amount')
            # 更新商品的价格
            if op.get('price') is not None:
                order_product.price = op.get('price')
            order_products.append(order_product)
        order.order_products = order_products

    session.commit()

    return json_response(order=OrderSchema().dump(order))


@order.route('/<int:id>', methods=['GET'])
def order_info(id):
    """查询订单
    """

    order = Order.query.get(id)
    if order is None:
        return json_response(ResponseCode.NOT_FOUND)

    return json_response(order=OrderSchema().dump(order))

