from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship, backref
from marshmallow import Schema, fields, post_load

from .base import Base
from .user import UserSchema


class Address(Base):
    __tablename__ = 'address'

    address = Column(String(200), nullable=False)
    zip_code = Column(String(6), nullable=False, default='')
    phone = Column(String(20), nullable=False)
    is_default = Column(Boolean, nullable=False, default=False)
    # 设置 ondelete='CASCADE'，在删除User的时候Address也会被删除掉
    user_id = Column(Integer, ForeignKey(
        'user.id', ondelete='CASCADE'), nullable=False)
    # 使用relationship后，Address类可以通过user属性访问User类；使用backref后，User类也可以通过addresses属性访问Address类
    # lazy='dynamic'表示禁止自动查询，用于添加过滤器
    user = relationship('User', uselist=False,
                         backref=backref('addresses', lazy='dynamic'))


class AddressSchema(Schema):
    id = fields.Int()
    address = fields.Str()
    zip_code = fields.Str()
    phone = fields.Str()
    is_default = fields.Bool()
    user_id = fields.Int()
    # 使用 fields.Nested() 关联与 UserSchema 的关系，在对地址对象序列化时也会生成对应的用户对象序列化
    user = fields.Nested(UserSchema)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()

    @post_load
    def make_user(self, data,**kwargs):
        return Address(**data)
