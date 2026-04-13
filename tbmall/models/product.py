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
    price = db.Column(db.Numeric(10, 2), nullable=False)
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
    extra = db.relationship(
        'ProductExtra',
        uselist=False,
        backref=db.backref('product', uselist=False),
        cascade='all, delete-orphan',
    )


class ProductSchema(Schema):
    id = fields.Int()
    title = fields.Str()
    description = fields.Str()
    cover = fields.Str()
    price = fields.Decimal(as_string=True, places=2)
    amount = fields.Int()
    shop_id = fields.Int()
    shop = fields.Nested(ShopSchema)
    extra_images = fields.Method('get_extra_images')
    sku_text = fields.Method('get_sku_text')
    category = fields.Method('get_category')
    created_at = fields.DateTime()
    updated_at = fields.DateTime()

    def get_extra_images(self, obj):
        if obj.extra is None or not obj.extra.gallery:
            return []
        return [item for item in obj.extra.gallery.split(',') if item]

    def get_sku_text(self, obj):
        if obj.extra is None:
            return ''
        return obj.extra.sku_text or ''

    def get_category(self, obj):
        if obj.extra is None:
            return ''
        return obj.extra.category or ''

    @post_load
    def make_product(self, data, **kwargs):
        return Product(**data)
