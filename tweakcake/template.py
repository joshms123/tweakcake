from .config import Config

class ConfigOption:
	def __init__(self, *, default, name, description=None, validator=None):
		self.default = default
		self.name = name
		self.description = description
		self.validator = validator

	def __set_name__(self, owner, name):
		self.config_key = name

	def validate(self, template_instance, value):
		if self.validator and not self.validator(value):
			raise ValueError(f"Validation failed for {self.config_key}: {value}")
		return value
	
class ConfigTemplate(Config):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		# Initialize nested ConfigTemplates if defined.
		for key, value in self.__class__.__dict__.items():
			if isinstance(value, ConfigOption) and isinstance(value.default, dict):
				nested_config = ConfigTemplate(_parent=self, _data=value.default)
				self._data[key] = nested_config

	def __getitem__(self, key):
		try:
			value = super(ConfigTemplate, self).__getitem__(key)
			return value
		except KeyError:
			config_option = getattr(self.__class__, key, None)
			if isinstance(config_option, ConfigOption):
				return config_option.default
			raise

	def __setitem__(self, key, value):
		config_option = getattr(self.__class__, key, None)
		if isinstance(config_option, ConfigOption):
			value = config_option.validate(self, value)
			super().__setitem__(key, value)
		elif isinstance(value, dict) and isinstance(self._data.get(key), ConfigTemplate):
			# Ensure nested updates are applied properly.
			for sub_key, sub_value in value.items():
				self._data[key][sub_key] = sub_value
		else:
			super().__setitem__(key, value)

	def get_config_options(self):
		options = []
		# Iterate over attributes of the class to find ConfigOption instances.
		for attr_name in dir(self.__class__):
			attr = getattr(self.__class__, attr_name)
			if isinstance(attr, ConfigOption):
				options.append(attr)
		return options
