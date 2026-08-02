import os.path
import re
import sys
import time

import lupa
import lupa.luajit21
from lupa.luajit21 import LuaRuntime
import importlib

from compiler import Parser, lex, CodeGen, LimeError, format_lime_error, resolve_lua_line
from config import *

if len(sys.argv) > 0:
    sys.argv.pop(0)


if len(sys.argv) < 1:
    print("Must be given 1 or more arguments to app")
    sys.exit(1)


def printlmerror(s):
    print(format_lime_error(str(s)))
    exit(1)


lua = LuaRuntime(unpack_returned_tuples=True)

lua.execute('jit.opt.start(3)')

lua.globals()["args"] = lua.table_from(sys.argv)
lua.globals()["defpyt"] = importlib.import_module
lua.globals()["exit"] = sys.exit
lua.globals()["getattr"] = getattr
lua.globals()["py"] = exec
lua.globals()["pystr"] = str
lua.globals()["pylist"] = lambda a: [i for i in a]
lua.globals()["tab"] = lambda a: lua.table_from(a)

path = os.path.normpath(os.path.abspath(sys.argv[0]))
options = sys.argv[1:]
PRELUDE_LINES = setting.count("\n")
timer = True

a = False

if "--version" in sys.argv:
    print("LimeLang Beta 1.0")
    a = True
if "--help" in sys.argv:
    print(help)
    a = True
if "--notime" in sys.argv:
    options.pop(options.index("--notime"))
    timer = False

if path == "jit":
    path = os.path.normpath(os.path.abspath(sys.argv[1]))
    if not os.path.exists(path):
        print("Unknown path to lua file for jit: " + sys.argv[0])
        sys.exit(1)
    with open(path, encoding="utf-8", mode="r") as f:
        code = f.read()
    a = time.time()
    try:
        lua.execute(setting + code)
    except lupa.luajit21.LuaSyntaxError as e:
        msg = str(e)
        m = re.search(r']:(\d+):\s*(.*)', msg, re.S) or re.search(r':(\d+):\s*(.*)$', msg, re.S)
        lua_line = None
        err_text = msg
        if m:
            lua_line = int(m.group(1)) - PRELUDE_LINES
            err_text = m.group(2).strip()
        print(format_lime_error(err_text, line=lua_line, code=code, path=path))
        sys.exit(1)
    except lupa.luajit21.LuaError as e:
        msg = str(e)
        m = re.search(r']:(\d+):\s*(.*)', msg, re.S) or re.search(r':(\d+):\s*(.*)$', msg, re.S)
        lua_line = None
        err_text = msg.split("stack")[0]
        hint = None
        if m:
            lua_line = int(m.group(1)) - PRELUDE_LINES
            err_text = m.group(2).strip().split("stack")[0]
            if "attempt to perform arithmetic on global" in msg:
                name = msg.split("'")[1]
                err_text = f"variable '{name}' is not defined"
                hint = f"do you want to write 'local' before {name}?"
        print(format_lime_error(err_text, line=lua_line, code=code, path=path, hint=hint))
        sys.exit(1)
    sys.exit(0)


if not os.path.exists(path):
    if a: sys.exit(0)
    print("Unknown path to project or file: " + sys.argv[0])
    sys.exit(1)

main_lm_file = "main.lm"

if os.path.isfile(path):
    p = path.split("\\")
    path = p[:-1]
    main_lm_file = p[-1]
    path = os.path.normpath("/".join(path))

if os.path.isdir(path):
    if "--build-exe" in options:
        with open(os.path.join(path, "output.lua"), encoding="utf-8", mode="r") as f:
            code = setting + f.read()
        print("not realized now...")
        sys.exit(-1)

    if "--lua" in options:
        with open(os.path.join(path, "output.lua"), encoding="utf-8", mode="r") as f:
            code = f.read()
        if timer:
            a = time.time()
        try:
            lua.execute(setting + code)
        except lupa.luajit21.LuaSyntaxError as e:
            msg = str(e)
            m = re.search(r']:(\d+):\s*(.*)', msg, re.S) or re.search(r':(\d+):\s*(.*)$', msg, re.S)
            lua_line = None
            err_text = msg
            if m:
                lua_line = int(m.group(1)) - PRELUDE_LINES
                err_text = m.group(2).strip()
            print(format_lime_error(err_text, line=lua_line, code=code, path=path))
            sys.exit(1)
        except lupa.luajit21.LuaError as e:
            msg = str(e)
            m = re.search(r']:(\d+):\s*(.*)', msg, re.S) or re.search(r':(\d+):\s*(.*)$', msg, re.S)
            lua_line = None
            err_text = msg.split("stack")[0]
            if m:
                lua_line = int(m.group(1)) - PRELUDE_LINES
                err_text = m.group(2).strip().split("stack")[0]
                if "attempt to perform arithmetic on global" in msg:
                    name = msg.split("'")[1]
                    err_text = f"variable '{name}' is not defined"
            print(format_lime_error(err_text, line=lua_line, code=code, path=path))
            sys.exit(1)
        if timer:
            b = time.time()
            print(f"\nExecuted in {(b - a) * 1000 // 1} ms")

    else:
        with open(os.path.join(path, main_lm_file), encoding="utf-8", mode="r") as f:
            code = f.read()

        try:
            tokens = lex(code)
            parser = Parser(tokens)
            ast = parser.parse()
            main_file_path = os.path.normpath(os.path.join(path, main_lm_file))
            codegen = CodeGen(ast, path, visited_files={main_file_path})
            lua_code = codegen.generate()
        except LimeError as e:
            print(format_lime_error(e.message, line=e.line, code=code, path=path, hint=e.hint))
            sys.exit(1)

        with open(os.path.join(path, "output.lua"), encoding="utf8", mode="w") as f:
            f.write("-- WARNING: It is LimeLang executing code, so it can be with uncorrected work without lime.exe "
                    "executing\n-- You can run it without parsing with \"lime [PATH] --lua\"\n" + lua_code)

        if timer:
            a = time.time()
        try:
            lua.execute(setting + lua_code)
        except lupa.luajit21.LuaSyntaxError as e:
            msg = str(e)
            m = re.search(r']:(\d+):\s*(.*)', msg, re.S) or re.search(r':(\d+):\s*(.*)$', msg, re.S)
            lime_line = None
            err_text = msg
            if m:
                lua_line = int(m.group(1)) - PRELUDE_LINES
                err_text = m.group(2).strip()
                if "'end' expected (to close 'while'" in msg and " near '::'" in msg:
                    err_text = f"'stop' can't be in main loop's block"
                elif "'end' expected (to close 'while'" in msg:
                    err_text = f"unreachable code after 'stop'"
                lime_line = resolve_lua_line(codegen.line_map, lua_line)
            print(format_lime_error(err_text, line=lime_line, code=code, path=path))
            sys.exit(1)
        except lupa.luajit21.LuaError as e:
            msg = str(e)
            m = re.search(r']:(\d+):\s*(.*)', msg, re.S) or re.search(r':(\d+):\s*(.*)$', msg, re.S)
            lime_line = None
            err_text = msg.split("stack")[0]
            hint = None
            if m:
                lua_line = int(m.group(1)) - PRELUDE_LINES
                err_text = m.group(2).strip().split("stack")[0]
                if "attempt to perform arithmetic on global" in msg:
                    name = msg.split("'")[1]
                    err_text = f"variable '{name}' is not defined"
                    hint = f"do you want to write 'var' before {name}?"
                elif "'end' expected (to close 'while'" in msg:
                    err_text = f"unreachable code after 'stop'"
                lime_line = resolve_lua_line(codegen.line_map, lua_line)
            print(format_lime_error(err_text, line=lime_line, code=code, path=path, hint=hint))
            sys.exit(1)
        if timer:
            b = time.time()
            print(f"\nExecuted in {(b - a) * 1000 // 1} ms")