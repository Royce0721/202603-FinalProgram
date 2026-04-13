from sqlalchemy import Column, Integer, String, Numeric
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from marshmallow import Schema, fields, post_load

from .base import Base


class Gender:
    UNKNOWN = ''
    MALE = 'm'
    FEMALE = 'f'


class User(Base):
    __tablename__ = 'user'

    username = Column(String(20), nullable=False, unique=True)
    _password = Column('password', String(256), nullable=False)
    avatar = Column(String(200), nullable=False, default='')
    gender = Column(String(1), nullable=False, default=Gender.UNKNOWN)
    mobile = Column(String(11), unique=True)
    wallet_money = Column(Numeric(10, 2), nullable=False, default=0)

    # 获取密码
    @property
    def password(self):
        return self._password

    # 设置密码
    @password.setter
    def password(self, password):
        # 使用密码加盐哈希函数对输入的密码进行加密
        self._password = generate_password_hash(password)

    # 核对密码
    def check_password(self, password):
        return check_password_hash(self._password, password)


# 创建 UserSchema 类实现对用户对象的序列化和反序列化
class UserSchema(Schema):
    id = fields.Int()
    username = fields.Str()
    avatar = fields.Str()
    gender = fields.Str()
    mobile = fields.Str()
    wallet_money = fields.Decimal(as_string=True, places=2)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()

    # 注册反序列化对象后调用的方法，实现字典或字符串到对象的转换
    @post_load
    def make_user(self, data, **kwargs):
        return User(**data)
