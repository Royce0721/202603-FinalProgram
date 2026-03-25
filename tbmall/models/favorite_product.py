from tblib.model import db
from marshmallow import Schema, fields, post_load

from .base import Base
from .product import ProductSchema


class FavoriteProduct(Base):
    __tablename__ = 'favorite_product'

    __table_args__ = (
        db.UniqueConstraint('user_id', 'product_id'),
        db.Index('idx_product_id', 'product_id'),
    )

    user_id = db.Column(db.Integer, nullable=False)
    product_id = db.Column(
        db.Integer,
        db.ForeignKey('product.id', ondelete='CASCADE'),
        nullable=False
    )

    product = db.relationship(
        'Product',
        uselist=False,
        backref=db.backref('favorites', lazy='dynamic')
    )


class FavoriteProductSchema(Schema):
    id = fields.Int()
    user_id = fields.Int()
    product_id = fields.Int()
    product = fields.Nested(ProductSchema)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()

    @post_load
    def make_favorite_product(self, data, **kwargs):
        return FavoriteProduct(**data)