from sqlalchemy import Column, Integer, ForeignKey, Index
from marshmallow import Schema, fields, post_load

from .base import Base


class ReviewExtra(Base):
    __tablename__ = 'review_extra'
    __table_args__ = (
        Index('idx_review_id', 'review_id'),
    )

    review_id = Column(Integer, ForeignKey('review.id', ondelete='CASCADE'), nullable=False, unique=True)
    rating = Column(Integer, nullable=False, default=5)


class ReviewExtraSchema(Schema):
    id = fields.Int()
    review_id = fields.Int()
    rating = fields.Int()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()

    @post_load
    def make_review_extra(self, data, **kwargs):
        return ReviewExtra(**data)
