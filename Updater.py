import json
import requests
import os
import datetime
from zipfile import ZipFile
import shutil

run_time = datetime.datetime.now().strftime("%Y-%m-%d")
if os.path.exists('logs/latest.log'): open('logs/latest.log', 'w').close()
def log(text):
	"""
	Prints text to the console and appends date, time, and text to a logs.txt file text. class str. The text to log
	"""
	if not os.path.exists('logs'): os.makedirs('logs')
	print(str(text))
	with open(f"logs/{run_time}.log", "a", encoding="UTF-8") as file: file.write(f"{str(text)}\n")
	with open(f"logs/latest.log", "a", encoding="UTF-8") as file: file.write(f"{str(text)}\n")

def logExit(text):
	log(text)
	exit()

mods_downloaded = 0
mods_updated = 0
class CurseforgeMod:
	def __init__(self, slug, version):
		data = requests.get('https://api.curseforge.com/v1/mods/search', params = {'gameId': '432','slug': slug, 'classId': '6'}, headers = headers).json()['data']
		try: self.data = data[0]
		except: logExit(f"			[WARN] FATAL: Could not find mod \"https://www.curseforge.com/minecraft/mc-mods/{slug}\". Please make sure the URL is still valid.")
		self.id = self.data['id']
		self.slug = slug
		self.url = self.data['links']['websiteUrl']
		self.version = version
		
		files = requests.get(f"https://api.curseforge.com/v1/mods/{self.id}/files", params = {'gameVersion': self.version, 'modLoaderType': 4}, headers = headers).json()['data']
		if len(files) != 0 : self.files = files
		else: self.files = None

		if self.files:
			download_url = requests.get(f"https://api.curseforge.com/v1/mods/{self.id}/files/{self.files[0]['id']}/download-url", headers = headers)
			if download_url.content == b"": self.download_url = f"https://edge.forgecdn.net/files/{str(self.files[0]['id'])[0:4]}/{str(self.files[0]['id'])[4:7]}/{self.files[0]['fileName']}"
			else: self.download_url = download_url.json()['data']
		else:
			self.download_url = None
			log(f"			[WARN] Cannot find {self.version} file for {self.url}")

	def __str__(self):
		return {'data': self.data, 'id': self.id, 'slug': self.slug, 'url': self.url, 'files': self.files, 'download_url': self.download_url}

	def downloadLatestFile(self, download_location, copy_locations):
		if self.download_url:
			file_name = self.files[0]['fileName']
			if not os.path.exists(f"{download_location}/{file_name}"):
				try:
					open(f"{download_location}/{file_name}", 'wb').write(requests.get(self.download_url).content)
					global mods_downloaded
					mods_downloaded += 1
					log(f"			[INFO] Downloaded {self.version} mod \"{file_name}\"")
				except Exception as e: log(f"			[WARN] Error downloading {self.url}. {e}")
			else: log(f"			Already up to date.")
			for copy_location in copy_locations:
				if not os.path.exists(f"{copy_location}/{file_name}"):
					try:
						shutil.copyfile(f"{download_location}/{file_name}", f"{copy_location}/{file_name}")
						global mods_updated
						mods_updated += 1
						log(f"			[INFO] Copied \"{download_location}/{file_name}\" to \"{copy_location}\"")
					except Exception as e: log(f"			[WARN] Could not copy mod \"{download_location}/{file_name}\" to \"{copy_location}\". {e}")
		else: return None


log(f"[{datetime.datetime.now()}] RUNNING MOD UPDATER")


"""LOAD CONFIG"""
log("[INFO] LOADING CONFIG")
try:
	with open('Manager Config.json') as f: config = json.load(f)
	log('	Config has been read')
except Exception as e:
	logExit(f'	[WARN] FATAL: Loading config file. {e}')
if len(config['x-api-key']) != 60 or config['x-api-key'][:7] != '$2a$10$':
	logExit("	[WARN] FATAL: x-api-key doesn't look valid. Please provide a valid API key.")
headers = {'Accept': 'application/json', 'x-api-key': config['x-api-key']}

HAD_ERROR = False
for instance in config['instances']:
	if not os.path.isdir(instance['directory']):
		HAD_ERROR = True
		log(f"	[WARN] Location \"{instance['directory']}\" is invalid/doesn't exist!")
	else:
		log(f"	Found {instance['directory']}")
if HAD_ERROR:
	logExit('	[WARN] FATAL: Cannot continue until directories listed above can be found.')

organized_config = {}
for instance in config['instances']:
	version = instance['version']
	directory = instance['directory']
	
	if version not in organized_config:
		organized_config[version] = {}
	
	for mod_link in instance['mod_links']:
		if mod_link[0:45] == 'https://www.curseforge.com/minecraft/mc-mods/':
			if mod_link[-1] != '/':
				slug = mod_link[45:]
				if '/' not in slug or ' ' not in slug or '\\' not in slug:
					if slug not in organized_config[version]:
						organized_config[version][slug] = {'directories': []}
					organized_config[version][slug]['directories'].append(directory)
				else: log(f'	[WARN] Invlalid slug: "{slug}"')
			else: log(f'	[WARN] Remove trailing "/" at the end of the url! "{mod_link}"')
		else: log(f'	[WARN] "{mod_link}" is not a curseforge mod and thus cannot be auto-downloaded.')

for version in organized_config:
	try:
		if not os.path.exists(f"{config['download_mods_location']}/{version}"): os.makedirs(f"{config['download_mods_location']}/{version}")
	except Exception as e:
		logExit('	[WARN]	FATAL: Could not generate folders to download mods into.')


"""UPDATING FABRIC"""
log("[INFO] UPDATING FABRIC")

installer_version = requests.get(f"https://meta.fabricmc.net/v2/versions/installer").json()[0]['version']
if not os.path.exists(f"{config['download_mods_location']}/fabric-installer-{installer_version}.jar"):
	open(f"{config['download_mods_location']}/fabric-installer-{installer_version}.jar", 'wb').write(requests.get(f"https://maven.fabricmc.net/net/fabricmc/fabric-installer/{installer_version}/fabric-installer-{installer_version}.jar").content)
	log(f"	[INFO] Downloaded {config['download_mods_location']}/fabric-installer-{installer_version}.jar")
else:
	log(f"	Installer already up to date")

fabric_version = requests.get(f"https://meta.fabricmc.net/v2/versions/loader").json()[0]['version']
for version in organized_config:
	if f"fabric-loader-{fabric_version}-{version}" not in os.listdir(f"{os.getenv('APPDATA')}/.minecraft/versions"):
		log(f"	Need to install fabric-loader-{fabric_version}-{version}")
	else:
		log(f"	Fabric {version} is up to date")


"""UPDATING MODS"""
log("[INFO] UPDATING MODS")
for version in organized_config:
	log(f"	Processing {version} mods:")
	for slug in organized_config[version]:
		log(f"		Scanning {slug}")
		mod = CurseforgeMod(slug, version)
		mod.downloadLatestFile(f"{config['download_mods_location']}/{version}", organized_config[version][slug]['directories'])

if mods_downloaded == 1: log(f"	Downloaded {mods_downloaded} mod.")
else: log(f"	Downloaded {mods_downloaded} mods.")

if mods_updated == 1: log(f"	Updated {mods_updated} mod.")
else: log(f"	Updated {mods_updated} mods.")


"""DELETE OLD MODS"""
log("[INFO] DELETING OLD MODS")
versions = []
for instance in config['instances']:
	version = instance['version']
	if version not in versions:
		versions.append(version)

directories = []
for version in versions:
	directories.append(f"{config['download_mods_location']}/{version}")
for instance in config['instances']:
	directory = instance['directory']
	if directory not in directories:
		directories.append(directory)

mods_deleted = 0
for directory in directories:
	cache = {}
	for mod in [file for file in os.listdir(directory) if file.endswith(".jar")]:
		path = f"{directory}/{mod}"
		tmodified = os.path.getmtime(path)
		with ZipFile(path, "r") as modzip:
			with modzip.open("fabric.mod.json", "r") as modinfo:
				mod_id = json.load(modinfo, strict=False)["id"]
			modinfo.close()
		modzip.close()
		if mod_id not in cache:
			cache[mod_id] = {'path': path, 'tmodified': tmodified}
		else:
			if tmodified > cache[mod_id]['tmodified']:
				os.remove(cache[mod_id]['path'])
				mods_deleted += 1
				log(f"	[INFO] Deleted {cache[mod_id]['path']}")
				cache[mod_id] = {'path': path, 'tmodified': tmodified}
			else:
				os.remove(path)
				mods_deleted += 1
				log(f"	[INFO] Deleted {path}")

if mods_deleted == 1: log(f"	Deleted {mods_deleted} file.")
else: log(f"	Deleted {mods_deleted} files.")


"""DONE"""
log(f"[INFO] DONE\n")
