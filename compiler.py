import os
import platform
import sys
from typing import Tuple


class LimeError(Exception):
    """Ошибка компиляции/выполнения Lime с привязкой к строке исходника."""

    def __init__(self, message: str, line: int = None, path: str = None, hint: str = None):
        self.message = message
        self.line = line
        self.path = path
        self.hint = hint
        super().__init__(message)


def resolve_lua_line(line_map: list, lua_line: int):
    best = None
    for mapped_lua_line, lime_line in line_map:
        if mapped_lua_line <= lua_line:
            if best is None or mapped_lua_line > best[0]:
                best = (mapped_lua_line, lime_line)
    return best[1] if best else None


def format_lime_error(message: str, line: int = None, code: str = None, path: str = None, hint: str = None) -> str:
    RED = "\033[31m"
    GRAY = "\033[90m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    out = [f"{RED}{BOLD}Lime Error{RESET}: {message}"]

    if line is not None and code is not None:
        lines = code.splitlines()
        location = f"{path}/main.lm:{line}" if path else f"строка {line}"
        out.append(f"{GRAY} --> {location}{RESET}")
        start = max(1, line - 2)
        end = min(len(lines), line + 1)
        width = len(str(end))
        for n in range(start, end + 1):
            src_line = lines[n - 1] if 0 <= n - 1 < len(lines) else ""
            if n == line:
                out.append(f"{RED}{BOLD}{n:>{width}} | {src_line}{RESET}")
                out.append(f"{' ' * width} | {RED}{'^' * max(1, len(src_line.strip()))}{RESET}")
            else:
                out.append(f"{GRAY}{n:>{width}} | {src_line}{RESET}")
    elif line is not None:
        out.append(f"{GRAY} --> {line}{RESET}")

    if hint is not None:
        out.append(f"{GRAY}Hint: {hint}{RESET}")

    return "\n".join(out)


keys = ["if", "elif", "ret", "fn", "else", "use", "match", "case", "var", "for", "loop", "load", "struct", "usec", "as",
        "in", "next", "stop", "try", "catch"]
ops = ['=', '+', '-', "*", '/', '==', '!=', '//', '%', '(', ')', '{', '}', '>', '<', '>=', '<=', ':', ';', '#', '.',
       ',', "^", '[', ']', '|', '&', '!', '..', "::", '+=', '-=', '*=', '/=', '->', '>>', '`']


def get_libs_path():
    if getattr(sys, 'frozen', False):

        p = os.path.dirname(sys.executable)
    else:

        p = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(p, "libs")


def lex(code) -> list[Tuple[str, str, int]]:
    chars: list[str] = list(code)
    tokens = []
    i = 0
    line = 1

    def get(x=0):
        nonlocal i
        if i + x < len(chars):
            return chars[i + x]
        return ''

    def advance():
        nonlocal i, line
        if get() == '\n':
            line += 1
        i += 1

    def pnum():
        start_line = line
        num = ""
        if get() == '0' and get(1) == 'x':
            num += get()
            advance()
            num += get()
            advance()
            while get().isdigit() or get().lower() in 'abcdef':
                num += get()
                advance()
            tokens.append(("NUM", num, start_line))  # оставляем как строку
            return
        while i < len(chars) and (get().isdigit() or get() == '.'):
            num += get()
            advance()
        tokens.append(("NUM", num, start_line))

    def pcom():
        while get() != "\n" and i < len(chars):
            advance()

    def pmcom():
        # Пропускаем всё до "*/" (раньше при любой '*' внутри комментария парсинг
        # обрывался раньше времени и мог перескочить закрывающую последовательность)
        while i < len(chars) and not (get() == "*" and get(1) == "/"):
            advance()
        if i < len(chars):
            advance()  # '*'
            advance()  # '/'

    def pstr(c):
        start_line = line
        s = ""

        escapes = {
            'n': '\\n',  # Новая строка
            't': '\\t',  # Табуляция
            'r': '\\r',  # Возврат каретки
            '\\': '\\\\',  # Обратный слэш
            '"': '\\"',  # Двойная кавычка
            "'": "\\'",
            '0': '\\0',  # Нуль-символ
            'a': '\\a',  # Звонок (bell)
            'b': '\\b'  # Забой (backspace)
        }

        while i < len(chars) and get() != c:
            ch = get()
            if ch == '\\':
                advance()
                if i < len(chars):
                    next_ch = get()
                    s += escapes.get(next_ch, next_ch)
                else:
                    break
            else:
                s += ch

            advance()

        advance()
        tokens.append(("STR", s, start_line))

    def pID():
        start_line = line
        s = ""
        while i < len(chars) and (get().isalpha() or get() == "_" or get().isdigit()):
            s += get()
            advance()
        if s in keys:
            tokens.append(("KEY", s, start_line))
            return
        tokens.append(("ID", s, start_line))

    while i < len(chars):
        if get().isdigit():
            pnum()
        elif get() == '"':
            advance()
            pstr('"')
        elif get() == "'":
            advance()
            pstr("'")
        elif get() == '/' and get(1) == '/':
            advance()
            advance()
            pcom()
        elif get() == '/' and get(1) == '*':
            advance()
            advance()
            pmcom()
        elif get().isalpha() or get() == "_":
            pID()
        elif get() in ops:
            start_line = line
            op = get()
            advance()
            while i < len(code) and op + get() in ops:
                op += get()
                advance()
            tokens.append(("OP", op, start_line))
        else:
            advance()

    return tokens


from typing import List, Tuple, Any, Dict


class Parser:
    def __init__(self, tokens: List[Tuple[str, str, int]]):
        self.tokens = tokens
        self.pos = 0
        self._last_line = tokens[-1][2] if tokens else 1

    def peek(self, x=0) -> tuple[str, str, int]:
        if self.pos + x < len(self.tokens):
            return self.tokens[self.pos + x]
        return ('EOF', '', self._last_line)

    def next(self) -> Tuple[str, str, int]:
        tok = self.peek()
        self.pos += 1
        return tok

    def line(self) -> int:
        """Номер строки текущего (ещё не съеденного) токена."""
        return self.peek()[2]

    def match(self, expected_type: str) -> Tuple[str, str, int]:
        tok = self.peek()
        if tok[0] == expected_type:
            return self.next()
        raise LimeError(f"Ожидался {expected_type}, получен {tok[0]} '{tok[1]}'", line=tok[2])

    def match_op(self, expected_op: str) -> Tuple[str, str, int]:
        """Точная проверка конкретного оператора / пунктуации."""
        tok = self.peek()
        if tok[0] == 'OP' and tok[1] == expected_op:
            return self.next()
        raise LimeError(f"Ожидался оператор '{expected_op}', получен {tok[0]} '{tok[1]}'", line=tok[2])

    def parse(self) -> List[Dict]:
        """Парсит программу (список statement'ов)"""
        statements = []
        while self.peek()[0] != 'EOF':
            stmt = self.parse_statement()
            if stmt:
                statements.append(stmt)
        return statements

    def parse_statement(self) -> Dict:
        """Парсит один statement"""
        start_line = self.line()
        stmt = self._parse_statement_inner()
        if isinstance(stmt, dict) and 'line' not in stmt:
            stmt['line'] = start_line
        return stmt

    def _parse_statement_inner(self) -> Dict:
        if self.peek()[0] == 'KEY' and self.peek()[1] == 'var':
            return self.parse_var()
        if self.peek()[0] == 'KEY' and self.peek()[1] == 'if':
            return self.parse_if()
        if self.peek()[0] == 'KEY' and self.peek()[1] == 'fn':
            return self.parse_fn()
        if self.peek()[0] == 'KEY' and self.peek()[1] == 'loop':
            return self.parse_loop()
        if self.peek()[0] == 'KEY' and self.peek()[1] == 'for':
            return self.parse_for()
        if self.peek()[0] == 'KEY' and self.peek()[1] == 'ret':
            return self.parse_ret()
        if self.peek()[0] == 'KEY' and self.peek()[1] == 'load':
            return self.parse_load()
        if self.peek()[0] == 'KEY' and self.peek()[1] == 'use':
            return self.parse_use()
        if self.peek()[0] == 'KEY' and self.peek()[1] == 'struct':
            return self.parse_struct()
        if self.peek()[0] == 'KEY' and self.peek()[1] == 'usec':
            return self.parse_usec()
        if self.peek()[0] == 'KEY' and self.peek()[1] == 'match':
            return self.parse_switch()
        if self.peek()[0] == 'KEY' and self.peek()[1] == 'next':
            return self.parse_next()
        if self.peek()[0] == 'KEY' and self.peek()[1] == 'stop':
            return self.parse_stop()
        if self.peek()[0] == 'KEY' and self.peek()[1] == 'try':
            return self.parse_stop()
        if self.peek()[0] == 'ID' and self.peek(1)[1] == ":":
            return self.parse_met()
        if self.peek()[0] == 'ID' and self._is_assignment_ahead():
            return self.parse_change()
        if self.peek()[1] == '{':
            return self.parse_block()
        if self.peek()[0] == 'OP' and self.peek()[1] == ";":
            self.next()
            return {"type": "end"}
        return self.parse_expression()

    def parse_block(self):
        statements = []
        self.match_op('{')

        while self.peek()[1] != "}":
            if self.peek()[0] == 'EOF':
                raise LimeError("Ожидалась '}'", line=self.line())
            statements.append(self.parse_statement())

        self.match_op('}')

        return {"type": "block", "statements": statements}

    def parse_switch(self):
        self.next()
        expr = self.parse_expression()
        tok = self.next()
        if tok[1] != ":":
            raise LimeError("Need ':' token but given " + tok[1], line=tok[2])
        cases = []
        while self.peek()[1] == "case":
            self.next()
            e = self.parse_expression()
            cases.append({"expr": e, "stmt": self.parse_statement()})
        return {"type": "match", "expr": expr, "cases": cases}

    def parse_met(self):
        cls = self.match("ID")[1]
        self.match_op(":")
        func = self.match("ID")[1]
        if self.peek()[0] != "OP" or self.peek()[1] != "(":
            raise LimeError("Need '(' token but given " + self.peek()[1], line=self.line())
        self.next()
        args = []
        while self.peek()[1] != ")":
            args.append(self.match("ID")[1])
            if self.peek()[1] == ",":
                self.next()
        self.match_op(")")
        stmt = self.parse_statement()
        return {'type': 'method', 'cls': cls, 'func': func, 'params': args, 'stmt': stmt}

    def parse_struct(self):
        self.match("KEY")
        name = self.match("ID")[1]
        if self.peek()[1] != '{':
            raise LimeError(f"Expected '{{' after struct {name}, but got {self.peek()[0]}", line=self.line())
        self.next()
        fields = []

        while not (self.peek()[0] == "OP" and self.peek()[1] == "}"):
            if self.peek()[0] == 'EOF':
                raise LimeError("Ожидалась '}'", line=self.line())
            n = self.match("ID")[1]
            self.match_op(":")
            t = self.match("ID")[1]
            fields.append({"name": n, "type": t})

            if self.peek()[1] == ',':
                self.next()

        self.match_op("}")

        return {
            'type': 'struct',
            'name': name,
            'fields': fields
        }

    def parse_if(self) -> Dict:
        self.match('KEY')
        expr = self.parse_expression()
        stmt = self.parse_statement()
        elifs = []
        while self.peek()[0] == 'KEY' and self.peek()[1] == 'elif':
            self.next()
            expr_ = self.parse_expression()
            stmt_ = self.parse_statement()
            elifs.append({'type': 'elif', 'expr': expr_, 'stmt': stmt_})
        estmt = {}
        if self.peek()[0] == 'KEY' and self.peek()[1] == 'else':
            self.next()
            estmt = self.parse_statement()
        return {'type': 'if', 'expr': expr, 'stmt': stmt, 'elifs': elifs, 'else': {'stmt': estmt}}

    def parse_loop(self) -> Dict:
        self.match('KEY')
        expr = self.parse_expression()
        stmt = self.parse_statement()
        return {'type': 'loop', 'expr': expr, 'stmt': stmt}

    def parse_load(self) -> Dict:
        self.match('KEY')
        expr = self.parse_expression()
        return {'type': 'load', 'expr': expr}

    def parse_use(self) -> Dict:
        self.match('KEY')
        expr = self.parse_expression()
        return {'type': 'use', 'expr': expr}

    def parse_next(self) -> Dict:
        self.match('KEY')
        return {'type': 'next'}

    def parse_stop(self) -> Dict:
        self.match('KEY')
        return {'type': 'stop'}

    def parse_usec(self) -> Dict:
        self.match('KEY')
        expr = self.parse_expression()
        using = {'rule': '', 'as': ''}
        if self.peek()[0] == "OP" and self.peek()[1] == '{':
            self.next()
            using["rule"] = self.parse_expression()
            self.match_op("}")
        if self.peek()[1] == "as" and self.peek()[0] == "KEY":
            self.next()
            using["as"] = self.parse_expression()
        return {'type': 'usec', 'expr': expr, "rules": using}

    def _is_for_in_ahead(self) -> bool:
        p = self.pos
        if self.tokens[p][0] != 'ID':
            return False
        p += 1
        while p < len(self.tokens) and self.tokens[p][0] == 'OP' and self.tokens[p][1] == ',':
            p += 1
            if p >= len(self.tokens) or self.tokens[p][0] != 'ID':
                return False
            p += 1
        return p < len(self.tokens) and self.tokens[p][0] == 'KEY' and self.tokens[p][1] == 'in'

    def parse_for(self) -> Dict:
        self.match('KEY')  # 'for'
        if self._is_for_in_ahead():
            return self.parse_for_in()
        start = self.parse_statement()
        self.match_op(',')
        expr = self.parse_expression()
        self.match_op(',')
        step = self.parse_expression()
        stmt = self.parse_statement()
        return {'type': 'for', 'start': start, 'expr': expr, 'step': step, 'stmt': stmt}

    def parse_for_in(self) -> Dict:
        names = [self.match('ID')[1]]
        while self.peek()[0] == 'OP' and self.peek()[1] == ',':
            self.next()
            names.append(self.match('ID')[1])
        self.match('KEY')  # 'in'
        expr = self.parse_expression()
        stmt = self.parse_statement()
        return {'type': 'for_in', 'names': names, 'expr': expr, 'stmt': stmt}

    def parse_fn(self) -> Dict:
        self.match('KEY')
        name = self.match('ID')[1]
        self.match_op('(')
        args = []
        while self.peek()[1] != ")":
            args.append(self.match("ID")[1])
            if self.peek()[1] == ",":
                self.next()
        self.match_op(')')
        stmt = self.parse_statement()
        return {'type': 'fs', 'name': name, 'params': args, 'stmt': stmt}

    def parse_ret(self) -> Dict:
        self.match('KEY')
        expr = self.parse_expression()
        return {'type': 'ret', 'expr': expr}

    def parse_var(self) -> Dict:
        """var x = 10 + 2"""
        self.match('KEY')  # 'var'
        name = self.match('ID')[1]
        self.match_op('=')
        expr = self.parse_expression()
        return {'type': 'var', 'name': name, 'value': expr}

    def _is_assignment_ahead(self) -> bool:
        """Смотрит вперёд: ID (('.' ID) | ('[' expr ']'))* '=' (но не '==')"""
        p = self.pos
        if self.tokens[p][0] != 'ID':
            return False
        p += 1
        while p < len(self.tokens):
            if self.tokens[p][0] == 'OP' and self.tokens[p][1] == '.':
                p += 1
                if p >= len(self.tokens) or self.tokens[p][0] != 'ID':
                    return False
                p += 1
            elif self.tokens[p][0] == 'OP' and self.tokens[p][1] == '[':
                depth = 1
                p += 1
                while p < len(self.tokens) and depth > 0:
                    if self.tokens[p][0] == 'OP' and self.tokens[p][1] == '[':
                        depth += 1
                    elif self.tokens[p][0] == 'OP' and self.tokens[p][1] == ']':
                        depth -= 1
                    p += 1
            else:
                break
        return (p < len(self.tokens)
                and self.tokens[p][0] == 'OP'
                and self.tokens[p][1] in ('=', '+=', '-=', '/=', '*='))

    def parse_change(self) -> Dict:
        """x = 10  |  a.b = 10  |  a[0] = 10  |  a[0].b = 10 ..."""
        pos, name = self.peek()[2], self.match('ID')[1]
        target = {'type': 'variable', 'name': name}

        while self.peek()[0] == 'OP' and self.peek()[1] in ('.', '['):
            op = self.next()[1]
            if op == '.':
                field = self.match('ID')[1]
                target = {'type': 'dot', 'left': target, 'field': field}
            else:  # '['
                index_expr = self.parse_expression()
                self.match_op(']')
                target = {'type': 'index', 'left': target, 'index': index_expr}

        op = self.match('OP')[1]  # '=', '+=' etc
        expr = self.parse_expression()
        return {'type': 'c_var', 'target': target, "op": op, 'value': expr}

    def parse_expression(self) -> Dict:
        left = self.parse_condition()
        while self.peek()[0] == 'OP' and self.peek()[1] == '>>':
            self.next()  # съедаем '>>'
            right = self.parse_condition()
            left = {'type': 'pipe', 'left': left, 'right': right}
        return left

    def parse_condition(self) -> Dict:
        left = self.parse_equality()
        while self.peek()[0] == 'OP' and self.peek()[1] in ('|', '&'):
            op = self.next()[1]
            right = self.parse_equality()
            left = {'type': 'logic', 'op': op, 'left': left, 'right': right}
        return left

    def parse_equality(self) -> Dict:
        left = self.parse_comparison()
        while self.peek()[0] == 'OP' and self.peek()[1] in ('==', '!='):
            op = self.next()[1]
            right = self.parse_comparison()
            left = {'type': 'binop', 'op': op, 'left': left, 'right': right}
        return left

    def parse_comparison(self) -> Dict:
        left = self.parse_term()
        while self.peek()[0] == 'OP' and self.peek()[1] in ('>', '<', '>=', '<='):
            op = self.next()[1]
            right = self.parse_term()
            left = {'type': 'binop', 'op': op, 'left': left, 'right': right}
        return left

    def parse_term(self) -> Dict:
        left = self.parse_factor()
        while self.peek()[0] == 'OP' and self.peek()[1] in ('+', '-', '..'):
            op = self.next()[1]
            right = self.parse_factor()
            left = {'type': 'binop', 'op': op, 'left': left, 'right': right}
        return left

    def parse_factor(self) -> Dict:
        left = self.parse_unary()
        while self.peek()[0] == 'OP' and self.peek()[1] in ('*', '/', '//', '%', '^'):
            op = self.next()[1]
            right = self.parse_unary()
            left = {'type': 'binop', 'op': op, 'left': left, 'right': right}
        return left

    def parse_unary(self) -> Dict:
        if self.peek()[0] == 'OP' and self.peek()[1] in ('+', '-', '#', '!'):
            op = self.next()[1]
            operand = self.parse_unary()
            return {'type': 'unary', 'op': op, 'operand': operand}
        return self.parse_func()

    def parse_func(self) -> Dict:
        left = self.parse_primary()
        while self.peek()[0] == 'OP' and self.peek()[1] in ('(', '.', '[', '::'):
            op = self.next()[1]
            if op == '(':
                args = []
                while self.peek()[0] != 'OP' or self.peek()[1] != ')':
                    if self.peek()[0] == 'EOF':
                        raise LimeError("Ожидалась ')'", line=self.line())
                    args.append(self.parse_expression())
                    if self.peek()[0] == "OP" and self.peek()[1] == ',':
                        self.next()
                self.match_op(')')
                left = {'type': 'func', 'left': left, 'args': args}
            elif op == '.':
                if self.peek()[0] != 'ID':
                    raise LimeError(f"Ожидался идентификатор после '.', получен {self.peek()[0]}", line=self.line())
                field_name = self.next()[1]
                left = {'type': 'dot', 'left': left, 'field': field_name}
            elif op == "::":
                func = self.match("ID")[1]
                if self.peek()[0] != "OP" or self.peek()[1] != "(":
                    raise LimeError("Need '(' token but given " + self.peek()[1], line=self.line())
                self.next()
                args = []
                while self.peek()[1] != ")":
                    args.append(self.parse_expression())
                    if self.peek()[1] == ",":
                        self.next()
                self.match_op(')')
                left = {'type': 'eval_met', 'cls': left, "func": func, 'args': args}
            elif op == '[':
                index_expr = self.parse_expression()
                self.match_op(']')
                left = {'type': 'index', 'left': left, 'index': index_expr}
        return left

    def parse_primary(self) -> Dict:
        tok = self.peek()

        if tok[0] == 'NUM':
            self.next()
            value = tok[1]
            if value.startswith('0x'):
                return {'type': 'number', 'value': int(value, 16)}
            if '.' in value:
                return {'type': 'number', 'value': float(value)}
            else:
                return {'type': 'number', 'value': int(value)}

        elif tok[0] == 'KEY' and tok[1] == 'fn':
            self.next()  # Съедаем 'fn'

            self.match_op('(')
            args = []
            while self.peek()[1] != ")":
                args.append(self.match("ID")[1])
                if self.peek()[1] == ",":
                    self.next()
            self.match_op(')')

            if self.peek()[0] == 'OP' and self.peek()[1] == '=':
                self.next()  # Съедаем '='
                body = self.parse_expression()
                return {'type': 'lambda', 'params': args, 'body': body, 'is_expr': True}

            elif self.peek()[0] == 'OP' and self.peek()[1] == '{':
                body = self.parse_block()
                return {'type': 'lambda', 'params': args, 'body': body, 'is_expr': False}
            else:
                raise LimeError("Expected '=' or '{' after lambda arguments", line=self.line())

        elif tok[0] == 'STR':
            self.next()
            return {'type': 'string', 'value': tok[1]}

        elif tok[0] == 'ID':
            self.next()
            return {'type': 'variable', 'name': tok[1]}

        elif tok[0] == 'OP' and tok[1] == '(':
            return self.parse_parentheses_or_tuple()

        elif tok[0] == 'OP' and tok[1] == '[':
            return self.parse_array_literal()

        elif tok[0] == 'OP' and tok[1] == '{':
            return self.parse_dict_literal()

        else:
            raise LimeError(f"Expected token: {tok[0]} '{tok[1]}'", line=tok[2])

    def parse_parentheses_or_tuple(self):
        self.match_op('(')

        # Пустой кортеж ()
        if self.peek()[1] == ')':
            self.next()
            return {'type': 'tuple', 'items': []}

        first_expr = self.parse_expression()

        # Если за первым выражением идет запятая — это КОРТЕЖ!
        if self.peek()[0] == 'OP' and self.peek()[1] == ',':
            items = [first_expr]
            while self.peek()[1] == ',':
                self.next()  # Съедаем ','
                if self.peek()[1] == ')':
                    break  # Поддержка trailing comma: (1, 2,)
                items.append(self.parse_expression())

            self.match_op(')')
            return {'type': 'tuple', 'items': items}

        self.match_op(')')
        return first_expr

    def parse_array_literal(self) -> Dict:
        self.match_op('[')
        items = []
        while not (self.peek()[0] == 'OP' and self.peek()[1] == ']'):
            if self.peek()[0] == 'EOF':
                raise LimeError("Ожидалась ']'", line=self.line())
            items.append(self.parse_expression())
            if self.peek()[0] == 'OP' and self.peek()[1] == ',':
                self.next()
        self.match_op(']')
        return {'type': 'array', 'items': items}

    def parse_dict_literal(self) -> Dict:
        self.match_op('{')
        pairs = []
        while not (self.peek()[0] == 'OP' and self.peek()[1] == '}'):
            if self.peek()[0] == 'EOF':
                raise LimeError("Ожидалась '}'", line=self.line())
            if self.peek()[0] == 'STR' or self.peek()[0] == 'ID':
                key = {'type': 'string', 'value': self.next()[1]}
            else:
                self.match_op('(')
                key = self.parse_expression()
                self.match_op(')')
            self.match_op(':')
            value = self.parse_expression()
            pairs.append((key, value))
            if self.peek()[0] == 'OP' and self.peek()[1] == ',':
                self.next()
        self.match_op('}')
        return {'type': 'dict', 'pairs': pairs}

    def pretty_print(self, ast: List[Dict], indent: int = 0) -> str:
        result = []
        for node in ast:
            result.append(self._node_to_str(node, indent))
        return '\n'.join(result)

    def _node_to_str(self, node: Dict, indent: int = 0) -> str:
        if node['type'] == 'var':
            return f'  ' * indent + f'var {node["name"]} = {self._node_to_str(node["value"], 0)}'

        elif node['type'] == 'binop':
            left = self._node_to_str(node['left'], 0)
            right = self._node_to_str(node['right'], 0)
            return f'({left} {node["op"]} {right})'

        elif node['type'] == 'unary':
            return f'({node["op"]}{self._node_to_str(node["operand"], 0)})'

        elif node['type'] == 'number':
            return str(node['value'])

        elif node['type'] == 'string':
            return f'"{node["value"]}"'

        elif node['type'] == 'variable':
            return node['name']

        else:
            return str(node)


class CodeGen:
    def __init__(self, ast: list[dict], path: str, visited_files: set = None):
        self.ast: list[dict] = ast
        self.gen = ""
        self.path = path
        self.line_map: list[tuple[int, int]] = []
        self.stop_stack = []
        self.loop_counter = 0
        self.visited_files = visited_files if visited_files is not None else set()

    def generate(self):
        for i in self.ast:
            self.genSt(i)
        return self.gen

    def _record_line(self, v):
        lime_line = v.get("line") if isinstance(v, dict) else None
        if lime_line is not None:
            lua_line = self.gen.count("\n") + 1
            self.line_map.append((lua_line, lime_line))

    def genSt(self, v):
        self._record_line(v)
        if v["type"] == "var":
            self.genVar(v)
        elif v["type"] == "c_var":
            self.gencVar(v)
        elif v["type"] == "block":
            for i in v["statements"]:
                self.genSt(i)
            self.gen += "\n"
            return
        elif v["type"] == "if":
            self.genIf(v)
        elif v["type"] == "fs":
            self.genFunction(v)
        elif v["type"] == "for":
            self.genFor(v)
        elif v["type"] == "for_in":
            self.genForIn(v)
        elif v["type"] == "loop":
            self.genLoop(v)
        elif v["type"] == "load":
            self.genLoad(v)
        elif v["type"] == "use":
            self.genUse(v)
        elif v["type"] == "ret":
            self.genRet(v)
        elif v["type"] == "struct":
            self.genStruct(v)
        elif v["type"] == "method":
            self.genMethod(v)
        elif v["type"] == "usec":
            self.genUseC(v)
        elif v["type"] == "match":
            self.genMatch(v)
        elif v["type"] == "next":
            self.genNext(v)
        elif v["type"] == "stop":
            self.genStop(v)
        elif v["type"] == "end":
            return
        else:
            self.genExpr(v)
        self.gen += '\n'

    def genMatch(self, v):
        fst = True
        for i in v["cases"]:
            if fst:
                fst = False
                self.gen += "if "
                self.genExpr(v['expr'])
                self.gen += " == "
                self.genExpr(i['expr'])
                self.gen += " then\n"
            elif i["expr"]["type"] == "variable" and i["expr"]["name"] == "_":
                self.gen += "else\n"
            else:
                self.gen += "elif "
                self.genExpr(v['expr'])
                self.gen += " == "
                self.genExpr(i['expr'])
                self.gen += " then\n"
            self.genSt(i["stmt"])

        self.gen += "end"

    def genVar(self, v):
        self.gen += "local " + v["name"] + " = "
        self.genExpr(v['value'])

    def genRet(self, v):
        self.gen += "return "
        self.genExpr(v['expr'])

    def genNext(self, v):
        if not self.stop_stack:
            raise LimeError("'next' cannot be used outside of a loop", line=v.get("line"))
        self.gen += f"goto next_{self.stop_stack[-1]}"

    def genStop(self, v):
        if not self.stop_stack:
            raise LimeError("'stop' cannot be used outside of a loop", line=v.get("line"))
        self.gen += "break"  # Родной break гораздо быстрее goto out

    def genLoop(self, v):
        self.loop_counter += 1
        current_loop = self.loop_counter
        self.stop_stack.append(current_loop)

        self.gen += "while "
        self.genExpr(v['expr'])
        self.gen += " do\n"

        self.genSt(v["stmt"])

        self.gen += f"\n::next_{current_loop}::\n"
        self.gen += "end"

        self.stop_stack.pop()

    def genFor(self, v):
        self.loop_counter += 1
        current_loop = self.loop_counter
        self.stop_stack.append(current_loop)

        self.gen += "for "
        if v["start"]['type'] != "c_var":
            raise LimeError('In "for" cycle must be var assignment (without "var")', line=v.get("line"))
        self.genSt(v['start'])
        self.gen += ", "
        self.genExpr(v["expr"])
        self.gen += ", "
        self.genExpr(v["step"])
        self.gen += " do\n"

        self.genSt(v["stmt"])

        self.gen += f"\n::next_{current_loop}::\n"
        self.gen += "end"

        self.stop_stack.pop()

    def genForIn(self, v):
        self.loop_counter += 1
        current_loop = self.loop_counter
        self.stop_stack.append(current_loop)

        names = ', '.join(v['names'])
        self.gen += f"for {names} in pairs("
        self.genExpr(v['expr'])
        self.gen += ") do\n"

        self.genSt(v["stmt"])

        self.gen += f"\n::next_{current_loop}::\n"
        self.gen += "end"

        self.stop_stack.pop()

    def genLoad(self, v):
        file_name = v["expr"]['value']
        if not file_name.endswith(".lm"):
            file_name += ".lm"

        full_path = os.path.normpath(os.path.join(self.path, file_name))

        if not os.path.exists(full_path):
            raise LimeError("Cannot find file: " + full_path, line=v.get("line"))

        if full_path in self.visited_files:
            return

        self.visited_files.add(full_path)

        with open(full_path, encoding="utf-8", mode="r") as f:
            code = f.read()

        offset = self.gen.count("\n")

        inner = CodeGen(Parser(lex(code)).parse(), os.path.dirname(full_path), self.visited_files)
        self.gen += inner.generate()
        self.line_map.extend((lua_line + offset, lime_line) for lua_line, lime_line in inner.line_map)

    def boxTypeToC(self, s):
        """
        Возвращает tuple: (ctype, default_val, kind, elem_type)
        kind: 'prim' (примитивы), 'str' (строки), 'arr' (массивы и указатели)
        """
        s = s.strip()
        if s in ("f", "float"):
            return "float", "0", "prim", "float"
        elif s in ("d", "double"):
            return "double", "0", "prim", "double"
        elif s in ("i", "int"):
            return "int", "0", "prim", "int"
        elif s in ("b", "bool"):
            return "bool", "false", "prim", "bool"
        elif s in ("s", "string"):
            return "const char*", '""', "str", "const char*"
        elif s in ("p", "ptr", "void*"):
            return "void*", "ffi.NULL", "arr", "void*"
        elif s in ("ai", "i*", "int*"):
            return "int*", "ffi.NULL", "arr", "int"
        elif s in ("af", "f*", "float*"):
            return "float*", "ffi.NULL", "arr", "float"
        elif s in ("ad", "d*", "double*"):
            return "double*", "ffi.NULL", "arr", "double"
        elif s in ("as", "s*", "string*"):
            return "const char**", "ffi.NULL", "arr", "const char*"
        else:
            if s.endswith("*"):
                elem = s[:-1].strip()
                return s, "ffi.NULL", "arr", elem
            raise LimeError("Unknown Type: " + s)

    def genStruct(self, v):
        struct_name = v["name"]
        fields = v["fields"]

        field_infos = []
        for f in fields:
            fname = f["name"]
            ftype = f["type"]
            ctype, default_val, kind, elem_type = self.boxTypeToC(ftype)
            is_managed = (kind != "prim")

            cname = f"_{fname}" if is_managed else fname
            field_infos.append({
                "name": fname,
                "cname": cname,
                "type": ftype,
                "ctype": ctype,
                "default": default_val,
                "kind": kind,
                "elem_type": elem_type,
                "is_managed": is_managed
            })

        self.gen += f"ffi.cdef([[\ntypedef struct {{\n"
        for fi in field_infos:
            self.gen += f"    {fi['ctype']} {fi['cname']};\n"
        self.gen += f"}} {struct_name};\n]])\n\n"

        self.gen += f"local {struct_name}_refs = setmetatable({{}}, {{__mode = 'k'}})\n"
        self.gen += f"local {struct_name}_methods = {{}}\n\n"

        self.gen += f"local function {struct_name}_get(self, k)\n"
        self.gen += f"    local m = {struct_name}_methods[k]\n"
        self.gen += f"    if m then return m end\n"

        managed_fields = [fi for fi in field_infos if fi["is_managed"]]
        if managed_fields:
            for fi in managed_fields:
                fname = fi["name"]
                cname = fi["cname"]
                kind = fi["kind"]

                self.gen += f"    if k == '{fname}' then\n"
                if kind == "str":
                    self.gen += f"        if self.{cname} == ffi.NULL then return \"\" end\n"
                    self.gen += f"        return ffi.string(self.{cname})\n"
                elif kind == "arr":
                    self.gen += f"        local ref = {struct_name}_refs[self] and {struct_name}_refs[self].{fname}\n"
                    self.gen += f"        if ref then return ref.orig end\n"
                    self.gen += f"        if self.{cname} == ffi.NULL then return nil end\n"
                    self.gen += f"        return self.{cname}\n"
                self.gen += f"    end\n"

        self.gen += f"    local ref = {struct_name}_refs[self]\n"
        self.gen += f"    if ref then return ref[k] end\n"
        self.gen += f"    return nil\n"
        self.gen += f"end\n\n"

        self.gen += f"local function {struct_name}_set(self, k, v)\n"
        if managed_fields:
            for fi in managed_fields:
                fname = fi["name"]
                cname = fi["cname"]
                kind = fi["kind"]
                elem_type = fi["elem_type"]

                self.gen += f"    if k == '{fname}' then\n"
                self.gen += f"        if not {struct_name}_refs[self] then {struct_name}_refs[self] = {{}} end\n"
                if kind == "str":
                    self.gen += f"        local str_val = tostring(v or \"\")\n"
                    self.gen += f"        {struct_name}_refs[self].{fname} = str_val\n"
                    self.gen += f"        self.{cname} = str_val\n"
                elif kind == "arr":
                    self.gen += f"        if type(v) == \"table\" then\n"
                    self.gen += f"            local c_arr = to_c_array(v, \"{elem_type}\")\n"
                    self.gen += f"            {struct_name}_refs[self].{fname} = {{ cdata = c_arr, orig = v }}\n"
                    self.gen += f"            self.{cname} = c_arr\n"
                    self.gen += f"        else\n"
                    self.gen += f"            {struct_name}_refs[self].{fname} = {{ cdata = v, orig = v }}\n"
                    self.gen += f"            self.{cname} = v\n"
                    self.gen += f"        end\n"
                self.gen += f"        return\n"
                self.gen += f"    end\n"

        self.gen += f"    if not {struct_name}_refs[self] then {struct_name}_refs[self] = {{}} end\n"
        self.gen += f"    {struct_name}_refs[self][k] = v\n"
        self.gen += f"end\n\n"

        self.gen += f"local _raw_{struct_name} = ffi.metatype(\"{struct_name}\", {{\n"
        self.gen += f"    __index = {struct_name}_get,\n"
        self.gen += f"    __newindex = {struct_name}_set\n"
        self.gen += f"}})\n\n"

        field_names_list = ", ".join(f"'{fi['name']}'" for fi in field_infos)
        self.gen += f"local function {struct_name}(...)\n"
        self.gen += f"    local obj = _raw_{struct_name}()\n"
        self.gen += f"    local args = {{...}}\n"
        self.gen += f"    if #args == 1 and type(args[1]) == \"table\" and not ffi.istype(\"{struct_name}\", args[1]) then\n"
        self.gen += f"        for k, v in pairs(args[1]) do obj[k] = v end\n"
        self.gen += f"    else\n"
        self.gen += f"        local fnames = {{{field_names_list}}}\n"
        self.gen += f"        for i, val in ipairs(args) do\n"
        self.gen += f"            if fnames[i] then obj[fnames[i]] = val end\n"
        self.gen += f"        end\n"
        self.gen += f"    end\n"
        self.gen += f"    return obj\n"
        self.gen += f"end"

    def genUse(self, v):
        path = os.path.join(self.path, "libs\\" + v["expr"]['value'] + "\\setup.lm")
        if not os.path.exists(path):
            path = os.path.join(get_libs_path(), v["expr"]['value'] + "\\setup.lm")
            if not os.path.exists(path):
                raise LimeError("Cannot find file: " + path, line=v.get("line"))
        with open(path, encoding="utf-8", mode="r") as f:
            code = f.read()
        offset = self.gen.count("\n")
        inner = CodeGen(Parser(lex(code)).parse(), os.path.dirname(path))
        self.gen += inner.generate()
        self.line_map.extend((lua_line + offset, lime_line) for lua_line, lime_line in inner.line_map)

    def normalize_path(self, path: str) -> str:
        path = os.path.normpath(path)
        path = path.replace('\\', '/')  # для Lua
        return path

    def get_library_extension(self) -> str:
        """Возвращает расширение библиотеки для текущей платформы"""
        if platform.system() == "Windows":
            return ".dll"
        elif platform.system() == "Linux":
            return ".so"
        elif platform.system() == "Darwin":  # macOS
            return ".dylib"
        return ".dll"  # fallback

    def find_library_file(self, name: str, search_paths: list) -> str | None:
        """Ищет библиотеку в указанных путях"""
        ext = self.get_library_extension()

        if not name.endswith(ext):
            candidates = [name + ext, name]
        else:
            candidates = [name]

        for path in search_paths:
            for candidate in candidates:
                full_path = os.path.join(path, candidate)
                if os.path.exists(full_path):
                    return full_path

        return None

    def genUseC(self, v):

        dll_name = v["expr"]['value']
        if not dll_name.endswith(('.dll', '.so', '.dylib')):
            dll_name += self.get_library_extension()

        search_paths = [
            os.path.join(self.path, "libs"),  # локальная папка проекта
            os.getcwd(),  # текущая папка
            os.path.join(get_libs_path()),  # глобальная LIME_PATH
            "C:\\\\Windows\\System32"
        ]

        if platform.system() == "Windows":
            search_paths.extend(os.environ.get("PATH", "").split(";"))
        else:
            search_paths.extend(os.environ.get("LD_LIBRARY_PATH", "").split(":"))
            search_paths.extend(["/usr/lib", "/usr/local/lib"])

        lib_path = self.find_library_file(dll_name, search_paths)

        if not lib_path:
            raise LimeError(f"Cannot find library: {dll_name} in {search_paths}", line=v.get("line"))

        lib_path = self.normalize_path(lib_path)

        var_name = os.path.splitext(os.path.basename(dll_name))[0]
        if v["rules"]["as"] and v["rules"]["as"] != '':
            var_name = v["rules"]["as"]["value"]

        if v["rules"]["rule"] and v["rules"]["rule"] != '':
            if v["rules"]["rule"]["type"] != "string":
                raise LimeError("Cannot work with non-string type in dll import", line=v.get("line"))

            self.gen += f"ffi.cdef([[\n{v["rules"]["rule"]["value"]}]])\n"

        self.gen += f"local {var_name} = ffi.load('{lib_path}')"

    def gencVar(self, v):
        self.genTarget(v['target'])
        match v['op']:
            case '=':
                self.gen += " = "
            case _:
                self.gen += " = ("
                self.genTarget(v['target'])
                self.gen += f") {v['op'][0]} "

        self.genExpr(v['value'])

    def genTarget(self, t):
        if t['type'] == 'variable':
            self.gen += t['name']
        elif t['type'] == 'dot':
            self.genTarget(t['left'])
            self.gen += "." + t['field']
        elif t['type'] == 'index':
            self.genTarget(t['left'])
            self.gen += "["
            self.genExpr(t['index'])
            self.gen += "]"

    def genFunction(self, v):
        self.gen += f"local function {v["name"]}("
        j = 0
        for i in v["params"]:
            self.gen += i
            if j < len(v["params"]) - 1:
                self.gen += ", "
            j += 1
        self.gen += ")\n"
        self.genSt(v["stmt"])
        self.gen += "end"

    def genMethod(self, v):
        self.gen += f"function {v["cls"]}_methods:{v["func"]}("
        j = 0
        for i in v["params"]:
            self.gen += i
            if j < len(v["params"]) - 1:
                self.gen += ", "
            j += 1
        self.gen += ")\n"
        self.genSt(v["stmt"])
        self.gen += "end"

    def genIf(self, v):
        self.gen += "if "
        self.genExpr(v['expr'])
        self.gen += " then\n"
        self.genSt(v["stmt"])
        for i in v["elifs"]:
            self.gen += "elseif "
            self.genExpr(i["expr"])
            self.gen += " then\n"
            self.genSt(i["stmt"])
        if v['else']['stmt'] != {}:
            self.gen += "else\n"
            self.genSt(v["else"]["stmt"])
        self.gen += "end"

    def genLambda(self, v):
        params_str = ", ".join(v['params'])
        self.gen += f"function({params_str})\n"
        if v['is_expr']:
            self.gen += "return "
            self.genExpr(v['body'])
            self.gen += "\n"
        else:
            self.genSt(v['body'])
        self.gen += "end"

    def genPipe(self, v):
        """
        Реализация пайпа: `left >> right`.

        - `a >> f`        -> f(a)
        - `a >> f(2)`     -> f(a, 2)          (a подставляется ПЕРВЫМ аргументом
                                                внутрь уже существующего вызова,
                                                а не вызывает результат f(2))
        - `a >> o::m(2)`  -> o:m(a, 2)        (то же самое для методов)
        - `(a, b) >> f(2)`-> f(a, b, 2)       (кортеж слева разворачивается в
                                                несколько аргументов)

        Благодаря левоассоциативному парсингу `a >> f(2) >> g(3)` строится как
        pipe(pipe(a, f(2)), g(3)), поэтому цепочки просто рекурсивно
        генерируются через genExpr/genPipe и дают g(f(a, 2), 3).
        """
        left = v['left']
        right = v['right']

        if left['type'] == 'tuple':
            left_args = left['items']
        else:
            left_args = [left]

        def gen_args(args):
            for i, arg in enumerate(args):
                self.genExpr(arg)
                if i < len(args) - 1:
                    self.gen += ", "

        if right['type'] == 'func':
            # right — это вызов вида callee(args...): вставляем left_args
            # перед уже переданными аргументами вызова.
            self.genExpr(right['left'])
            self.gen += "("
            gen_args(left_args + right['args'])
            self.gen += ")"
        elif right['type'] == 'eval_met':
            # right — это вызов метода вида cls::func(args...)
            self.genExpr(right['cls'])
            self.gen += ":" + right['func'] + "("
            gen_args(left_args + right['args'])
            self.gen += ")"
        else:
            # right — просто вызываемое значение (переменная, dot-цепочка,
            # лямбда и т.п.), вызываем его с left в качестве аргумента(ов).
            self.genExpr(right)
            self.gen += "("
            gen_args(left_args)
            self.gen += ")"

    def genExpr(self, v):
        if v["type"] == "binop":
            self.gen += "("
            self.genExpr(v["left"])
            self.gen += f"{v['op'] if v["op"] != "!=" else "~="}"
            self.genExpr(v["right"])
            self.gen += ")"
        if v["type"] == "logic":
            self.gen += "("
            self.genExpr(v["left"])
            self.gen += f"{" and " if v['op'] == "&" else " or "}"
            self.genExpr(v["right"])
            self.gen += ")"
        elif v["type"] == "number":
            self.gen += str(v["value"])
        elif v["type"] == "unary":
            self.gen += v["op"] if v["op"] != "!" else " not "
            self.genExpr(v["operand"])
        elif v["type"] == "eval_met":
            self.genExpr(v["cls"])
            self.gen += ":" + v["func"]
            self.gen += "("
            j = 0
            for i in v['args']:
                self.genExpr(i)
                if len(v["args"]) - 1 > j:
                    self.gen += ", "
                j += 1
            self.gen += ')'
        elif v["type"] == "string":
            self.gen += f'("{v["value"]}")'
        elif v["type"] == "variable":
            self.gen += v["name"]
        elif v["type"] == "func":
            self.genExpr(v['left'])
            self.gen += "("
            j = 0
            for i in v['args']:
                self.genExpr(i)
                if len(v["args"]) - 1 > j:
                    self.gen += ", "
                j += 1
            self.gen += ')'
        elif v["type"] == "dot":
            self.genExpr(v['left'])
            self.gen += "." + v["field"]
        elif v["type"] == "index":
            self.genExpr(v['left'])
            self.gen += "["
            self.genExpr(v['index'])
            self.gen += "]"
        elif v["type"] == "array":
            self.gen += "_arr({"
            j = 0
            for item in v["items"]:
                self.genExpr(item)
                if len(v["items"]) - 1 > j:
                    self.gen += ", "
                j += 1
            self.gen += "})"
        elif v["type"] == "dict":
            self.gen += "_arr({"
            j = 0
            for key, value in v["pairs"]:
                self.gen += "["
                self.genExpr(key)
                self.gen += "] = "
                self.genExpr(value)
                if len(v["pairs"]) - 1 > j:
                    self.gen += ", "
                j += 1
            self.gen += "})"
        elif v["type"] == "lambda":
            self.genLambda(v)
        elif v["type"] == "pipe":
            self.genPipe(v)