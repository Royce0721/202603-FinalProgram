from flask import Blueprint, request, current_app
from sqlalchemy import or_
from werkzeug.exceptions import BadRequest

from tblib.model import session
from tblib.handler import json_response, ResponseCode

from ..models.user import User, UserSchema
from ..models.wallet_transaction import WalletTransaction, WalletTransactionSchema

user = Blueprint('user', __name__, url_prefix='/users')


@user.route('', methods=['POST'])
def create_user():
    """注册用户
    """

    # 获取通过http协议传递过来的json数据
    data = request.get_json()
    # 在获取的数据中把 password 一项删除掉，在删除时把 password 对应的值赋值给 password 变量
    password = data.pop('password')

    # 反序列化，使用 load() 方法完成 dict 到 dict 的转换
    user = UserSchema().load(data)
    # 给 user 对象添加密码
    user.password = password
    # 添加用户对象
    session.add(user)
    # 提交用户对象到 flask-sqlalchemy
    session.commit()
    # 序列化user对象后给浏览器返回
    return json_response(user=UserSchema().dump(user))


@user.route('', methods=['GET'])
def user_list():
    """查询用户列表，可通过用户名、手机等字段进行筛选
    """

    # 通过 request.args.get(key, default=None, type=None) 方法获取使用 get 方法传递过来的参数
    username = request.args.get('username')
    mobile = request.args.get('mobile')
    # 排序方式
    order_direction = request.args.get('order_direction', 'desc')
    # 查询数量，如果没有就设置一个默认值
    limit = request.args.get(
        'limit', current_app.config['PAGINATION_PER_PAGE'], type=int)
    # 查询偏移起始值，默认为 0
    offset = request.args.get('offset', 0, type=int)

    # 设置排序方式，默认为降序
    order_by = User.id.asc() if order_direction == 'asc' else User.id.desc()
    # 查询接口
    query = User.query
    # 如果用户名不为空，使用 username 对查询结果过滤
    if username is not None and username != '':
        query = query.filter(User.username.ilike('%{}%'.format(username)))
    # 如果手机号不为空，使用 mobile 对查询结果过滤
    if mobile is not None and mobile != '':
        query = query.filter(User.mobile.ilike('%{}%'.format(mobile)))
    # 统计数量
    total = query.count()
    # 进行查询
    query = query.order_by(order_by).limit(limit).offset(offset)
    # 对查询的结果序列化并返回
    return json_response(users=UserSchema().dump(query, many=True), total=total)


@user.route('/<int:id>', methods=['POST'])
def update_user(id):
    """更新用户
    """

    data = request.get_json()
    allowed_fields = {'username', 'password', 'avatar', 'gender', 'mobile', 'wallet_money'}

    user = User.query.get(id)
    # 如果用户不存在，返回不存在的结果
    if user is None:
        return json_response(ResponseCode.NOT_FOUND)
    # 使用内置函数 setattr(object, name, value) 设置对象的属性值
    for key, value in data.items():
        if key not in allowed_fields:
            continue
        setattr(user, key, value)
    # 更新数据库
    session.commit()
    # 对更新后的 user 对象进行序列化并返回
    return json_response(user=UserSchema().dump(user))


@user.route('/<int:id>', methods=['GET'])
def user_info(id):
    """查询用户
    """

    user = User.query.get(id)
    if user is None:
        return json_response(ResponseCode.NOT_FOUND)

    return json_response(user=UserSchema().dump(user))


@user.route('/infos', methods=['GET'])
def user_infos():
    """批量查询用户，查询指定 ID 列表里的多个用户
    """

    # 新建一个 ids 的空列表
    ids = []
    # 获取传递过来的 ids，并以逗号分隔，并遍历
    for v in request.args.get('ids', '').split(','):
        # 去除首尾空格
        id = int(v.strip())
        # 如果 id 大于 0 ，则添加到列表中
        if id > 0:
            ids.append(id)
    # 如果列表长度为 0，抛出异常
    if len(ids) == 0:
        raise BadRequest()
    # in_ 用于包含查找
    query = User.query.filter(User.id.in_(ids))
    # 字典推导式，对每一个 user 进行序列化
    users = {user.id: UserSchema().dump(user)
             for user in query}

    return json_response(users=users)


@user.route('/check_password', methods=['GET'])
def check_password():
    """验证用户名和密码是否匹配
    """

    username = request.args.get('username')
    password = request.args.get('password')
    if username is None or password is None:
        return json_response(isCorrect=False)

    # first() 取返回列表中的第一个元素
    user = User.query.filter(User.username == username).first()
    if user is None:
        return json_response(isCorrect=False)
    # 验证密码，返回布尔值
    isCorrect = user.check_password(password)

    return json_response(isCorrect=isCorrect, user=UserSchema().dump(user) if isCorrect else None)
