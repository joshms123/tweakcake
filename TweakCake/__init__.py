#!/usr/bin/env python3

import os, json, errno, tempfile, shutil, logging, atexit, sys
from collections.abc import MutableMapping

class Config(MutableMapping):
	_logger = logging.getLogger(__name__)
	_site_config_home = "/etc"
	_user_config_home = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))

	def __init__(self, name=os.path.basename(sys.argv[0]), save_on_exit=True, autosave=False, _parent=None, _data=None, custom_path=None):
		self._name = name
		self._autosave = autosave
		self._custom_path = custom_path
		self._parent = _parent
		self._cf_closed = False
		if _data is None:
			self._data = {}
			if _parent is None:  # Load config if this is the top-level object
				self._load_config()
				if save_on_exit:
					atexit.register(self.save)
		else:
			self._data = _data

	def _load_config(self):
		for config_file in self.config_files:
			try:
				with open(config_file, 'r') as fh:
					self.update(json.load(fh))
			except FileNotFoundError:
				self._logger.debug(f"No configuration file found at {config_file}")
			except Exception as e:
				self._logger.error(f"Error loading configuration from {config_file}: {e}")

	@property
	def config_files(self):
		files = [
			os.path.join(self._site_config_home, self._name, "config.json"),
			os.path.join(self._user_config_home, self._name, "config.json")
		]
		if self._custom_path:
			files.append(os.path.join(self._custom_path, self._name + ".json"))
		return files

	def save(self, mode=0o600):
		if self._parent:
			return self._parent.save(mode=mode)
		else:
			config_file = self.config_files[-1]
			os.makedirs(os.path.dirname(config_file), exist_ok=True)
			# Use a temporary file to ensure atomic write
			fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(config_file))
			with os.fdopen(fd, 'w') as fh:
				json.dump(self._data, fh, indent=1, default=lambda obj: obj._data if hasattr(obj, '_data') else obj)
			# Backup existing config file, if it exists
			backup_file = config_file + ".bak"
			if os.path.exists(config_file):
				shutil.copyfile(config_file, backup_file)
			# Atomically move the temporary file to the target location
			shutil.move(temp_path, config_file)
			os.chmod(config_file, mode)
			self._logger.info(f"Configuration saved to {config_file}")

	def _as_config(self, value):
		if isinstance(value, MutableMapping):
			return Config(name=self._name, autosave=self._autosave, _parent=self, _data=value, custom_path=self._custom_path)
		return value

	def __getitem__(self, key):
		return self._as_config(self._data[key])

	def __setitem__(self, key, value):
		self._data[key] = value
		if self._autosave:
			self.save()

	def __delitem__(self, key):
		del self._data[key]
		if self._autosave:
			self.save()

	def __getattr__(self, name):
		try:
			return self[name]
		except KeyError:
			raise AttributeError(f"'Config' object has no attribute '{name}'")

	def __setattr__(self, name, value):
		if name.startswith("_"):
			super(Config, self).__setattr__(name, value)
		else:
			self[name] = self._as_config(value)

	def __delattr__(self, name):
		if name.startswith("_"):
			super(Config, self).__delattr__(name)
		else:
			del self[name]

	def __iter__(self):
		return iter(self._data)

	def __len__(self):
		return len(self._data)

	def __repr__(self):
		return repr(self._data)

	def close(self):
		if not self._cf_closed:
			self._cf_closed = True
			self.save()
			atexit.unregister(self.save)
			return True
		return False
