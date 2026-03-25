from flask import Blueprint, request

from tblib.handler import json_response

from ..models import OrderProduct

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
