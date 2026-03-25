from tblib.model import db
from marshmallow import Schema, fields, post_load

from .base import Base
from .shop import ShopSchema


class Product(Base):
    __tablename__ = 'product'

    __table_args__ = (
        db.Index('idx_shop_id', 'shop_id'),
    )

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(2000), nullable=False, default='')
    # 这里的封面图片只是存储通过文件服务返回的图片id值
    cover = db.Column(db.String(200), nullable=False, default='')
    price = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    shop_id = db.Column(
        db.Integer,
        db.ForeignKey('shop.id', ondelete='CASCADE'),
        nullable=False
    )

    shop = db.relationship(
        'Shop',
        uselist=False,
        backref=db.backref('products', lazy='dynamic')
    )


class ProductSchema(Schema):
    id = fields.Int()
    title = fields.Str()
    description = fields.Str()
    cover = fields.Str()
    price = fields.Int()
    amount = fields.Int()
    shop_id = fields.Int()
    shop = fields.Nested(ShopSchema)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()

    @post_load
    def make_product(self, data, **kwargs):
        return Product(**data)