from flask_wtf import FlaskForm
from wtforms import (
	BooleanField,
	FileField,
	FloatField,
	IntegerField,
	StringField,
	SubmitField,
	TextAreaField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class AddItemForm(FlaskForm):
	name = StringField("Name:", validators=[DataRequired(), Length(max=50)])
	price = FloatField("Price:", validators=[DataRequired()])
	category = StringField("Category:", validators=[DataRequired(), Length(max=50)])
	image = FileField("Image:", validators=[Optional()])
	details = TextAreaField("Details:", validators=[DataRequired()])
	price_id = StringField("Stripe id:", validators=[DataRequired()])
	stock_quantity = IntegerField(
		"Stock quantity:",
		validators=[DataRequired(), NumberRange(min=0)],
		default=0,
	)
	low_stock_threshold = IntegerField(
		"Low-stock alert threshold:",
		validators=[Optional(), NumberRange(min=0)],
		default=0,
	)
	is_published = BooleanField("Published:", default=True)
	submit = SubmitField("Add")

class OrderEditForm(FlaskForm):
	status = StringField("Status:", validators=[DataRequired()])
	submit = SubmitField("Update")
