from flask import Blueprint, request, current_app
from sqlalchemy import and_, or_

from tblib.model import session
from tblib.handler import json_response, ResponseCode

from ..models.user import User
from ..models.wallet_transaction import WalletTransaction, WalletTransactionSchema

wallet_transaction = Blueprint(
    'wallet_transaction', __name__, url_prefix='/wallet_transactions')


@wallet_transaction.route('', methods=['POST'])
def create_wallet_transaction():
    """创建交易
    """

    data = request.get_json()
    # 反序列化
    wallet_transaction = WalletTransactionSchema().load(data)

    # 采用乐观锁来防止并发情况下可能出现的数据不一致性，也可使用悲观锁（query 时使用 with_for_update），但资源消耗较大
    # 查看付款人 payer 是否存在，如果不存在则返回不存在
    payer = User.query.get(wallet_transaction.payer_id)
    if payer is None:
        return json_response(ResponseCode.NOT_FOUND)

    # 查看收款人 payee 是否存在，如果不存在则返回不存在
    payee = User.query.get(wallet_transaction.payee_id)
    if payee is None:
        return json_response(ResponseCode.NOT_FOUND)

    # and_ 表示必须同时满足：付款人id等于用户id，用户钱包金额大于付款金额，付款人钱包金额等于用户钱包金额；然后更新用户钱包金额；最终返回的是一个布尔值
    count = User.query.filter(
        and_(User.id == payer.id, User.wallet_money >= wallet_transaction.amount,
             User.wallet_money == payer.wallet_money)
    ).update({
        User.wallet_money: payer.wallet_money - wallet_transaction.amount
    })
    # 如果布尔值为 false，表示更新失败，事件回滚，返回'事件执行失败'
    if count == 0:
        session.rollback()
        return json_response(ResponseCode.TRANSACTION_FAILURE)

    # 以相同的方式，更新收款人钱包金额
    count = User.query.filter(
        and_(User.id == payee.id, User.wallet_money == payee.wallet_money)
    ).update({
        User.wallet_money: payee.wallet_money + wallet_transaction.amount
    })
    if count == 0:
        session.rollback()
        return json_response(ResponseCode.TRANSACTION_FAILURE)

    session.add(wallet_transaction)

    session.commit()
    # 序列化并返回对应的响应
    return json_response(wallet_transaction=WalletTransactionSchema().dump(wallet_transaction))


@wallet_transaction.route('', methods=['GET'])
def wallet_transaction_list():
    """查询交易列表
    """

    user_id = request.args.get('user_id', type=int)
    keywords = request.args.get('keywords', '')
    order_direction = request.args.get('order_direction', 'desc')
    limit = request.args.get(
        'limit', current_app.config['PAGINATION_PER_PAGE'], type=int)
    offset = request.args.get('offset', 0, type=int)

    order_by = WalletTransaction.id.asc(
    ) if order_direction == 'asc' else WalletTransaction.id.desc()
    query = WalletTransaction.query
    # 如果用户id非空，满足：用户id等于付款人id,或者用户id等于收款人id，就进行查询
    if user_id is not None:
        query = query.filter(or_(WalletTransaction.payer_id ==
                                 user_id, WalletTransaction.payee_id == user_id))
    if keywords != '':
        query = query.filter(WalletTransaction.note.ilike('%{}%'.format(keywords)))
    total = query.count()
    query = query.order_by(order_by).limit(limit).offset(offset)

    return json_response(wallet_transactions=WalletTransactionSchema().dump(query, many=True), total=total)


@wallet_transaction.route('/<int:id>', methods=['POST'])
def update_wallet_transaction(id):
    """更新交易
    """

    data = request.get_json()

    count = WalletTransaction.query.filter(
        WalletTransaction.id == id).update(data)
    if count == 0:
        return json_response(ResponseCode.NOT_FOUND)
    wallet_transaction = WalletTransaction.query.get(id)
    session.commit()

    return json_response(wallet_transaction=WalletTransactionSchema().dump(wallet_transaction))


@wallet_transaction.route('/<int:id>', methods=['GET'])
def wallet_transaction_info(id):
    """查询交易
    """

    wallet_transaction = WalletTransaction.query.get(id)
    if wallet_transaction is None:
        return json_response(ResponseCode.NOT_FOUND)

    return json_response(wallet_transaction=WalletTransactionSchema().dump(wallet_transaction))
