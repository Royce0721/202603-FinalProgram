from flask import Blueprint, current_app, request

from tblib.handler import ResponseCode, json_response
from tblib.model import session

from ..models import OrderProduct, Review, ReviewExtra, ReviewSchema

review = Blueprint('review', __name__, url_prefix='/reviews')


@review.route('', methods=['POST'])
def create_review():
    data = request.get_json() or {}
    if not data.get('order_id') or not data.get('user_id') or not (data.get('content') or '').strip():
        return json_response(ResponseCode.ERROR, '评价信息不完整')
    rating = int(data.get('rating') or 5)
    if rating < 1 or rating > 5:
        return json_response(ResponseCode.ERROR, '评分范围不合法')

    existing_review = Review.query.filter(Review.order_id == data['order_id']).first()
    if existing_review is not None:
        return json_response(ResponseCode.ERROR, '该订单已经评价过了')

    review_data = ReviewSchema().load({
        'order_id': data['order_id'],
        'user_id': data['user_id'],
        'content': data['content'].strip(),
    })
    session.add(review_data)
    session.commit()

    review_extra = ReviewExtra(review_id=review_data.id, rating=rating)
    session.add(review_extra)
    session.commit()

    return json_response(review=ReviewSchema().dump(review_data))


@review.route('', methods=['GET'])
def review_list():
    order_id = request.args.get('order_id', type=int)
    user_id = request.args.get('user_id', type=int)
    product_id = request.args.get('product_id', type=int)
    limit = request.args.get('limit', current_app.config['PAGINATION_PER_PAGE'], type=int)
    offset = request.args.get('offset', 0, type=int)

    query = Review.query
    if order_id is not None:
        query = query.filter(Review.order_id == order_id)
    if user_id is not None:
        query = query.filter(Review.user_id == user_id)
    if product_id is not None:
        query = query.join(OrderProduct, Review.order_id == OrderProduct.order_id).filter(
            OrderProduct.product_id == product_id
        ).distinct(Review.id)

    total = query.count()
    reviews = query.order_by(Review.id.desc()).limit(limit).offset(offset)
    return json_response(reviews=ReviewSchema().dump(reviews, many=True), total=total)
