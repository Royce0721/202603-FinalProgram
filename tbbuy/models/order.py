from sqlalchemy import Column, Integer, String, Index, Numeric
from sqlalchemy.orm import relationship
from marshmallow import Schema, fields, post_load

from .base import Base

from .order_product import OrderProductSchema


class OrderStatus:
    NEW = 'new'
    CANCELLED = 'cancelled'
    PAIED = 'paied'
    DELIVERED = 'delivered'
    RECEIVED = 'received'
    RETURNED = 'returned'
    COMMENTED = 'commented'


class Order(Base):
    __tablename__ = 'order'
    __table_args__ = (
        Index('idx_user_id', 'user_id'),
    )

    # 金额
    pay_amount = Column(Numeric(10, 2), nullable=False)
    # 备注
    note = Column(String(200), nullable=False, default='')
    # 收货地址
    address_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    # 状态，默认是新建的状态
    status = Column(String(20), nullable=False, default=OrderStatus.NEW)


class OrderSchema(Schema):
    id = fields.Int()
    pay_amount = fields.Decimal(as_string=True, places=2)
    note = fields.Str()
    address_id = fields.Int()
    user_id = fields.Int()
    status = fields.Str()
    # 使用 fields.Nested() 关联与 OrderProductSchema 的关系，在对订单对象序列化时也会生成对应的订单商品序列化，并且是多个
    order_products = fields.Nested(OrderProductSchema, many=True)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()

    @post_load
    def make_order(self, data, **kwargs):
        return Order(**data)
