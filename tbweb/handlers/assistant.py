from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user
import requests

from .admin import is_admin_user
from ..services import TbMall

assistant = Blueprint('assistant', __name__, url_prefix='/assistant')


INTENT_RULES = (
    (
        'order',
        ('订单', '下单', '支付', '发货', '收货', '评价', '取消订单', '物流'),
        '订单相关问题优先围绕下单、支付、发货、收货和评价来回答。',
    ),
    (
        'seller',
        ('开店', '商品', '上架', '店铺', '商家', '发布商品', '商品管理'),
        '商家问题优先围绕开店、编辑店铺、发布商品、商品管理和店铺订单来回答。',
    ),
    (
        'account',
        ('登录', '注册', '密码', '头像', '地址', '钱包', '充值', '资料'),
        '账户问题优先围绕登录注册、个人资料、头像、密码、收货地址和钱包来回答。',
    ),
    (
        'admin',
        ('管理员', '后台', '用户管理', '店铺管理', '订单管理', '交易管理'),
        '后台问题优先围绕管理员后台中的用户、店铺、商品、订单和交易管理来回答。',
    ),
)


FAQ_RULES = (
    (
        ('怎么开店', '我要开店', '如何开店', '开店'),
        '登录后打开右上角菜单，点“我要开店”，把店铺信息填好再提交就行。',
    ),
    (
        ('怎么下单', '如何下单', '怎么买', '购买流程'),
        '先把商品加入购物车，在购物车里勾选要结算的商品，点“去结算”，确认地址后提交订单，再完成支付就行。',
    ),
    (
        ('怎么查看订单', '我的订单在哪', '查看订单'),
        '登录后打开右上角菜单，点“我的订单”就能看到自己的订单。',
    ),
    (
        ('怎么发布商品', '如何发布商品', '新增商品', '上架商品'),
        '先开店，然后打开右上角菜单里的“商品管理”，进入后点“新增商品”就可以发布。',
    ),
    (
        ('怎么发货', '如何发货', '店铺订单'),
        '商家登录后打开右上角菜单，进入“店铺订单”，找到订单后按页面提示发货就行。',
    ),
    (
        ('怎么改密码', '修改密码', '密码'),
        '登录后打开右上角菜单，进“修改密码”就可以改。',
    ),
)


def detect_intent(message):
    lowered = (message or '').lower()
    for intent, keywords, _hint in INTENT_RULES:
        if any(keyword.lower() in lowered for keyword in keywords):
            return intent
    return 'general'


def direct_faq_reply(message):
    lowered = (message or '').strip().lower()
    for keywords, answer in FAQ_RULES:
        if any(keyword.lower() in lowered for keyword in keywords):
            return answer
    return ''


def fetch_current_user_role():
    if not current_user.is_authenticated:
        return '访客'
    if is_admin_user():
        return '管理员'
    try:
        resp = TbMall(current_app).get_json('/shops', params={
            'user_id': current_user.get_id(),
            'limit': 1,
            'offset': 0,
        }, check_code=False)
        shops = resp.get('data', {}).get('shops', [])
    except Exception:
        shops = []
    return '商家' if shops else '普通用户'


def build_system_prompt(intent, role, page_name):
    topic_hint = ''
    for rule_intent, _keywords, hint in INTENT_RULES:
        if rule_intent == intent:
            topic_hint = hint
            break

    return '\n'.join([
        '你是仁爱购物网的站内客服助手。',
        '你只回答本站功能相关问题，范围包括：商品浏览、店铺浏览、购物车、下单支付、订单处理、开店、商品管理、管理员后台、个人资料、地址和钱包。',
        '不要编造不存在的页面、按钮、规则或支付能力。',
        '如果问题超出本站范围，请明确说“我目前主要帮助处理本站购物和店铺相关问题”。',
        '回答尽量简短、清楚，先直接回答，再给最多3步操作建议。',
        '不要使用项目、闭环、平台能力这类汇报口吻。',
        f'当前用户角色：{role}。',
        f'当前页面：{page_name or "首页"}。',
        topic_hint,
        '本站已知功能：普通用户可以注册登录、浏览商品和店铺、加入购物车、下单支付、确认收货、按商品评价；商家可以开店、发布和编辑商品、管理商品图片、查看店铺订单并发货；管理员可以管理用户、店铺、商品、订单和交易。',
    ])


def ask_local_model(user_message, system_prompt):
    url = current_app.config['ASSISTANT_BASE_URL'].rstrip('/') + '/api/chat'
    resp = requests.post(
        url,
        json={
            'model': current_app.config['ASSISTANT_MODEL'],
            'stream': False,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_message},
            ],
            'options': {
                'temperature': 0.2,
            },
        },
        timeout=current_app.config['ASSISTANT_TIMEOUT'],
    )
    resp.raise_for_status()
    data = resp.json()
    return (data.get('message') or {}).get('content', '').strip()


@assistant.route('/chat', methods=['POST'])
def chat():
    if not current_app.config.get('ASSISTANT_ENABLED', True):
        return jsonify({'code': 1, 'message': '客服助手暂时不可用', 'data': {}})

    payload = request.get_json(silent=True) or {}
    message = (payload.get('message') or '').strip()
    page_name = (payload.get('page_name') or '').strip()
    if not message:
        return jsonify({'code': 1, 'message': '请输入问题', 'data': {}})

    try:
        direct_answer = direct_faq_reply(message)
        if direct_answer:
            return jsonify({
                'code': 0,
                'message': '成功',
                'data': {
                    'answer': direct_answer,
                    'intent': detect_intent(message),
                },
            })

        role = fetch_current_user_role()
        intent = detect_intent(message)
        system_prompt = build_system_prompt(intent, role, page_name)
        answer = ask_local_model(message, system_prompt)
        if not answer:
            answer = '我先没组织好这句，你可以换个更直接的问法试试。'
        return jsonify({
            'code': 0,
            'message': '成功',
            'data': {
                'answer': answer,
                'intent': intent,
            },
        })
    except requests.RequestException:
        return jsonify({
            'code': 1,
            'message': '本地客服暂时没连上，请稍后再试',
            'data': {},
        })
    except Exception:
        return jsonify({
            'code': 1,
            'message': '客服回复失败，请换个问法试试',
            'data': {},
        })
