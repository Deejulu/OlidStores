from django.db import migrations


def seed_new_security_questions(apps, schema_editor):
	SecurityQuestion = apps.get_model('users', 'SecurityQuestion')
	new_questions = [
		('pet_name', 'What is the name of your first pet?'),
		('fav_color', 'What is your favorite color?'),
		('best_friend', 'What is the name of your best friend?'),
		('fav_food', 'What is your favorite food?'),
		('fav_book', 'What is your favorite book or author?'),
		('childhood_hero', 'What is the name of your childhood hero?'),
		('childhood_street', 'What is the name of the street you grew up on?'),
		('fav_movie', 'What is your favorite movie of all time?'),
		('first_teacher', 'What is the name of your first teacher?'),
		('fav_vacation', 'What is your favorite vacation destination?'),
		('fav_childhood_memory', 'What is your favorite childhood memory?'),
		('fav_athlete', 'What is the name of your favorite athlete or sports team?'),
		('fav_restaurant', 'What is the name of your favorite restaurant or meal?'),
		('dream_job', 'What is your dream job or career?'),
		('first_school', 'What is the name of the first school you attended?'),
		('fav_song', 'What is your favorite song or artist?'),
		('fav_tradition', 'What is your favorite family tradition?'),
		('closest_relative', 'What is the name of your closest relative?'),
	]
	for key, text in new_questions:
		SecurityQuestion.objects.update_or_create(
			question_key=key,
			defaults={'question_text': text},
		)


def reverse_seed(apps, schema_editor):
	SecurityQuestion = apps.get_model('users', 'SecurityQuestion')
	keys = [
		'pet_name', 'fav_color', 'best_friend', 'fav_food', 'fav_book',
		'childhood_hero', 'childhood_street', 'fav_movie', 'first_teacher',
		'fav_vacation', 'fav_childhood_memory', 'fav_athlete', 'fav_restaurant',
		'dream_job', 'first_school', 'fav_song', 'fav_tradition', 'closest_relative',
	]
	SecurityQuestion.objects.filter(question_key__in=keys).delete()


class Migration(migrations.Migration):

	dependencies = [
		('users', '0019_expand_security_questions'),
	]

	operations = [
		migrations.RunPython(seed_new_security_questions, reverse_seed),
	]