from tblib.model import db
from marshmallow import Schema, fields, post_load

from .base import Base


class ProductExtra(Base):
    __tablename__ = 'product_extra'

    product_id = db.Column(
        db.Integer,
        db.ForeignKey('product.id', ondelete='CASCADE'),
        nullable=False,
        unique=True,
        index=True,
    )
    gallery = db.Column(db.String(2000), nullable=False, default='')
    sku_text = db.Column(db.String(1000), nullable=False, default='')
    category = db.Column(db.String(100), nullable=False, default='')


class ProductExtraSchema(Schema):
    id = fields.Int()
    product_id = fields.Int()
    gallery = fields.Str()
    sku_text = fields.Str()
    category = fields.Str()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()

    @post_load
    def make_product_extra(self, data, **kwargs):
        return ProductExtra(**data)
