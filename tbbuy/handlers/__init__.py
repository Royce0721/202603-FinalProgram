from tblib.handler import handle_error_json

from .cart_product import cart_product
from .order import order
from .order_product import order_product
from .review import review


def init(app):
    app.register_error_handler(Exception, handle_error_json)

    app.register_blueprint(cart_product)
    app.register_blueprint(order)
    app.register_blueprint(order_product)
    app.register_blueprint(review)
