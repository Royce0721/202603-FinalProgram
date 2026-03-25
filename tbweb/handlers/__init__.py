import traceback

from flask import current_app, render_template
from flask_login import LoginManager

from .address import address
from .admin import admin
from .cart_product import cart_product
from .common import common
from .order import order
from .product import product
from .shop import shop
from .user import user
from ..models import User
from ..services import TbUser


def init(app):
    app.register_error_handler(Exception, handle_error)

    app.register_blueprint(address)
    app.register_blueprint(admin)
    app.register_blueprint(cart_product)
    app.register_blueprint(common)
    app.register_blueprint(order)
    app.register_blueprint(product)
    app.register_blueprint(shop)
    app.register_blueprint(user)

    init_login_manager(app)
    init_context_processor(app)


def handle_error(error):
    traceback.print_exc()
    return render_template('error.html', error=str(error))


def init_login_manager(app):
    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def user_loader(id):
        resp = TbUser(current_app).get_json('/users/{}'.format(id), check_code=False)
        user = resp['data'].get('user')
        if user is None:
            return None
        else:
            return User(user)

    login_manager.login_view = 'user.login'
    login_manager.login_message = "请先登录"


def init_context_processor(app):
    @app.context_processor
    def inject_current_user_shop():
        from flask_login import current_user
        from .admin import is_admin_user
        from ..services import TbMall

        if not current_user.is_authenticated:
            return {
                'current_user_shop': None,
                'current_user_is_admin': False,
            }

        try:
            resp = TbMall(current_app).get_json('/shops', params={
                'user_id': current_user.get_id(),
                'limit': 1,
            }, check_code=False)
            shops = resp.get('data', {}).get('shops', [])
        except Exception:
            shops = []

        return {
            'current_user_shop': shops[0] if shops else None,
            'current_user_is_admin': is_admin_user(),
        }
