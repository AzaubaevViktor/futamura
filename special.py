import dis
from typing import Union, List

from DefaultDict import DefaultDict


def by_2(l: list):
    for i in range(0, len(l), 2):
        yield l[i], l[i + 1]


class Code:
    def __init__(self, code):
        self.consts = list(code.co_consts)
        self.vars = list(code.co_varnames)
        self.names = list(code.co_names)
        self.argcount = code.co_argcount

        self.kwonlyargcount = code.co_kwonlyargcount
        self.nlocals = code.co_nlocals
        self.stacksize = code.co_stacksize
        self.flags = code.co_flags
        self.names = code.co_names
        self.freevars = list(code.co_freevars)
        self.cellvars = list(code.co_cellvars)
        self.filename = code.co_filename
        self.name = code.co_name
        self.firstlineno = code.co_firstlineno
        self.lnotab = list(code.co_lnotab)

        self.bytecode = []
        self._parse(code.co_code)

    def add_const(self, const) -> int:
        try:
            return self.consts.index(const)
        except ValueError:
            self.consts.append(const)
            return len(self.consts) - 1

    def _parse(self, co_code):
        byte_incs = self.lnotab[0::2]
        line_incs = self.lnotab[1::2]

        line_by_byte = []
        curr_byte = 0
        curr_line = 0

        for bi, li in zip(byte_incs, line_incs):
            line_by_byte += [curr_line] * (bi // 2)
            curr_line += li

        for byte_n, (num, arg) in enumerate(by_2(co_code)):
            line = line_by_byte[byte_n] if len(line_by_byte) > byte_n else curr_line
            self.bytecode.append(ByteCode(num, arg, line))

    def __getitem__(self, item) -> "ByteCode":
        return self.bytecode[item]

    def __len__(self):
        return len(self.bytecode)


class ByteCode:
    funcs = {
        1: "pop_top",
        2: "rot_two",
        20: "binary_multiply",
        23: "binary_add",
        83: "return_value",
        100: "load_const",
        116: "load_global",
        124: "load_fast",
        131: "call_function",
        125: "store_fast",
    }

    def __init__(self, num: int, arg: int, line=None):
        self.num = num
        self.arg = arg
        self.line = line


    def __str__(self):
        return f"<Bytecode {self.funcs[self.num]} {self.arg}, line:{self.line}>"

    def _compile(self):
        return self.num, self.arg

    @staticmethod
    def compile(bytecodes: List["ByteCode"], code: Code):
        def get_code_object():
            return type((lambda x: x).__code__)

        CodeObject = get_code_object()

        data = []
        for item in bytecodes:
            data += list(item._compile())
        data = bytes(data)
        # argcount, kwonlyargcount, nlocals, stacksize, flags, codestring,
        #       constants, names, varnames, filename, name, firstlineno,
        #       lnotab[, freevars[, cellvars]]
        co = CodeObject(
            code.argcount,
            code.kwonlyargcount,
            code.nlocals,
            code.stacksize,
            code.flags,
            data,
            tuple(code.consts),
            tuple(code.names),
            tuple(code.vars),
            code.filename,
            code.name,
            code.firstlineno,
            code.lnotab,
            tuple(code.freevars),
            tuple(code.cellvars),
        )

        for attr in dir(co):
            if "co" in attr:
                print(attr, getattr(co, attr))
        return type(lambda: 0)(co, globals())


class Stack(list):
    def push(self, obj):
        self.append(obj)


class UnknownValue:
    def __add__(self, other):
        return self

    def __radd__(self, other):
        return self

    def __mul__(self, other):
        return self

    def __rmul__(self, other):
        return self

    def __str__(self):
        return f"<UnknownValue>"


class GlobalObject(UnknownValue):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return f"<GlobalObject#{self.name}>"


ROT_TWO_CODE = 2
LOAD_CONST_CODE = 100
LOAD_FAST_CODE = 124
STORE_FAST_CODE = 125

works_with_vars = [
    LOAD_FAST_CODE,
    STORE_FAST_CODE
]

class Specializer:
    def __init__(self, code):
        self.code = Code(code)
        self.glob: dict = {'print': GlobalObject("print")}
        self.stack = Stack()
        self.PC = 0
        self.funcs = None
        self._init_func()
        self.is_return = False
        self.optimized: List[ByteCode] = []
        self.result = None

    def _init_func(self):
        self.funcs = {
            1: self.pop_top,
            ROT_TWO_CODE: self.rot_two,
            20: self.binary_multiply,
            23: self.binary_add,
            83: self.return_value,
            LOAD_CONST_CODE: self.load_const,
            116: self.load_global,
            LOAD_FAST_CODE: self.load_fast,
            131: self.call_function,
            STORE_FAST_CODE: self.store_fast,
        }

    def run(self, *args, **kwargs):
        unknowns = [isinstance(arg, UnknownValue) for arg in args]

        # Заполняем переданные неизвестные номерами, чтобы суметь их идентифицировать после
        self.vars = [None] * len(self.code.vars)

        for i, arg in enumerate(args):
            self.vars[i] = arg
        last = len(args)

        for j in range(last, self.code.argcount):
            self.vars[j] = UnknownValue()

        # Конец подготовки данных
        # Исполняем с нужными аргументами
        self.is_return = False
        while not self.is_return and self.PC < len(self.code):
            item = self.code[self.PC]
            self._step(item)
            self.PC += 1

        #  Изменяем code
        last_unknown = 0
        for arg_i, is_unknown in enumerate(unknowns):
            if is_unknown:
                # Меняем переменные в байткоде
                var_convert = DefaultDict({
                    arg_i: last_unknown,
                    last_unknown: arg_i
                }, default=lambda var_i: var_i)

                for item in self.optimized:
                    if item.num in works_with_vars:
                        item.arg = var_convert[item.arg]
                # Меняем в vars:
                self.code.vars[arg_i], self.code.vars[last_unknown] = self.code.vars[last_unknown], self.code.vars[arg_i]
                last_unknown += 1
            else:
                # Добавляем инициализацию переменной
                self.optimized.insert(0, ByteCode(LOAD_CONST_CODE, 0))  # Load None
                self.optimized.insert(1, ByteCode(STORE_FAST_CODE, arg_i))  # Store to unknown var
                self.code.argcount -= 1

        # Продолжаем: заполняем co_lnotab
        lnotab = []
        cur_line = 0
        bi = 0
        li = 0
        for item in self.optimized:
            if item.line is None:
                item.line = cur_line
            else:
                if item.line != cur_line:
                    li = item.line - cur_line
                    lnotab += [bi, li]
                    bi = 0
                    li = 0
                cur_line = item.line
            bi += 2
        self.code.lnotab = bytes(lnotab)

        # Возвращаем результат
        return self.result, self.optimized, self.code

    def B_add(self, bytecode: ByteCode):
        # add bytecode, big B для понимания, что идёт работа с байткодом
        self.optimized.append(bytecode)

    def B_add_prev(self, bytecode: ByteCode):
        self.optimized.insert(-1, bytecode)

    def B_add_const(self, const_value):
        const_i = self.code.add_const(const_value)
        self.B_add(ByteCode(LOAD_CONST_CODE, const_i))

    def B_add_const_prev(self, const_value):
        const_i = self.code.add_const(const_value)
        self.B_add_prev(ByteCode(LOAD_CONST_CODE, const_i))

    def _step(self, item: ByteCode):
        self.funcs[item.num](item)

    def pop_top(self, item: ByteCode):
        self.stack.pop()

        self.B_add(item)

    def rot_two(self, item: ByteCode):
        a, b = self.stack.pop(), self.stack.pop()
        self.stack.append(a)
        self.stack.append(b)

        self.B_add(item)

    def binary_add(self, item: ByteCode):
        tos = self.stack.pop()
        tos1 = self.stack.pop()
        r = tos1 + tos
        self.stack.append(r)

        if isinstance(r, UnknownValue):
            if not isinstance(tos, UnknownValue):
                self.B_add_const(tos)
            if not isinstance(tos1, UnknownValue):
                if self.optimized[-1].num == LOAD_CONST_CODE:
                    self.B_add_const_prev(tos1)
                else:
                    self.B_add_const(tos1)
                    self.B_add(ByteCode(ROT_TWO_CODE, 0))
            self.B_add(item)

    def binary_multiply(self, item: ByteCode):
        tos = self.stack.pop()
        tos1 = self.stack.pop()
        r = tos1 * tos
        self.stack.append(r)

        if isinstance(r, UnknownValue):
            if not isinstance(tos, UnknownValue):
                self.B_add_const(tos)
            if not isinstance(tos1, UnknownValue):
                if self.optimized[-1].num == LOAD_CONST_CODE:
                    self.B_add_const_prev(tos1)
                else:
                    self.B_add_const(tos1)
                    self.B_add(ByteCode(ROT_TWO_CODE, 0))
            self.B_add(item)

    def return_value(self, item: ByteCode):
        self.is_return = True

        result = self.stack.pop()
        if not isinstance(result, UnknownValue):
            self.B_add_const(result)

        self.B_add(item)

    def load_global(self, item: ByteCode):
        name_i = item.arg
        r = self.glob[self.code.names[name_i]]
        self.stack.push(r)

        self.B_add(item)

    def load_fast(self, item: ByteCode):
        arg_i = item.arg
        r = self.vars[arg_i]
        self.stack.push(r)

        if isinstance(r, UnknownValue):
            self.B_add(item)

    def load_const(self, item: ByteCode):
        const_i = item.arg
        self.stack.push(self.code.consts[const_i])

    def store_fast(self, item: ByteCode):
        var_i = item.arg
        r = self.stack.pop()
        self.vars[var_i] = r

        if isinstance(r, UnknownValue):
            self.B_add(item)

    def call_function(self, item: ByteCode):
        count = item.arg
        args = []
        for x in range(count):
            arg = self.stack.pop()
            args.append(arg)
            if not isinstance(arg, UnknownValue):
                self.B_add_const(arg)
        func = self.stack.pop()
        # Тут позднее будет проверка!
        self.stack.append(UnknownValue())

        self.B_add(item)


def f(a, b):
    if a == 1:
        print("one")
    else:
        print("noone")

    if a + b == 1:
        print("two")
    print(a)
    print(b)


def g(x, y):
    print(x)
    x = x * 2 + 1 + y
    print(x)
    print(x + 3, "hello!")
    return x + y


def test(source_f, args_for_source, args_for_spec, args_for_func):
    print("===== Source func Bytecode: =====")
    dis.dis(source_f)

    spec = Specializer(source_f.__code__)
    print("===== simple run =====")
    print("Return:", source_f(*args_for_source))
    print("=====  hard  =====")

    ret, bytecode, code = spec.run(*args_for_spec)

    print(f"Need Returned: {ret}")
    print(f"Consts: {code.consts}")
    print("Bytecode:")
    for i, item in enumerate(bytecode):
        print("{:>3}".format(i*2), item)

    print("Generate new function")
    func = ByteCode.compile(bytecode, code)
    print("Disassemble:")
    dis.dis(func)
    print("===== RUN: ======")
    ret = func(*args_for_func)
    print(f"Return: {ret}")

def specialize(*args):
    def _spec_decorator(func):
        spec = Specializer(func.__code__)
        ret, bytecode, code = spec.run(*args)
        func = ByteCode.compile(bytecode, code)
        return func
    return _spec_decorator


# test(g, (100, 200), (100, 200), ())

# test(g, (100, 200), (UnknownValue(), 200), (100,))

# test(g, (100, 200), (100, UnknownValue()), (200,))

# test(g, (100, 200), (UnknownValue(), UnknownValue()), (100, 200,))

def h(a, b):
    c = 11
    a = a + c
    b = b + c
    print(a)
    print(b)
    return a * 2 + b * 3

# test(h, (5, 7), (5, 7), ())

# test(h, (5, 7), (UnknownValue(), 7), (5,))
if __name__ == "__main__":
    #                a  b
    test(h, (5, 7), (5, UnknownValue()), (7,))

# test(h, (5, 7), (UnknownValue(), UnknownValue()), (5, 7))
