import sqlite3

class SQLighter:

	def __init__(self,database_file):
		"""Подключаемся к БД и сохраняем курсор соединения"""
		self.connection = sqlite3.connect(database_file)
		self.execute = self.connection.cursor().execute

	def user_exists(self,user_id):
		"""Проверяем есть ли пользователь в базе"""
		with self.connection:
			result = self.execute("SELECT * FROM `Users` WHERE `user_id` = ?",(user_id,)).fetchall()
			return bool(len(result))

	def get_date(self):
		amount = self.execute("SELECT `date` FROM `Posts`").fetchall()
		return [x[0] for x in amount]
	
	def add_user(self,user_id,stage=0):
		"""Добавляем пользователя в базу"""
		with self.connection:
			return self.execute("INSERT INTO `Users` (`user_id`,`stage`) VALUES (?,?)",(user_id,stage,))

	def update_param(self,user_id,param,value,table='Users'):
		"""Обновляем значение"""
		with self.connection:
			return self.execute("UPDATE `%s` SET '%s' = ? WHERE `user_id` = ?" % (table,param),(value,user_id,))

	def add_post(self,user_id,name,date,post):
		"""Добавляем пользователя в базу"""
		with self.connection:
			return self.execute("INSERT INTO `Posts` (`user_id`,`name`,`date`,`post`,`posting`) VALUES (?,?,?,?,?)",(user_id,name,date,post,True,))

	def get_posts(self):
		with self.connection:
			result = self.execute("SELECT * FROM `Posts` WHERE `posting` = ?",(True,)).fetchall()
			return result
	
	def get_params(self,user_id,*params,table='Users'):
		values = []
		with self.connection:
			for param in params:
				result = self.execute("SELECT `%s` FROM `%s` WHERE `user_id` = ?" % (param,table),(user_id,))
				result = result.fetchall()
				if result == []:
					result = None
				else:
					result = result[0][0]
				values.append(result)
			
		if len(values) == 1:
			return values[0]
		return values

	def find_post(self,user_id,message_id):
		with self.connection:
			result = self.execute("SELECT * FROM `Posts` WHERE `user_id` = ? AND `message_id` = ?",(user_id,message_id,)).fetchall()
			
			if result == []:
				result = None
			
			else:
				result = result[0]
			
			return result

	def del_post(self,user_id,message_id,post_id):
		with self.connection:
			return self.execute("DELETE FROM `Posts`  WHERE `user_id` = ? AND `message_id` = ? AND `post_id` = ?",(user_id,message_id,post_id,))


	def close(self):
		self.connection.close()