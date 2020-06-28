
import logging
import os.path
import asyncio
from datetime import datetime,timedelta
from sql import SQLighter

from aiogram import Bot
from aiogram import Dispatcher
from aiogram import types
from aiogram.types import reply_keyboard
from aiogram.types import inline_keyboard
from aiogram import executor
from aiogram.types.message import ContentType

import config

logging.basicConfig(level=logging.INFO)
bot = Bot(token=config.token)
dp = Dispatcher(bot)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "users.db")

db = SQLighter(db_path)

channel_name = '@' + config.channel_link.split('/')[-1]

@dp.callback_query_handler()
async def check_react(callback:types.CallbackQuery):
	if callback.data == 'Удалить':
		
		user_id = callback.from_user.id
		message_id = callback.message.message_id

		post = db.find_post(user_id,message_id)
		
		if not post:
			await bot.send_message(user_id,'Вы уже удаляли этот пост')
			return

		post_id = post[2]

		await bot.delete_message(chat_id=channel_name,message_id=post_id)

		await bot.send_message(user_id,'Пост успешно удалён')

		db.del_post(user_id,message_id,post_id)

		return


#Для стартовой функции
@dp.message_handler(commands=['start'])
async def start(message:types.Message):
	
	keyboard = make_keyboard(config.start_button)
	user_id = message.chat.id
	name = message.chat.full_name.split()[0]	
	
	if not db.user_exists(user_id):
		db.add_user(user_id)
		start_message = 'Привет,{},я бот OpenAd,напиши мне,если хочешь создать объявление на канале'.format(name)
	
	else:
		ability_to_post,days_left = check_ability_to_post(message.chat.id)
	
		if not ability_to_post:
			await refuse(message,days_left)
			return
		
		db.update_param(user_id,'stage',0)
		db.update_param(user_id,'post','')
		start_message = 'С возвращением,{}'.format(name)

	await message.answer(start_message,reply_markup=keyboard)

#Основной код
@dp.message_handler()
async def check_meassge(message:types.Message):
	user_id = message.chat.id
	
	if not db.user_exists(user_id):
		db.add_user(user_id)
	
	
	sub = await bot.get_chat_member(chat_id=channel_name,user_id=user_id)
	if sub['status'] == 'left':
		await message.answer('Вы должны быть подписаны на этот канал '+config.channel_link)
		return
	
	ability_to_post,days_left = check_ability_to_post(user_id)
	if not ability_to_post:
		await refuse(message,days_left)
		return
	
	stage = db.get_params(user_id,'stage')
	
	if message.text != config.start_button and stage == 0:
		keyboard = make_keyboard(config.start_button)
		await message.answer('Если хотите создать объявление,нажмите на копку или напишите "Создать объявление"',reply_markup=keyboard)
		return

	elif message.text.lower() == 'назад' and stage > 1:
		keyboard = None
		
		await message.answer(config.post_text[stage-2],reply_markup=keyboard)

		db.update_param(user_id,'stage',stage-1)
		return
	
	elif stage < 3:
		
		keyboard = None
		
		if stage == 1:
			keyboard = make_keyboard('Назад')
		
		if stage == 2:
			await message.answer('Пожалуйста,киньте фотографию объявление')
			return
		
		await ask(user_id,stage,message,keyboard)
	
	elif stage == 3:
		if message.text == 'Да':
			post = db.get_params(user_id,'post')
			answer = 'Ваш пост попал в очередь,он будет опубликован на этом канале: {}'.format(config.channel_link)

			await create_post(post,user_id,message.chat.full_name)
			print(message.chat.full_name,'создал пост')
			stage = -1

		elif message.text == 'Отмена':
			answer = 'Возврат к началу'
			stage = -1
		
		else:
			answer = 'Пожалуйста,ответьте,нет ли ошибки в посте'
			return

		start_keyboard = make_keyboard(config.start_button)
		
		await message.answer(answer,reply_markup=start_keyboard)

	db.update_param(user_id,'stage',stage+1)


@dp.message_handler(content_types=['photo'])
async def chek_photo(message:types.Message):
	user_id = message.chat.id
	stage,post = db.get_params(user_id,'stage','post')
	
	if stage == 2:
		if not os.path.exists('photo_users'):
			os.mkdir('photo_users')
	
	path = f'photo_users/{str(user_id)}.jpg' 
	
	await message.photo[-1].download(path)
	await message.answer(config.post_text[3])
	
	keyboard = make_keyboard('Да','Отмена','Назад')

	db.update_param(user_id,'stage',stage+1)

	with open(path,'rb') as photo:
		await message.answer_photo(photo,caption=post,reply_markup=keyboard)


async def ask(user_id,stage,message,keyboard):
	
	post_text = config.post_text[stage]
	
	await message.answer(post_text,reply_markup=keyboard)

	text = message.text
	
	if stage != 0:
		db.update_param(user_id,'post',str(text))

def make_keyboard(*args,inline=False):
	if not inline:
		keyboard = reply_keyboard.ReplyKeyboardMarkup()
		KeyboardButton = reply_keyboard.KeyboardButton
	
	else:
		keyboard = inline_keyboard.InlineKeyboardMarkup() 
		KeyboardButton = inline_keyboard.InlineKeyboardButton
	
	for arg in args:
		arr = {}

		arr['text'] = arg

		if inline:
			arr['callback_data'] = arg
		
		button = KeyboardButton(**arr)
		keyboard.row(button)

	return keyboard


def check_last_date():
	amount = db.get_date()
	max_date = datetime.now()
	
	for date in amount:
		if not date:
			continue 
		date = transform_date(date)
		if date > max_date:
			max_date = date
	
	return max_date

def transform_date(date):
	date = date.replace('-',' ').replace(':',' ').split()
	date = [int(x.split('.')[0]) for x in date]
	date = datetime(*date)
	return date

def check_ability_to_post(user_id):
	now = datetime.now()
	date = db.get_params(user_id,'date',table='Posts')
	
	if date == None:
		return [True,None]

	post_date = transform_date(date)
	time_down = now - post_date

	ability_days = get_time('ability')
	
	if time_down.days < ability_days:
		return [False,ability_days - time_down.days]

	return [True,None]

def get_time(kind):
	with open(kind+'_time.txt','r',encoding='utf-8') as f:
		sleep_time = int(f.read())
		return sleep_time

async def post_in_channel(wait_for):
	while True:
		posts = db.get_posts()
		
		
		if posts == []:
			await asyncio.sleep(wait_for)
			continue 
		
		user_id = posts[0][5]
		post = posts[0][-1]
		
		keyboard = make_keyboard('👍','👎',inline=True)	
		
		path = f'photo_users/{str(user_id)}.jpg'
		photo = open(path,'rb')

		post_message = await bot.send_photo(channel_name,photo=photo,caption=post,reply_markup=keyboard)

		text = 'Ваш пост опублкован:\n\n' + str(post)
		keyboard = make_keyboard('Удалить',inline=True)
		
		photo = open(path,'rb')
		manager_message = await bot.send_photo(user_id,photo=photo,caption=text,reply_markup=keyboard)

		values = [post_message.message_id,manager_message.message_id,False]
		params = ['post_id','message_id','posting']
		
		for i in range(3):
			db.update_param(user_id,params[i],values[i],table='Posts')

		photo.close()

		os.remove(path)

		await asyncio.sleep(wait_for)

async def create_post(post,user_id,name):
	date = check_last_date()
	
	wait_for = get_time('sleep')
	now = datetime.now()
	differens = date - now 

	post_date = now+differens+timedelta(seconds=wait_for)
	
	date = post_date.strftime('%d:%m:%Y')
	hours = post_date.strftime('%H')
	
	hours_word = get_word_of_number(hours,['час','часа','часов'])
	await bot.send_message(user_id,f'Ваш пост будет опубликован {date} примерно в {hours} {hours_word}')
	
	db.add_post(user_id,name,post_date,post)
	
	return

async def refuse(message,days_left):
	await message.answer(config.fail_text+str(get_time('ability')))

	days = get_word_of_number(days_left,['день','дня','дней'])
	
	await message.answer(f'Осталось {days_left} {days}')

def get_word_of_number(number,varios):
	number = int(number)
	if number > 10:
		digits = number%100
		if digits in range(10,21):
			return varios[2] 
	
	digit = number%10
	
	if digit == 0 or number%10 in range(5,10):
		return varios[2] 

	if digit == 1:
		return varios[0]

	else:
		return varios[1]

if __name__ == '__main__':
	dp.loop.create_task(post_in_channel(get_time('sleep')))
	executor.start_polling(dp,skip_updates=True)