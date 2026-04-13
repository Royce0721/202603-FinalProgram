from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint, Index, Numeric
from sqlalchemy.orm import relationship, backref
from marshmallow import Schema, fields, post_load

from .base import Base


class OrderProduct(Base):
    __tablename__ = 'order_product'
    __table_args__ = (
        UniqueConstraint('order_id', 'product_id'),
        Index('idx_product_id', 'product_id'),
    )

    order_id = Column(Integer, ForeignKey(
        'order.id', ondelete='CASCADE'), nullable=False)
    product_id = Column(Integer, nullable=False)
    product_shop_id = Column(Integer, nullable=False, default=0)
    product_title = Column(String(200), nullable=False, default='')
    product_cover = Column(String(200), nullable=False, default='')
    shop_name = Column(String(200), nullable=False, default='')
    # 保存下单时的价格
    price = Column(Numeric(10, 2), nullable=False)
    amount = Column(Integer, nullable=False, default=1)
    order = relationship('Order', uselist=False, backref=backref(
        'order_products', lazy='dynamic'))


class OrderProductSchema(Schema):
    id = fields.Int()
    order_id = fields.Int()
    product_id = fields.Int()
    product_shop_id = fields.Int()
    product_title = fields.Str()
    product_cover = fields.Str()
    shop_name = fields.Str()
    price = fields.Decimal(as_string=True, places=2)
    amount = fields.Int()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()

    @post_load
    def make_order_product(self, data, **kwargs):
        return OrderProduct(**data)
