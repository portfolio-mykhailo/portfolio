from configparser import ConfigParser


class Config:
	_instances = {}

	def __new__(cls, user_id: int, path: str, *args, **kwargs):
		if user_id not in cls._instances:
			instance = super().__new__(cls)
			cls._instances[user_id] = instance
		return cls._instances[user_id]

	def __init__(self, user_id: int, path: str):
		if not hasattr(self, 'initialized'):
			self.user_id = user_id
			self.path = path
			self.config = ConfigParser()
			self.initialized = True

	async def get(self, section, key):
		self.config.read(self.path, encoding='utf-8')
		raw_string = self.config.get(section, key).strip('"')
		return raw_string.replace('\\n', '\n')

	async def change_path(self, new_path):
		self.path = new_path
