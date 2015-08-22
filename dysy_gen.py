import sys
import os
import ast
import random
import time
import z3
import codegen


class StaticAnalyzer:
    _function_name = None
    _arg_names = None
    _predicates = None
    _expressions = None
    _predicate_pairs = None

    def __init__(self, path_to_subject):
        ast_root = ast.parse(open(path_to_subject).read())

        class CallVisitor(ast.NodeVisitor):
            f = None
            a = []
            p = {}
            e = {}
            pp = {}

            def visit_FunctionDef(self, ast_node):
                self.f = ast_node.name
                for i in range(len(ast_node.args.args)):
                    self.a.append(ast_node.args.args[i].id)
                self.generic_visit(ast_node)

            def visit_If(self, ast_node):
                self._add_predicate_to_map(ast_node)

            def visit_While(self, ast_node):
                self._add_predicate_to_map(ast_node)

            def visit_Assign(self, ast_node):
                self.e[ast_node.lineno] = codegen.to_source(ast_node.targets[0]), codegen.to_source(ast_node.value)

            def get_function_name_with_args(self):
                return self.f, self.a

            def get_predicates(self):
                return self.p

            def get_expressions(self):
                return self.e

            def get_predicate_pairs(self):
                return self.pp

            def _add_predicate_to_map(self, ast_node):
                test = ast_node.test
                body = ast_node.body
                orelse = ast_node.orelse
                if_line_no = ast_node.lineno
                self.p[if_line_no] = codegen.to_source(test)
                if orelse is None or len(orelse) < 1:
                    end_if = body[len(body) - 1]
                    else_line_no = end_if.lineno + 1
                    #self.p[else_line_no] = "not" + codegen.to_source(test)
                else:
                    else_line_no = orelse[0].lineno
                    #self.p[else_line_no] = "not" + codegen.to_source(test)
                self.pp[if_line_no] = else_line_no
                #self.pp[else_line_no] = if_line_no
                self.generic_visit(ast_node)

        v = CallVisitor()
        v.visit(ast_root)
        (self._function_name, self._arg_names) = v.get_function_name_with_args()
        self._predicates = v.get_predicates()
        self._expressions = v.get_expressions()
        self._predicate_pairs = v.get_predicate_pairs()

    def generate_random_function_call(self):
        """
        @return: string, <function_name>(<param1>, <param2>)
        """
        call = self._function_name + "("
        for i in range(len(self._arg_names)):
            call = call + repr(StaticAnalyzer.generate_arg_value(self._arg_names[i])) + ", "
        call = call[:-2] + ")"
        return call

    def get_arg_names(self):
        return self._arg_names

    def get_function_name(self):
        return self._function_name

    def is_expr(self, line_no):
        return line_no in self._expressions

    def is_control(self, line_no):
        return line_no in self._predicates

    def get_predicate(self, line_no):
        return self._predicates[line_no]

    def get_other_predicate(self, line_no):
        return self._predicate_pairs[line_no], "not" + self._predicates[line_no]

    def get_expr(self, line_no):
        return self._expressions[line_no]

    @staticmethod
    def is_contains_call(predicate):
        class ContainsCall(ast.NodeTransformer):
            _c = False

            def visit_Call(self, node):
                self._c = True

            def is_contains(self):
                return self._c
        cv = ContainsCall()
        cv.visit(ast.parse(predicate))
        return cv.is_contains()

    @staticmethod
    def generate_symbolic_expression(expression, symbolic_state, local_vars, arg_names):
        """
        @expression: string, expression to be transformed
        @symbolic_state: map<string, string>, current symbolic state
        @local_vars: map<string, Object>, map of concrete values
        @ arg_names : list<string>, list of arg names of the target function
        """

        class Concretize(ast.NodeTransformer):

            def visit_Name(self, node):
                if node.id in local_vars and node.id not in arg_names:
                    return ast.copy_location(ast.Num(local_vars[node.id]), node)
                return node
        class ReplaceByNode(ast.NodeTransformer):
            _var_name = None
            _new_node = None

            def __init__(self, var_name, new_node):
                self._var_name = var_name
                self._new_node = new_node

            def visit_Name(self, this_node):
                if this_node.id == self._var_name:
                    return self._new_node
                else:
                    return this_node

        class ReplaceName(ast.NodeTransformer):

            def visit_Subscript(self, node):
                new_node_str = codegen.to_source(node)
                if new_node_str.find("seq") >= 0:
                    Concretize().visit(node)
                else:
                    return node
                if new_node_str.find("int") >= 0:
                    z3_node = ast.parse("z3.Int(x)")
                elif new_node_str.find("real") >= 0:
                    z3_node = ast.parse("z3.Real(x)")
                else:
                    return node

                # fix the symbolic names
                new_node_str = codegen.to_source(node)
                print "Before ", new_node_str
                first_sub = new_node_str.find('[')
                new_node_str = new_node_str[0:first_sub] + "#" + new_node_str[first_sub + 1:-1]
                print "After ", new_node_str
                s_new_node = ast.Str(new_node_str)
                ReplaceByNode('x', s_new_node).visit(z3_node)
                return z3_node

            def visit_Name(self, node):
                if node.id in arg_names:
                    if node.id.find("seq") >= 0:
                        return node
                    # create z3 node
                    if node.id.find("int") >= 0:
                        z3_node = ast.parse("z3.Int(x)")
                    elif node.id.find("real") >= 0:
                        z3_node = ast.parse("z3.Real(x)")
                    else:
                        return node

                    # fix the symbolic names
                    new_node_str = codegen.to_source(node) + "#"
                    # replace x by this new_node
                    s_new_node = ast.Str(new_node_str)
                    ReplaceByNode('x', s_new_node).visit(z3_node)
                    return z3_node
                elif node.id in symbolic_state:
                    # print node.id, symbolic_state[node.id]
                    return ast.parse(symbolic_state[node.id])
                elif node.id in local_vars:
                    return ast.copy_location(ast.Num(local_vars[node.id]), node)
                else:
                    return node

        print "Actual - ", expression
        parsed_exp = ast.parse(expression)

        class ReplaceCalls(ast.NodeTransformer):
            def visit_Call(self, node):
                return ast.Num(15)

        symbolic_exp = ReplaceCalls().visit(parsed_exp)
        symbolic_exp = ReplaceName().visit(symbolic_exp)

        class BoolTransform(ast.NodeTransformer):

            def visit_UnaryOp(self, node):
                # print "XX", codegen.to_source(node), node.op, node.op == ast.NotEq, node.op == ast.Not, node.op == ast.IsNot, codegen.to_source(node.op)
                old_source = codegen.to_source(node)
                if old_source.find("not") >= 0:
                    new_source = old_source.replace("not", "z3.Not")
                    return ast.parse(new_source)
                else:
                    return node

        symbolic_exp = BoolTransform().visit(symbolic_exp)

        return_val = codegen.to_source(symbolic_exp)
        return_val = return_val.replace('\n', ' ')
        print "Symbolic - ", return_val
        return return_val

    @staticmethod
    def generate_arg_value(arg_name):
        """
        @ arg_name: string, eg. int_array_seq, real_a, ...
        @return: mixed, [3, 5, 1, 5, 9] for int_xx_seq, <rand_int> for int_xx, ...
        """
        if arg_name.find("int") >= 0:
            if arg_name.find("seq") >= 0:
                arg_value = []
                for i in range(15):
                    arg_value.append(random.randint(5, 10))
            else:
                arg_value = random.randint(5, 10)
        else:
            if arg_name.find("seq") >= 0:
                arg_value = []
                for i in range(15):
                    arg_value.append(random.uniform(0.5, 1) * 10)
            else:
                arg_value = random.uniform(0.5, 1) * 10
        return arg_value

    @staticmethod
    def generate_single_arg_value(arg_name):
        if arg_name.find("int") >= 0:
            arg_value = random.randint(5, 10)
        else:
            arg_value = random.uniform(0.5, 1) * 10
        return arg_value

    @staticmethod
    def get_z3_wrap(arg_name):
        if arg_name.find('int') >= 0:
            return "z3.Int"
        else:
            return "z3.Real"


class ConstraintSolver:
    def __init__(self):
        pass

    @staticmethod
    def solve_constraints(constraints):
        solved_constraints = {}
        s = z3.Solver()
        for constraint in constraints:
            parsed_constraint = ast.parse(constraint, mode='eval')
            compiled_constraint = compile(parsed_constraint, '<string>', 'eval')
            e_constraint = eval(compiled_constraint)
            s.add(e_constraint)
        if s.check() == z3.sat:
            m = s.model()
            for d in m.decls():
                solved_value = m[d]
                if solved_value.is_int():
                    solved_constraints[d.name()] = int(solved_value.as_string())
                else:
                    solved_constraints[d.name()] = eval("1.0 * " + solved_value.as_string())
            return solved_constraints
        return None


class TraceState:
    static_analyzer = None
    symbolic_state = None
    unsolved_constraints = None
    solved_constraints = None
    current_constraints = None

    def __init__(self, sr, uc, sc):
        self.static_analyzer = sr
        self.symbolic_state = {}
        self.unsolved_constraints = uc
        self.solved_constraints = sc
        self.current_constraints = []


_trace_state = None


def trace_lines(frame, event, arg):
    def check_true(p, value_map):
        for var, val in value_map.items():
            locals()[var] = val
        return eval(compile(ast.parse(p, mode='eval'), '<string>', 'eval'))

    if event != 'line':
        return
    co = frame.f_code
    func_name = co.co_name
    line_no = frame.f_lineno
    local_vars = frame.f_locals
    if _trace_state.static_analyzer.is_expr(line_no):
        (target, expression) = _trace_state.static_analyzer.get_expr(line_no)
        symbolic_expression = _trace_state.static_analyzer.generate_symbolic_expression(
            expression, _trace_state.symbolic_state, local_vars, _trace_state.static_analyzer.get_arg_names())
        _trace_state.symbolic_state[target] = symbolic_expression
    if _trace_state.static_analyzer.is_control(line_no):
        this_predicate = _trace_state.static_analyzer.get_predicate(line_no)
        # # skip if predicate contains function call
        # if StaticAnalyzer.is_contains_call(this_predicate):
        #     return
        #print local_vars
        is_true = check_true(this_predicate, local_vars)
        #print locals()
        if is_true:
            true_predicate = this_predicate
            true_line_no = line_no
            (false_line_no, false_predicate) = _trace_state.static_analyzer.get_other_predicate(line_no)
        else:
            false_predicate = this_predicate
            false_line_no = line_no
            (true_line_no, true_predicate) = _trace_state.static_analyzer.get_other_predicate(line_no)
        # remove from unsolved constraints and add it to solved
        print "True predicate", true_line_no, true_predicate, "\t", "False predicate", false_line_no, false_predicate
        if true_line_no in _trace_state.unsolved_constraints:
            _trace_state.unsolved_constraints.pop(true_line_no)
        _trace_state.solved_constraints[true_line_no] = True
        if false_line_no not in _trace_state.solved_constraints:
            symbolic_false_predicate = _trace_state.static_analyzer.generate_symbolic_expression(
                false_predicate, _trace_state.symbolic_state, local_vars, _trace_state.static_analyzer.get_arg_names())
            _trace_state.unsolved_constraints[false_line_no] = _trace_state.current_constraints + [
                symbolic_false_predicate]
        symbolic_true_predicate = _trace_state.static_analyzer.generate_symbolic_expression(
            true_predicate, _trace_state.symbolic_state, local_vars, _trace_state.static_analyzer.get_arg_names())
        #print symbolic_true_predicate
        _trace_state.current_constraints.append(symbolic_true_predicate)
        print line_no, "Unsolved constraints", _trace_state.unsolved_constraints


def trace_calls(frame, event, arg):
    if event != 'call':
        return
    co = frame.f_code
    func_name = co.co_name
    if func_name != _trace_state.static_analyzer.get_function_name():
        return
    return trace_lines


class SymbolicExecutor:
    _static_analyzer = None
    _solved_constraints = None  # map of line numbers to True that are solved.
    _unsolved_constraints = None  # map of line numbers to the corresponding constraints that are yet to be solved.
    _module_name = None

    def __init__(self, path_to_subject):
        self._solved_constraints = {}
        self._unsolved_constraints = {}
        self._static_analyzer = StaticAnalyzer(path_to_subject)
        self._module_name = os.path.splitext(os.path.basename(path_to_subject))[0]
        #init constraints so that they yield some values in the beginning
        initial_constraints = []
        arg_names = self._static_analyzer.get_arg_names()
        for arg_name in arg_names:
            arg_value_or_list = StaticAnalyzer.generate_arg_value(arg_name)
            z3_string = StaticAnalyzer.get_z3_wrap(arg_name)
            if type(arg_value_or_list) == list:
                for i in range(len(arg_value_or_list)):
                    constraint = z3_string + "('" + arg_name + "#" + str(i) + "')==" + str(arg_value_or_list[i])
                    initial_constraints.append(constraint)
            else:
                constraint = z3_string + "('" + arg_name + "#')" + "==" + str(arg_value_or_list)
                initial_constraints.append(constraint)
        self._unsolved_constraints[-1] = initial_constraints
        self._static_analyzer.is_expr(1)
        global _trace_state
        _trace_state = TraceState(self._static_analyzer, self._unsolved_constraints, self._solved_constraints)
        sys.settrace(trace_calls)

    def get_next_function_call(self, **kw):
        """
        @return: string/None, a non-empty string if the next call covers an additional branch, An empty string if a call
                is generated but does not cover additional branch. None if no constraints are left to solve.
        """
        global _trace_state
        _trace_state = TraceState(self._static_analyzer, self._unsolved_constraints, self._solved_constraints)
        if len(self._unsolved_constraints) > 0:
            # pop next unsolved constraint
            (line_no, constraints) = self._unsolved_constraints.popitem()
            # solve the constraint
            print "Solving constraints ", line_no, " ", constraints
            solved_variables = ConstraintSolver.solve_constraints(constraints)
            print "Solved constraints", solved_variables
            if solved_variables is None:
                print "SKIP - Unsatisfiable constraints"
                return None
            # generate function call
            arg_values = {}
            for variable_name, variable_value in solved_variables.items():
                if variable_name[-1] == '#':
                    arg_values[variable_name[:-1]] = variable_value
                else:
                    variable_name_n_index = variable_name.split("#")
                    variable_name_only = variable_name_n_index[0]
                    variable_index_only = int(variable_name_n_index[1])
                    if variable_name_only not in arg_values:
                        arg_values[variable_name_only] = [None] * 15
                    arg_values[variable_name_only][variable_index_only] = variable_value
            #fill missing values
            for a_name in self._static_analyzer.get_arg_names():
                if a_name not in arg_values:
                    arg_values[a_name] = self._static_analyzer.generate_arg_value(a_name)
                elif a_name.find("seq") >= 0:
                    old_value = arg_values[a_name]
                    new_value = [None] * 15
                    for i in range(15):
                        if old_value[i] is None:
                            new_value[i] = self._static_analyzer.generate_single_arg_value(a_name)
                        else:
                            new_value[i] = old_value[i]
                    arg_values[a_name] = new_value

            call = self._static_analyzer.get_function_name() + "("
            for arg_name, arg_value_rep in arg_values.items():
                call = call + arg_name + "=" + repr(arg_value_rep) + " ,"
            call = self._module_name + "." + call[:-1] + ")"
            # execute the call
            num_solved = len(self._solved_constraints)
            print "CALLING - ", call
            exec call in kw
            # check if more constrains are solved now
            if len(self._solved_constraints) > num_solved:
                print "ADD - ", call
                return call
            else:
                print "SKIP - Already covered", call
                return ""
        else:
            print "NO-CONSTRAINT - "
            return None

    def close(self):
        sys.settrace(None)


class TestWriter:
    """
    Helper class for generating the final test file. The test cases are output
    in accordance with the TestCase framework.
    """
    _file = None
    _indent = None
    _test_num = None
    _test_case_num = None

    def _get_base_code(self, module_name):
        start = '''\
import {0}
import unittest

class RandomTestCases(unittest.TestCase) :

'''.format(module_name)
        # start = start + ' ' * self._indent + "def test0(self) :" + "\n"
        return start

    def __init__(self, od, subject_module):
        """
        @output_dir : The output directory where test cases should be written.
        @subject : The subject filename to be imported in test file.
        """
        self._indent = 2
        self._test_num = 0
        self._test_case_num = 0
        file_name = "Test_" + subject_module + "_Test.py"
        self._file = open(os.path.join(od, file_name), 'w')
        self._file.write(self._get_base_code(subject_module))

    def add_function_call_to_test(self, function_call, start_new):
        if len(function_call) == 0:
            return
        if start_new:
            self._test_case_num += 1
            self._file.write("\n" + ' ' * self._indent + "def test" + str(self._test_case_num) + "(self) :" + "\n")
        self._file.write(' ' * self._indent * 2 + function_call + "\n")
        self._test_num += 1

    def close(self):
        """
        @return : None, Creates the final and valid PyUnit test file.
        """
        if self._test_num == 0:
            self._file.write(' ' * self._indent * 2 + "pass\n")

        end_string = '''\
if __name__ == '__main__':
unittest.main()
suite = unittest.TestLoader().loadTestsFromTestCase(RandomTestCases)
unittest.TextTestRunner(verbosity=2).run(suite)
'''
        lines = end_string.split('\n')
        joiner = '\n' + ' ' * self._indent
        fixed_string = joiner.join(lines)
        self._file.write(fixed_string)
        self._file.close()


def main():
    start = current = time.time()
    random.seed()
    if len(sys.argv) < 4:
        print "Usage: dysy_gen.py <path_to_subject.py> <output_dir> <timeout>"
        return -1
    path_to_subject = sys.argv[1]
    subject_module = os.path.splitext(os.path.basename(path_to_subject))[0]
    output_dir = sys.argv[2]
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    timeout = int(sys.argv[3]) - 2
    test_writer = TestWriter(output_dir, subject_module)
    symbolic_executor = SymbolicExecutor(path_to_subject)
    total_added = 0
    total_skipped = 0
    start_new_test_case = True
    while int(current - start) < timeout:
        current = time.time()
        function_call = symbolic_executor.get_next_function_call(**{subject_module: __import__(subject_module)})
        if function_call is None:
            print "Reinit symbolic executor"
            symbolic_executor = SymbolicExecutor(path_to_subject)
            start_new_test_case = True
            continue
        if len(function_call) > 0:
            test_writer.add_function_call_to_test(function_call, start_new_test_case)
            total_added += 1
            start_new_test_case = False
        else:
            total_skipped += 1
    test_writer.close()
    symbolic_executor.close()
    print "ADDED - ", total_added
    print "SKIPPED - ", total_skipped
    return 0


if __name__ == "__main__":
    sys.exit(main())
