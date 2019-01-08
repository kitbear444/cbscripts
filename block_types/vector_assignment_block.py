from cbscript import perform_vector_assignment

class vector_assignment_block(block_type):
	def __init__(self, line, var, op, expr):
		self.line = line
		self.var = var
		self.op = open
		self.expr = expr
		
	def compile(self, func):
		if not perform_vector_assignment(func, 'VectorAssignment', self.line, self.var, self.op, self.expr):
			raise Exception('Unable to perform vector assignment at line {}'.format(self.line))