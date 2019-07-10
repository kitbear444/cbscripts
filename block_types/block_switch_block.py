from block_switch_base import block_switch_base
from CompileError import CompileError

class block_switch_block(block_switch_base):
	def __init__(self, line, coords, cases):
		self.line = line
		self.coords = coords
		self.cases = cases
		
		super(block_switch_block, self).__init__()
		
	def case_condition(self, func, block_state):
		return 'block {} {}'.format(self.coords.get_value(func), block_state)
		
	def compile_block_case(self, func, block):
		if 'properties' in self.blocks[block]:
			case_func = func.create_child_function()
			
			props = self.blocks[block]['properties']
			self.compile_property_case(case_func, block, props.keys(), props, '{}['.format(block))
			func.call_function(
				case_func,
				'line{0:03}/switch_{1}/{1}'.format(self.line, block.replace('minecraft:','')),
				'execute if block {} {} run '.format(self.coords.get_value(func), block)
			)
		else:
			self.compile_single_case(
				func,
				block,
				'line{:03}/case_{}'.format(self.line, block.replace('minecraft:',''))
			)
			
	def compile_property_case(self, func, block, prop_names, props, partial_block_state):
		cur_prop_name = prop_names[0]
		cur_prop = props[cur_prop_name]
	
		if len(prop_names) == 1:
			for value in cur_prop:
				block_state = '{}{}={}]'.format(partial_block_state, cur_prop_name, value)
				self.compile_single_case(
					func,
					block_state,
					'line{:03}/switch_{}/{}_{}'.format(self.line, block.replace('minecraft:',''), cur_prop_name, value)
				)
		else:
			for value in cur_prop:
				block_state = '{}{}={},'.format(partial_block_state, cur_prop_name, value)
				
				case_func = func.create_child_function()
				
				self.compile_property_case(case_func, block, prop_names[1:], props, block_state)
				func.call_function(
					case_func,
					'line{:03}/switch_{}/{}_{}'.format(self.line, block.replace('minecraft:',''), cur_prop_name, value),
					'execute if block {} {}[{}={}] run '.format(self.coords.get_value(func), block, cur_prop_name, value)
				)
				
			
	def compile_single_case(self, func, block_state, case_func_name):
		id = self.block_state_ids[block_state]
		case = self.block_state_list[block_state]
		falling_block_nbt = self.falling_block_nbt[block_state]
		
		case_func = func.create_child_function()
		try:
			case.compile(block_state, id, case_func, falling_block_nbt)
		except CompileError as e:
			print(e)
			raise CompileError('Unable to compile block switch case "{}" at line {}'.format(block_state, self.line))
			
		func.call_function(
			case_func,
			case_func_name,
			'execute if {} run '.format(self.case_condition(func, block_state))
		)
	
	def get_range_condition(self, func, blocks):
		unique = func.get_unique_id()
		block_tag_name = 'switch_{}'.format(unique)
		func.register_block_tag(block_tag_name, [block.replace('minecraft:', '') for block in blocks])
		
		return 'block {} #{}:{}'.format(self.coords.get_value(func), func.namespace, block_tag_name)
		
	def get_case_ids(self):
		return sorted(self.block_list.keys())