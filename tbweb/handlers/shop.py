# handlers/shop.py

from flask import Blueprint, request, current_app, render_template

from ..services import TbMall, TbUser

shop = Blueprint('shop', __name__, url_prefix='/shops')


@shop.route('')
def index():
    """店铺列表
    """
      # 添加了下面一行代码
    keywords = request.args.get('keywords', '')

    page = request.args.get('page', 1, type=int)

    limit = current_app.config['PAGINATION_PER_PAGE']
    offset = (page - 1) * limit
    resp = TbMall(current_app).get_json('/shops', params={
            # 添加了下面一行代码
        'keywords': keywords,

        'limit': limit,
        'offset': offset
    })
    shops = resp['data']['shops']
    total = resp['data']['total']

    user_ids = [shop['user_id'] for shop in shops]
    if len(user_ids) > 0:
        # 批量查询多个店铺的店主信息
        resp = TbUser(current_app).get_json('/users/infos', params={
            'ids': ','.join([str(v) for v in user_ids]),
        })
        for shop in shops:
            shop['user'] = resp['data']['users'].get(str(shop['user_id']))

    # 每个店铺选取三个商品来展示
    for shop in shops:
        r = TbMall(current_app).get_json('/products', params={
            'shop_id': shop['id'],
            'limit': 3
        })
        shop['products'] = r['data']['products']

    # 修改了下面这一行代码
    return render_template('shop/index.html', shops=shops, total=total, keywords=keywords)



@shop.route('/<int:id>')
def detail(id):
    """店铺详情
    """

    # 获取当前页码的编号
    page = request.args.get('page', 1, type=int)

    # 使用 get 方法向后台商场服务查询店铺id对应的店铺信息
    resp = TbMall(current_app).get_json('/shops/{}'.format(id))
    shop = resp['data']['shop']

    # 使用 get 方法向后台用户服务店铺id对应用户信息
    resp = TbUser(current_app).get_json('/users/{}'.format(shop['user_id']))
    shop['user'] = resp['data']['user']

    limit = current_app.config['PAGINATION_PER_PAGE']
    offset = (page - 1) * limit
    # 查询当前页该店铺对应的商品信息
    resp = TbMall(current_app).get_json('/products', params={
        'shop_id': id,
        'limit': limit,
        'offset': offset
    })

    return render_template('shop/detail.html', shop=shop, **resp['data'])


def full_shop_info(shops):
    user_ids = [shop['user_id'] for shop in shops]
    if len(user_ids) > 0:
        # 批量查询多个店铺的店主信息
        resp = TbUser(current_app).get_json('/users/infos', params={
            'ids': ','.join([str(v) for v in user_ids]),
        })
        for shop in shops:
            shop['user'] = resp['data']['users'].get(str(shop['user_id']))

    # 每个店铺选取三个商品来展示
    for shop in shops:
        r = TbMall(current_app).get_json('/products', params={
            'shop_id': shop['id'],
            'limit': 3
        })
        shop['products'] = r['data']['products']

    return shops
