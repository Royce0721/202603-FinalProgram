from flask import Blueprint, request
from sqlalchemy import func

from tblib.handler import json_response

from ..models import Order, OrderProduct

order_product = Blueprint('order_product', __name__, url_prefix='/order_products')


@order_product.route('/exists', methods=['GET'])
def exists():
    product_ids = []
    for value in request.args.get('product_ids', '').split(','):
        value = value.strip()
        if not value:
            continue
        pid = int(value)
        if pid > 0:
            product_ids.append(pid)

    if len(product_ids) == 0:
        return json_response(has_refs=False, ref_product_ids=[])

    rows = OrderProduct.query.filter(OrderProduct.product_id.in_(product_ids)).all()
    ref_product_ids = sorted({row.product_id for row in rows})
    return json_response(has_refs=len(ref_product_ids) > 0, ref_product_ids=ref_product_ids)


@order_product.route('/sales', methods=['GET'])
def sales():
    limit = request.args.get('limit', 20, type=int)
    user_id = request.args.get('user_id', type=int)

    valid_statuses = ['paied', 'delivered', 'received', 'commented']
    query = (
        OrderProduct.query
        .join(Order, OrderProduct.order_id == Order.id)
        .filter(Order.status.in_(valid_statuses))
    )

    if user_id is not None:
        query = query.filter(Order.user_id == user_id)

    rows = (
        query.with_entities(
            OrderProduct.product_id.label('product_id'),
            func.sum(OrderProduct.amount).label('sales'),
        )
        .group_by(OrderProduct.product_id)
        .order_by(func.sum(OrderProduct.amount).desc(), OrderProduct.product_id.desc())
        .limit(limit)
        .all()
    )

    return json_response(product_sales=[
        {
            'product_id': row.product_id,
            'sales': int(row.sales or 0),
        } for row in rows
    ])
