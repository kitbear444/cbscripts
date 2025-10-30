import global_context
import mcworld
from environment import environment
from mcfunction import mcfunction, compile_section
from selector_definition import selector_definition
from source_file import source_file
from CompileError import CompileError
import tellraw
import traceback
import math
import collections
import time
import os
import json
from pathlib import Path

class cbscript(object):
	def __init__(self, source_file, parse_func):
		self.source_file = source_file
		self.parse = parse_func
		self.namespace = self.source_file.get_base_name().split('.')[0].lower()
		self.dependencies = []
		self.worldversion = 0
		self.latest_log_file = None
	
	def log(self, text):
		print(text)
		
	def log_traceback(self):
		traceback.print_exc()
	
	def check_for_update(self):
		recompile = False
		# It's important to go through all the files, to make sure that if multiple were updated
		# we don't try to compile multiple times
		for file in [self.source_file] + self.dependencies:
			if file.was_updated():
				recompile = True
				
		if recompile:
			self.try_to_compile()
			
		if self.latest_log_file and self.latest_log_file.was_updated():
			log_text = self.latest_log_file.get_text(only_new_text=True)
			self.search_log_for_errors(log_text)
			
	def search_log_for_errors(self, log_text):
		lines = log_text.split('\n')
		error_text = ''
		for line in lines:
			if len(error_text) == 0:
				# Haven't found an error, keep searching
				if self.namespace in line and ('ERROR' in line or 'Exception' in line):
					error_text = line
			else:
				# Append lines to the error message until it's over
				if len(line) > 0 and line[0] == '[':
					# Error message is over, print and return
					print('========= Error detected in Minecraft log file =========')
					print(error_text + '\a')
					print('========================================================')
					return
				else:
					# Error message continues
					if not line.startswith('\t'):
						error_text = error_text + '\n \n' + line
					
				
	
	def try_to_compile(self):
		try:
			self.log(f'Compiling {self.namespace}...')
			success = self.compile_all()
			if success:
				self.log(f"Script successfully applied at {time.ctime()}.")
			else:
				self.log("Script had compile error(s).\a")
		except SyntaxError as e:
			self.log(str(e) + '\a')
		except CompileError as e:
			self.log(str(e) + '\a')
		except Exception as e:
			self.log("Compiler encountered unexpected error during compilation:\a")
			self.log_traceback()
		
	def create_world(self, dir, namespace, worldversion):
		return mcworld.mcworld(dir, namespace, worldversion)
	
	def compile_all(self):
		text = self.source_file.get_text()
	
		result = self.parse(text + "\n")
		
		if result == None:
			self.log('Unable to parse script.')
			return False
		
		type, parsed = result
		
		if type != 'program':
			self.log('Script does not contain a full program.')
			return False
			
		self.global_context = global_context.global_context(self.namespace)
		global_environment = environment(self.global_context)
		global_environment.set_dollarid('namespace', self.namespace)
		global_environment.set_dollarid('get_num_blocks', self.global_context.get_num_blocks)
		global_environment.set_dollarid('get_num_block_states', self.global_context.get_num_block_states)

		if 'scale' not in parsed:
			parsed['scale'] = 10000
		global_environment.set_dollarid('global_scale', parsed['scale'])
		global_func = mcfunction(global_environment)
		
		self.global_context.scale = parsed['scale']
		self.global_context.parser = self.parse

		lines = parsed['lines']
		
		# Register macros and template functions
		for line in lines:
			line.register(self.global_context)

		# Compile all lines
		try:
			global_func.compile_blocks(lines)
		except Exception as e:
			print(e)
			self.dependencies = [source_file(d) for d in self.global_context.dependencies]
			return False
		# Gets the world version of the save
		self.worldversion = self.get_world_version(parsed["dir"])

		self.post_processing()
			
		world = self.create_world(parsed["dir"], self.namespace, self.worldversion)

		latest_log_filename = world.get_latest_log_file()
		if os.path.exists(latest_log_filename):
			self.latest_log_file = source_file(latest_log_filename)

		world.write_data_folder(self.source_file)
		world.write_functions(self.global_context.functions)
		world.write_tags(self.global_context.clocks, self.global_context.block_tags, self.global_context.entity_tags, self.global_context.item_tags)
		world.write_mcmeta(parsed['desc'])
		world.write_recipes(self.global_context.recipes)
		world.write_advancements(self.global_context.advancements)
		world.write_loot_tables(self.global_context.loot_tables)
		world.write_predicates(self.global_context.predicates)
		world.write_item_modifiers(self.global_context.item_modifiers)
		world.write_zip()
		
		self.dependencies = [source_file(d) for d in self.global_context.dependencies]
			
		return True
		
	def post_processing(self):
		self.global_context.finalize_functions()
		self.add_scratch_objectives()
		self.add_temp_objectives()
		self.add_constants()
		self.add_trigger_objectives()
		self.add_registered_objectives()
		self.add_max_chain_length()
		self.initialize_stack()
		self.initialize_args()
		
	def add_max_chain_length(self):
		f = self.global_context.get_reset_function()
		# Gamerule names all changed in 25w44a (1.20.11)
		if self.worldversion >= 4659:
			f.insert_command('/gamerule max_command_sequence_length 1000000000', 0)
		else:
			f.insert_command('/gamerule maxCommandChainLength 1000000000', 0)
		
	def initialize_stack(self):
		f = self.global_context.get_reset_function()
		f.insert_command(f'/data modify storage {self.namespace} stack set value []', 0)
		
	def initialize_args(self):
		f = self.global_context.get_reset_function()
		f.insert_command(f'/data modify storage {self.namespace}:global args set value {{}}', 0)
		
	def add_scratch_objectives(self):
		f = self.global_context.get_reset_function()
		
		for prefix in self.global_context.scratch:			
			for i in range(self.global_context.scratch[prefix]):
				f.insert_command(f'/scoreboard objectives add {prefix}_scratch{i} dummy', 0)
	
	
	def add_temp_objectives(self):
		f = self.global_context.get_reset_function()
		
		for t in range(self.global_context.temp):
			f.insert_command(f'scoreboard objectives add temp{str(t)} dummy', 0)
	
	def add_constants(self):
		self.global_context.add_constant_definitions()
	
	def add_trigger_objectives(self):
		None
	
	def add_registered_objectives(self):
		reset = self.global_context.get_reset_function()
		
		defined = reset.defined_objectives()
		
		for objective in self.global_context.objectives.keys():
			if objective not in defined:
				reset.insert_command(f"/scoreboard objectives add {objective} dummy", 0)
	
	# Get the world version by looking for the most recently modified .json file in the stats directory
	def get_world_version(self, leveldir):
		try:
			# Construct a search path for all .json files in the directory
			statsdir = os.path.join(leveldir, 'stats')
			search_path = Path(statsdir) #os.path.join(statsdir, '*.json')
			list_of_files = search_path.glob("*.json") #glob.glob(search_path)
			key_to_find = 'DataVersion'

			# Handle case where no JSON files are found
			if not list_of_files:
				print(f"Error: No .json files found in '{search_path}'")
				return 0

			# Find the file with the latest modification time
			latest_file = max(list_of_files, key=os.path.getmtime)
			#print(f"Found latest file: {os.path.basename(latest_file)}")

			# Open and read the JSON file
			with open(latest_file, 'r') as f:
				data = json.load(f)

			# Retrieve the value for the specified key.
			value = data.get(str(key_to_find))

			if value is None:
				#print(f"Key '{key_to_find}' not found in {os.path.basename(latest_file)}.")
				return 0
			
			return int(value)
		
		except FileNotFoundError:
			print(f"Error: Directory not found at '{statsdir}'.")
			return 0
		except json.JSONDecodeError:
			print(f"Error: Could not decode JSON from '{os.path.basename(latest_file)}'.")
			return 0
		except Exception as e:
			print(f"An unexpected error occurred: {e}")
			return 0
