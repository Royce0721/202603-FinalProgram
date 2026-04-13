from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, MultipleFileField
from wtforms import DecimalField, IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


PRODUCT_CATEGORY_CHOICES = [
    ('', '请选择分类'),
    ('数码', '数码'),
    ('服饰', '服饰'),
    ('鞋包', '鞋包'),
    ('家居', '家居'),
    ('食品', '食品'),
    ('美妆', '美妆'),
    ('图书', '图书'),
    ('其他', '其他'),
]


class ProductForm(FlaskForm):
    title = StringField('商品名称', validators=[DataRequired(), Length(2, 100)])
    description = TextAreaField('商品描述', validators=[DataRequired(), Length(2, 1000)])
    category = SelectField('商品分类', choices=PRODUCT_CATEGORY_CHOICES, validators=[DataRequired()])
    sku_text = TextAreaField('规格说明', validators=[Optional(), Length(0, 500)])
    price = DecimalField('商品价格', places=2, validators=[DataRequired(), NumberRange(0.01, 100000000)])
    amount = IntegerField('库存数量', validators=[DataRequired(), NumberRange(0, 1000000)])
    cover = FileField('主图', validators=[FileAllowed(['jpg', 'jpeg', 'png'], '商品图片必须为图片')])
    extra_images = MultipleFileField('详情图集', validators=[FileAllowed(['jpg', 'jpeg', 'png'], '详情图必须为图片')])
    submit = SubmitField('提交')
