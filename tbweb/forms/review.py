from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length


class ReviewForm(FlaskForm):
    rating = SelectField(
        '评分',
        choices=[('5', '5 分'), ('4', '4 分'), ('3', '3 分'), ('2', '2 分'), ('1', '1 分')],
        validators=[DataRequired()],
        default='5',
    )
    content = TextAreaField('评价内容', validators=[DataRequired(), Length(2, 120)])
    submit = SubmitField('提交评价')
