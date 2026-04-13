# 导入处理异常栈的模块
import traceback

# 导入 jsonify 模块，可以将其它类型数据转换为 json 格式
from flask import jsonify
from .money import normalize_money_data

class ResponseCode:
    OK = 0
    ERROR = 1
    NOT_FOUND = 10
    TRANSACTION_FAILURE = 20
    QUANTITY_EXCEEDS_LIMIT = 30
    NO_ENOUGH_MONEY = 40

    MESSAGES = {
        OK: '成功',
        ERROR: '未知错误',
        NOT_FOUND: '资源未找到',
        TRANSACTION_FAILURE: '执行事务失败',
        QUANTITY_EXCEEDS_LIMIT: '数量超过限制',
        NO_ENOUGH_MONEY: '余额不足'
    }


def json_response(code=ResponseCode.OK, message='', **kwargs):
    return jsonify(normalize_money_data({
        'code': code,
        'message': message or ResponseCode.MESSAGES.get(code, ''),
        'data': kwargs
    }))


def handle_error_json(exception):
    traceback.print_exc()   # 打印异常信息
    return json_response(ResponseCode.ERROR, str(exception))
