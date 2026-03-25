from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length


class ReviewForm(FlaskForm):
    content = TextAreaField('评价内容', validators=[DataRequired(), Length(2, 120)])
    submit = SubmitField('提交评价')
