from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, InputRequired, Length, NumberRange, Optional


class AdminUserForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired(), Length(2, 20)])
    gender = SelectField(
        '性别',
        choices=[('', '未设置'), ('男', '男'), ('女', '女')],
        validators=[Optional()],
    )
    mobile = StringField('手机号', validators=[Optional(), Length(0, 11)])
    wallet_money = IntegerField('钱包余额', validators=[InputRequired(), NumberRange(0, 100000000)])
    submit = SubmitField('保存用户')


class AdminOrderForm(FlaskForm):
    status = SelectField(
        '订单状态',
        choices=[
            ('new', '待支付'),
            ('cancelled', '已取消'),
            ('paied', '待发货'),
            ('delivered', '待收货'),
            ('received', '待评价'),
            ('returned', '已退回'),
            ('commented', '已评价'),
        ],
        validators=[DataRequired()],
    )
    note = TextAreaField('订单备注', validators=[Optional(), Length(0, 200)])
    submit = SubmitField('保存订单')


class RecommendationForm(FlaskForm):
    submit = SubmitField('保存推荐位')
