from sqlalchemy import Column, Integer, String, Index
from marshmallow import Schema, fields, post_load

from .base import Base


class Review(Base):
    __tablename__ = 'review'
    __table_args__ = (
        Index('idx_order_id', 'order_id'),
        Index('idx_user_id', 'user_id'),
    )

    order_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    content = Column(String(200), nullable=False, default='')


class ReviewSchema(Schema):
    id = fields.Int()
    order_id = fields.Int()
    user_id = fields.Int()
    content = fields.Str()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()

    @post_load
    def make_review(self, data, **kwargs):
        return Review(**data)
