from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import IntegerField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange


class ProductForm(FlaskForm):
    title = StringField('商品名称', validators=[DataRequired(), Length(2, 100)])
    description = TextAreaField('商品描述', validators=[DataRequired(), Length(2, 1000)])
    price = IntegerField('商品价格', validators=[DataRequired(), NumberRange(1, 100000000)])
    amount = IntegerField('库存数量', validators=[DataRequired(), NumberRange(0, 1000000)])
    cover = FileField('商品图片', validators=[FileAllowed(['jpg', 'jpeg', 'png'], '商品图片必须为图片')])
    submit = SubmitField('提交')
