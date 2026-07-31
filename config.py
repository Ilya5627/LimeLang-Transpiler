setting = """
local ffi = require('ffi')

cstr = ffi.string

function pairs(t)
    local current_key = nil

    local is_array = type(t) == "table" and (rawget(t, 1) ~= nil)

    return function()
        local key, value = next(t, current_key)
        current_key = key
        if key ~= nil then
            if is_array then
                return value, key
            else
                return key, value
            end
        end
        return nil
    end
end

-- ===== Reactive core: ref / live (computed) / watch =====
-- ref(x)      -- settable reactive value:   r.value = 10
-- live(fn)    -- read-only computed value:  v.value  (cached; only recomputes when a dependency it read last time changes)
-- watch(fn)   -- runs fn immediately, then reruns it automatically whenever any ref/live it read changes; returns fn(), watcher_id
-- unwatch(id) -- stops a watcher created by watch()
-- trigger()   -- manually force-rerun every active watcher (escape hatch for state outside the reactive graph)

local _dep_stack = {}

local function _track_dep(subs)
    local top = _dep_stack[#_dep_stack]
    if top then
        top.deps[subs] = true
        subs[top.notify] = true
    end
end

local function _run_tracked(notify, fn)
    local new_deps = {}
    table.insert(_dep_stack, { notify = notify, deps = new_deps })
    local ok, result = pcall(fn)
    table.remove(_dep_stack)
    return ok, result, new_deps
end

local function _resubscribe(old_deps, new_deps, notify)
    for dep_subs in pairs(old_deps) do
        if not new_deps[dep_subs] then
            dep_subs[notify] = nil
        end
    end
end

local function _notify_all(subs)
    local list = {}
    for n in pairs(subs) do table.insert(list, n) end
    for _, n in ipairs(list) do n() end
end

local ref_state = setmetatable({}, { __mode = "k" })
local live_state = setmetatable({}, { __mode = "k" })

local function _unwrap(x)
    if type(x) == "table" then
        local rs = ref_state[x]
        if rs then
            _track_dep(rs.subs)
            return rs.value
        end
        local ls = live_state[x]
        if ls then
            if ls.dirty then ls.recompute() end
            _track_dep(ls.subs)
            return ls.value
        end
    end
    return x
end

local ref_mt = {
    __index = function(self, key)
        local st = ref_state[self]
        if key == "value" then
            _track_dep(st.subs)
            return st.value
        elseif key == "peek" then
            return function() return st.value end
        end
    end,
    __newindex = function(self, key, v)
        if key ~= "value" then
            error("ref: only '.value' can be assigned, got '" .. tostring(key) .. "'")
        end
        local st = ref_state[self]
        if v ~= st.value then
            st.value = v
            _notify_all(st.subs)
        end
    end,
    __tostring = function(self) return tostring(ref_state[self].value) end,
    __call = function(self) return ref_state[self].value end,
    __eq = function(a, b) return _unwrap(a) == _unwrap(b) end,
    __lt = function(a, b) return _unwrap(a) < _unwrap(b) end,
    __le = function(a, b) return _unwrap(a) <= _unwrap(b) end,
    __add = function(a, b) return _unwrap(a) + _unwrap(b) end,
    __sub = function(a, b) return _unwrap(a) - _unwrap(b) end,
    __mul = function(a, b) return _unwrap(a) * _unwrap(b) end,
    __div = function(a, b) return _unwrap(a) / _unwrap(b) end,
    __mod = function(a, b) return _unwrap(a) % _unwrap(b) end,
    __pow = function(a, b) return _unwrap(a) ^ _unwrap(b) end,
    __unm = function(a) return -_unwrap(a) end,
    __concat = function(a, b) return tostring(_unwrap(a)) .. tostring(_unwrap(b)) end,
}

function ref(initial)
    local self = setmetatable({}, ref_mt)
    ref_state[self] = { value = initial, subs = {} }
    return self
end

local live_mt = {
    __index = function(self, key)
        local st = live_state[self]
        if key == "value" then
            if st.dirty then st.recompute() end
            _track_dep(st.subs)
            return st.value
        elseif key == "peek" then
            return function()
                if st.dirty then st.recompute() end
                return st.value
            end
        elseif key == "refresh" then
            return function()
                st.dirty = true
                _notify_all(st.subs)
            end
        end
    end,
    __newindex = function(self, key)
        error("live: computed values are read-only, can't set '" .. tostring(key) .. "'")
    end,
    __tostring = function(self)
        local st = live_state[self]
        if st.dirty then st.recompute() end
        return tostring(st.value)
    end,
    __call = function(self)
        local st = live_state[self]
        if st.dirty then st.recompute() end
        return st.value
    end,
    __eq = function(a, b) return _unwrap(a) == _unwrap(b) end,
    __lt = function(a, b) return _unwrap(a) < _unwrap(b) end,
    __le = function(a, b) return _unwrap(a) <= _unwrap(b) end,
    __add = function(a, b) return _unwrap(a) + _unwrap(b) end,
    __sub = function(a, b) return _unwrap(a) - _unwrap(b) end,
    __mul = function(a, b) return _unwrap(a) * _unwrap(b) end,
    __div = function(a, b) return _unwrap(a) / _unwrap(b) end,
    __mod = function(a, b) return _unwrap(a) % _unwrap(b) end,
    __pow = function(a, b) return _unwrap(a) ^ _unwrap(b) end,
    __unm = function(a) return -_unwrap(a) end,
    __concat = function(a, b) return tostring(_unwrap(a)) .. tostring(_unwrap(b)) end,
}

function live(fn)
    local self = setmetatable({}, live_mt)
    local st
    local function notify_subs()
        if not st.dirty then
            st.dirty = true
            _notify_all(st.subs)
        end
    end
    local function recompute()
        local ok, result, new_deps = _run_tracked(notify_subs, fn)
        _resubscribe(st.deps, new_deps, notify_subs)
        st.deps = new_deps
        if not ok then
            st.dirty = true
            error(result, 0)
        end
        st.value = result
        st.dirty = false
    end
    st = { value = nil, dirty = true, subs = {}, deps = {}, recompute = recompute }
    live_state[self] = st
    return self
end

local _watchers = {}
local _watcher_id = 0

function watch(fn)
    _watcher_id = _watcher_id + 1
    local id = _watcher_id
    local w = { deps = {} }
    local function run()
        local ok, result, new_deps = _run_tracked(run, fn)
        _resubscribe(w.deps, new_deps, run)
        w.deps = new_deps
        if not ok then error(result, 0) end
        return result
    end
    w.run = run
    _watchers[id] = w
    local first_result = run()
    return first_result, id
end

function unwatch(id)
    local w = _watchers[id]
    if w then
        for dep_subs in pairs(w.deps) do
            dep_subs[w.run] = nil
        end
        _watchers[id] = nil
    end
end

function trigger()
    local list = {}
    for _, w in pairs(_watchers) do table.insert(list, w) end
    for _, w in ipairs(list) do w.run() end
end

function tap(fn)
    return function(x)
        fn(x)
        return x
    end
end

local function is_array(t)
    return type(t) == "table" and (rawget(t, 1) ~= nil)
end

local function infer_type(t)
    local first = t[1]
    local ttype = type(first)

    for i = 2, #t do
        if type(t[i]) ~= ttype then
            return nil, "mixed types"
        end
    end

    if ttype == "number" then
        return "double"
    elseif ttype == "string" then
        return "const char*"
    elseif ttype == "boolean" then
        return "bool"
    else
        return nil, "unsupported type: " .. ttype
    end
end

local function to_c_array(self, explicit_type)
    if not is_array(self) then
        error("ptr(): table is not a pure array")
    end

    local ctype

    if explicit_type then
        ctype = explicit_type
    else
        local inferred, err = infer_type(self)
        if not inferred then
            error("ptr(): " .. err)
        end
        ctype = inferred
    end

    local n = #self

    local arr = ffi.new(ctype .. "[?]", n)

    for i = 1, n do
        arr[i-1] = self[i]
    end

    return arr
end

local function from_c_array(ptr, ctype, len)
    if ptr == ffi.NULL or ptr == nil then return nil end

    -- 1. Приводим void* к запрашиваемому типу указателя
    local typed_ptr = ffi.cast(ctype .. "*", ptr)

    -- 2. Собираем элементы в Lime-массив (_arr)
    local res = _arr({})
    for i = 0, len - 1 do
        res:add(typed_ptr[i])
    end
    return res
end

local array_methods = {
    sum = function(self)
        local total = 0
        for _, v in ipairs(self) do total = total + v end
        return total
    end,
    push = function(self, val) table.insert(self, val) end,
    add = function(self, val) table.insert(self, val) end,
    pop = function(self) return table.remove(self) end,
    shift = function(self) return table.remove(self, 1) end,
    first = function(self) return self[1] end,
    last = function(self) return self[#self] end,
    len = function(self) return #self end,
    clear = function(self)
        for i = #self, 1, -1 do table.remove(self, i) end
    end,
    map = function(self, func)
        local res = {}
        for k, v in pairs(self) do res[k] = func(v, k) end
        return res
    end,
    ptr = to_c_array,
    tostr = function(self)
    local is_array = true
    local count = 0

    local k = nil
    while true do
        k = next(self, k)
        if k == nil then break end

        count = count + 1
        if type(k) ~= "number" or k <= 0 or math.floor(k) ~= k then
            is_array = false
            break
        end
    end

    if is_array and count > 0 then
        for i = 1, count do
            if rawget(self, i) == nil then
                is_array = false
                break
            end
        end
    end

    local items = {}

    if is_array and count > 0 then
        for i = 1, count do
            local v = rawget(self, i)
            local val_str = type(v) == "string" and string.format("%q", v) or tostring(v)
            table.insert(items, val_str)
        end
        return "[" .. table.concat(items, ", ") .. "]"
    else
        -- Важно: тут мы используем стандартный next, чтобы собирать словарь правильно
        local k_curr = nil
        while true do
            local v_curr
            k_curr, v_curr = next(self, k_curr)
            if k_curr == nil then break end

            local key_str = type(k_curr) == "string" and string.format("%q", k_curr) or tostring(k_curr)
            local val_str = type(v_curr) == "string" and string.format("%q", v_curr) or tostring(v_curr)
            table.insert(items, key_str .. ": " .. val_str)
        end
        return "{" .. table.concat(items, ", ") .. "}"
    end
end
}

local array_mt = {
    __index = function(self, key)
        if type(key) == "number" then
            if key >= 0 then
                return rawget(self, key + 1)
            elseif key == -1 then
                return rawget(self, #self)
            elseif key < 0 then
                return rawget(self, #self + key + 1)
            end
        end
        return array_methods[key]
    end,

    __newindex = function(self, key, value)
        if type(key) == "number" and key >= 0 then
            rawset(self, key + 1, value)
        else
            rawset(self, key, value)
        end
    end,
    __len = function(self) return #self end,
    __tostring = function(self)
    local is_array = true
    local count = 0

    local k = nil
    while true do
        k = next(self, k)
        if k == nil then break end

        count = count + 1
        if type(k) ~= "number" or k <= 0 or math.floor(k) ~= k then
            is_array = false
            break
        end
    end

    if is_array and count > 0 then
        for i = 1, count do
            if rawget(self, i) == nil then
                is_array = false
                break
            end
        end
    end

    local items = {}

    if is_array and count > 0 then
        for i = 1, count do
            local v = rawget(self, i)
            local val_str = type(v) == "string" and string.format("%q", v) or tostring(v)
            table.insert(items, val_str)
        end
        return "[" .. table.concat(items, ", ") .. "]"
    else
        -- Важно: тут мы используем стандартный next, чтобы собирать словарь правильно
        local k_curr = nil
        while true do
            local v_curr
            k_curr, v_curr = next(self, k_curr)
            if k_curr == nil then break end

            local key_str = type(k_curr) == "string" and string.format("%q", k_curr) or tostring(k_curr)
            local val_str = type(v_curr) == "string" and string.format("%q", v_curr) or tostring(v_curr)
            table.insert(items, key_str .. ": " .. val_str)
        end
        return "{" .. table.concat(items, ", ") .. "}"
    end
end
}

function _arr(t)
    return setmetatable(t, array_mt)
end

args = _arr(args)

local function carr(config, lua_table)
    if type(lua_table) ~= "table" then return lua_table end

    local size = #lua_table

    local c_arr = ffi.new("double[?]", size)
    for i = 1, size do
        c_arr[i - 1] = lua_table[i]
    end
    return c_arr
end

string.split = function(self, sep)
    sep = sep or "%s"
    local result = _arr({})
    if sep == "" then
    for item in string.gmatch(self, ".") do
        result:add(item)
    end
    else
    for item in string.gmatch(self, "([^" .. sep .. "]+)") do
        result:add(item)
    end
    end
    return result
end

string.trim = function(self)
    return self:match("^%s*(.-)%s*$")
end

string.startswith = function(self, prefix)
    return self:sub(1, #prefix) == prefix
end

string.endswith = function(self, suffix)
    return suffix == "" or self:sub(-#suffix) == suffix
end

string.contains = function(self, sub)
    return self:find(sub, 1, true) ~= nil
end

string.replace = function(self, old, new)
    local escaped_old = old:gsub("[%(%)%.%%%+%-%*%?%[%^%$]", "%%%1")
    return self:gsub(escaped_old, new)
end

string.join = function(self, tbl)
    return table.concat(tbl, self)
end

string.isdigit = function(self)
    return self:match("^%d+$") ~= nil
end

debug.setmetatable(0, {
    __index = {
        isEven = function(self)
            return self % 2 == 0
        end,

        clamp = function(self, min, max)
            if self < min then return min end
            if self > max then return max end
            return self
        end,

        round = function(self)
            return math.floor(self + 0.5)
        end,

        sign = function(self)
            if self > 0 then return 1 end
            if self < 0 then return -1 end
            return 0
        end,

        abs = function(self)
            return math.abs(self)
        end,

        odd = function(self)
            return self % 2 ~= 0
        end,

        range = function(self, min, max)
            return self >= min and self <= max
        end,

        fract = function(self)
            return self - math.floor(self)
        end
    }
})
"""

help = """Lime is programming language that simple as Python
Version: 1.0.0

Using:
    lime <PATH> [ARGS]

Examples:
    lime .../MyProj --lua (Compiling without parsing at non-first executing without changing)

    lime build-exe GameInLime -o mygame.exe --console --icon icon.ico

    lime --version
    lime --help

Github: "https://github.com/Ilya5627/LimeLang-Transpiler\""""