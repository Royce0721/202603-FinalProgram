from tblib.model import db
from marshmallow import Schema, fields, post_load

from .base import Base


class Shop(Base):
    __tablename__ = 'shop'

    __table_args__ = (
        db.Index('idx_user_id', 'user_id'),
    )

    name = db.Column(db.String(200), nullable=False, unique=True)
    description = db.Column(db.String(2000), nullable=False, default='')
    # 这里的封面图片只是存储通过文件服务返回的图片id值
    cover = db.Column(db.String(200), nullable=False, default='')
    user_id = db.Column(db.Integer, nullable=False)


class ShopSchema(Schema):
    id = fields.Int()
    name = fields.Str()
    description = fields.Str()
    cover = fields.Str()
    user_id = fields.Int()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()

    @post_load
    def make_shop(self, data, **kwargs):
        return Shop(**data)