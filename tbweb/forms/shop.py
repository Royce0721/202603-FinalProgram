from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length


class ShopForm(FlaskForm):
    name = StringField('店铺名称', validators=[DataRequired(), Length(2, 50)])
    description = TextAreaField('店铺介绍', validators=[DataRequired(), Length(2, 500)])
    cover = FileField('店铺封面', validators=[FileAllowed(['jpg', 'jpeg', 'png'], '封面必须为图片')])
    submit = SubmitField('提交')
