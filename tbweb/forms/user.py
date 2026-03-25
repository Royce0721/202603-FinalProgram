from flask import current_app
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, IntegerField
from wtforms.validators import DataRequired, Optional, Length, Email, EqualTo, DataRequired, ValidationError, NumberRange

from ..services import TbUser

# 注册表单
class RegisterForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(2, 20)])
    password = PasswordField('密码', validators=[DataRequired(), Length(6, 20)])
    repeat_password = PasswordField(
        '重复密码', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('提交')

    # 验证用户名
    def validate_username(self, field):
        # 使用 GET 方式向后台的用户服务接口 /users 地址发送查询用户名的请求，获取返回数据
        resp = TbUser(current_app).get_json('/users', params={
            'username': field.data,
        })
        # 如果存在用户数据就抛出异常
        if len(resp['data']['users']) > 0:
            raise ValidationError('用户名已经存在')

# 登录表单
class LoginForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(2, 20)])
    password = PasswordField('密码', validators=[DataRequired(), Length(6, 20)])
    remember_me = BooleanField('记住我')
    submit = SubmitField('提交')

# 个人资料表单
class ProfileForm(FlaskForm):
    username = StringField('用户名', validators=[Length(2, 20)])
    gender = StringField('性别', validators=[Length(1, 1)])
    mobile = StringField('手机', validators=[Length(11, 11)])
    submit = SubmitField('提交')

# 头像表单
class AvatarForm(FlaskForm):
    avatar = FileField(
        validators=[FileRequired(), FileAllowed(['jpg', 'png'], '头像必须为图片')])
    submit = SubmitField('提交')

# 密码表单
class PasswordForm(FlaskForm):
    password = PasswordField('密码', validators=[DataRequired(), Length(6, 20)])
    repeat_password = PasswordField(
        '重复密码', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('提交')

# 钱包表单
class WalletForm(FlaskForm):
    money = IntegerField('充值数量（元）', validators=[
                         DataRequired(), NumberRange(1, 1000000)])
    submit = SubmitField('提交')

