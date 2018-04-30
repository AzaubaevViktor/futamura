import dis


def by_2(l: list):
    for i in range(0, len(l), 2):
        yield l[i], l[i + 1]


class Code:
    def __init__(self, code):
        self.consts = code.co_consts
        self.vars = code.co_varnames
        self.names = code.co_names
        self.argcount = code.co_argcount
        self.bytecode = []
        self._parse(code.co_code)

    def _parse(self, co_code):
        for num, arg in by_2(co_code):
            self.bytecode.append(ByteCode(self, num, arg))

    def __getitem__(self, item) -> "ByteCode":
        return self.bytecode[item]

    def __len__(self):
        return len(self.bytecode)


class ByteCode:
    funcs = {
        1: "pop_top",
        20: "binary_multiply",
        23: "binary_add",
        83: "return_value",
        100: "load_const",
        116: "load_global",
        124: "load_fast",
        131: "call_function",
        125: "store_fast",
    }
    def __init__(self, code:Code, num: int, arg: int):
        self.num = num
        self.arg = arg

    def __str__(self):
        return f"<Bytecode {self.funcs[self.num]} {self.arg}>"



class Stack(list):
    def push(self, obj):
        self.append(obj)


class Interpreter:
    def __init__(self, code):
        self.code = Code(code)
        self.glob: dict = {'print': self._print}
        self.stack = Stack()
        self.PC = 0
        self.funcs = None
        self.vars = None
        self._init_func()
        self.is_return = False

    def _print(self, *args, **kwargs):
        print(*args, **kwargs)

    def _init_func(self):
        self.funcs = {
            1: self.pop_top,
            20: self.binary_multiply,
            23: self.binary_add,
            83: self.return_value,
            100: self.load_const,
            116: self.load_global,
            124: self.load_fast,
            131: self.call_function,
            125: self.store_fast
        }

    def run(self, *args, **kwargs):
        self.vars = [None] * len(self.code.vars)

        for i, arg in enumerate(args):
            self.vars[i] = arg

        self.is_return = False
        while not self.is_return and self.PC < len(self.code):
            item = self.code[self.PC]
            self._step(item)
            self.PC += 1

        return self.stack.pop()

    def _step(self, item: ByteCode):
        self.funcs[item.num](item)

    def pop_top(self, item: ByteCode):
        self.stack.pop()

    def binary_add(self, item: ByteCode):
        tos = self.stack.pop()
        tos1 = self.stack.pop()
        self.stack.append(tos1 + tos)

    def binary_multiply(self, item: ByteCode):
        tos = self.stack.pop()
        tos1 = self.stack.pop()
        self.stack.append(tos1 * tos)

    def return_value(self, item: ByteCode):
        self.is_return = True

    def load_global(self, item: ByteCode):
        name_i = item.arg
        self.stack.push(self.glob[self.code.names[name_i]])

    def load_fast(self, item: ByteCode):
        arg_i = item.arg
        self.stack.push(self.vars[arg_i])

    def load_const(self, item: ByteCode):
        const_i = item.arg
        self.stack.push(self.code.consts[const_i])

    def store_fast(self, item: ByteCode):
        var_i = item.arg
        self.vars[var_i] = self.stack.pop()

    def call_function(self, item: ByteCode):
        count = item.arg
        args = []
        for x in range(count):
            args.append(self.stack.pop())
        func = self.stack.pop()
        self.stack.append(func(*args[::-1]))


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
    z = 10
    print(x)
    x = x * 2 + 1 + y
    print(x)
    print(x + 3, "hello!")
    print(z + y)

dis.dis(g)

i = Interpreter(g.__code__)
print("===== simple =====")
print(g(100, 200))
print("=====  hard  =====")
print(i.run(100, 200))