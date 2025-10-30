import sys
import os
import codecs
import shutil
import time
import json
import io
import zipfile
from CompileError import CompileError

class mcworld(object):
	def __init__(self, leveldir, namespace, worldversion=0):
		self.current_dir = os.getcwd()
		self.dir = leveldir
		self.zipbytes = io.BytesIO()
		self.zip = zipfile.ZipFile(self.zipbytes, 'w', zipfile.ZIP_DEFLATED, False)
		self.namespace = namespace
		self.worldversion = worldversion
		self.unpluralize = self.worldversion >= 3953  # 1.21+
		print("Minecraft save version: ", self.worldversion, " (", "1.21+" if self.unpluralize else "before 1.21", ")", sep='')
		
	def get_latest_log_file(self):
		savesdir = os.path.split(self.dir)[0]
		versiondir = os.path.split(savesdir)[0]
		logsdir = os.path.join(versiondir, 'logs')
		logfile = os.path.join(logsdir, 'latest.log')
		
		return logfile
	
	def write_functions(self, functions):
		function_dir = f'data/{self.namespace}/{"function" if self.unpluralize else "functions"}/'
		
		for name in functions:
			filename = os.path.join(function_dir, f"{name}.mcfunction")
			
			func = functions[name]
			text = func.get_utf8_text()
			self.zip.writestr(filename, text)
				
	def write_tags(self, clocks, block_tags, entity_tags, item_tags):
		tag_dir = f"data/minecraft/tags/{"function" if self.unpluralize else "functions"}/"
		
		tick_tag_file = os.path.join(tag_dir, 'tick.json')
		self.zip.writestr(tick_tag_file, json.dumps({'values':[f'{self.namespace}:{name}'for name in clocks]}, indent=4))
		
		load_tag_file = os.path.join(tag_dir, 'load.json')
		self.zip.writestr(load_tag_file, json.dumps({'values':[f'{self.namespace}:reset']}, indent=4))
			
		for name, list in [
			({"block" if self.unpluralize else "blocks"}, block_tags),
			({"item" if self.unpluralize else "items"}, item_tags),
			({"entity_type" if self.unpluralize else "entity_types"}, entity_tags)
		]:
			if len(list) > 0:
				tag_dir = f'data/{self.namespace}/tags/{name}/'
				
				for tag in list:
					items = list[tag]
					
					tag_filename = os.path.join(tag_dir, f'{tag}.json')
					self.zip.writestr(tag_filename, json.dumps({'values':[f'minecraft:{item}'for item in items]}, indent=4))
				
	def write_recipes(self, recipes):
		if len(recipes) > 0:
			recipe_dir = f'data/{self.namespace}/{"recipe" if self.unpluralize else "recipes"}/'
			
			id = 0
			for recipe in recipes:
				id += 1
				recipe_file = os.path.join(recipe_dir, f'{recipe.get_type()}{id}.json')
				recipe_struct = recipe.get_json_struct()
				
				self.zip.writestr(recipe_file, json.dumps(recipe_struct, indent=4))
				
	def write_advancements(self, advancements):
		if len(advancements) > 0:
			advancement_dir = f'data/{self.namespace}/{"advancement" if self.unpluralize else "advancements"}/'
			
			for name in advancements:
				advancement_file = os.path.join(advancement_dir, f'{name}.json')
				self.zip.writestr(advancement_file, advancements[name])
				
	def write_loot_tables(self, loot_tables):
		if len(loot_tables) > 0:
			for name in loot_tables:
				(type, contents) = loot_tables[name]
				if ':' in name:
					parts = name.split(':')
					if len(parts) != 2:
						raise CompileError(f'Invalid loot tables name "{name}"')
					loot_table_dir = f'data/{parts[0]}/{"loot_table" if self.unpluralize else "loot_tables"}/{type}/'
					filename = parts[1]
				else:
					loot_table_dir = f'data/{self.namespace}/{"loot_table" if self.unpluralize else "loot_tables"}/{type}/'
					filename = name
				loot_table_file = os.path.join(loot_table_dir, f'{filename}.json')
				self.zip.writestr(loot_table_file, contents)
	
	def write_predicates(self, predicates):
		if len(predicates) > 0:
			predicate_dir = f'data/{self.namespace}/{"predicate" if self.unpluralize else "predicates"}/'
			
			for name in predicates:
				predicate_file = os.path.join(predicate_dir, f'{name}.json')
				self.zip.writestr(predicate_file, predicates[name])

	def write_item_modifiers(self, item_modifiers):
		if len(item_modifiers) > 0:
			item_modifier_dir = f'data/{self.namespace}/{"item_modifier" if self.unpluralize else "item_modifiers"}/'
			
			for name in item_modifiers:
				item_modifier_file = os.path.join(item_modifier_dir, f'{name}.json')
				self.zip.writestr(item_modifier_file, item_modifiers[name])

	def write_mcmeta(self, desc):
		mcmeta_file = 'pack.mcmeta'
		
		self.zip.writestr(mcmeta_file, json.dumps({'pack':{'pack_format':1, 'description':desc}}, indent=4))
	
	# If data folder exists in a folder named the same as the namespace, add it to the zip
	def write_data_folder(self, source_file, global_context=""):
		try:
			script_dir = os.path.dirname(source_file.filename)
		except AttributeError:
			print("Error: Could not get script directory from 'source_file' object.")
			return
		
		data_dir = os.path.join(script_dir, 'data')
		if os.path.isdir(data_dir):
			print("Found custom 'data' folder, adding contents to zip...")

			# Walk through the custom 'data' directory
			for root, dirs, files in os.walk(data_dir):
				for file in files:
					# Get the full path to the file on your computer
					file_path = os.path.join(root, file)
					
					# Get the relative path to be used inside the zip
					# This preserves the 'data/...' structure
					arcname = os.path.relpath(file_path, script_dir)
					
					if global_context:
						# Registers this file as a dependency for change monitoring
						global_context.register_dependency(arcname)

					# Write the file to the zip
					print(f"  Adding: {arcname}")
					self.zip.write(file_path, arcname=arcname)

	def write_zip(self):
		self.zip.close()
	
		zip_filename = os.path.join(self.dir, f'datapacks/{self.namespace}.zip')
		with open(zip_filename, 'wb') as file:
			file.write(self.zipbytes.getvalue())
