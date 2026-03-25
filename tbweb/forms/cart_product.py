# forms/cart_product.py

from flask import current_app
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, IntegerField, HiddenField
from wtforms.validators import DataRequired, Optional, Length, Email, EqualTo, DataRequired, ValidationError, NumberRange


class CartProductForm(FlaskForm):
    product_id = HiddenField('商品', validators=[DataRequired()])
    amount = IntegerField('购买数量', validators=[DataRequired(), NumberRange(1, 100)])
    submit = SubmitField('提交')
