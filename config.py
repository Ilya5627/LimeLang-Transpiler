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
    -- ═══════════════════════════════════════════
    --  БАЗОВЫЕ (существующие)
    -- ═══════════════════════════════════════════

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
        for i, v in ipairs(self) do
            res[i] = func(v, i - 1)
        end
        return setmetatable(res, getmetatable(self))
    end,

    ptr = to_c_array,

    -- ═══════════════════════════════════════════
    --  ПОИСК
    -- ═══════════════════════════════════════════

    includes = function(self, val)
        for _, v in ipairs(self) do
            if v == val then return true end
        end
        return false
    end,

    index_of = function(self, val)
        for i, v in ipairs(self) do
            if v == val then return i - 1 end
        end
        return -1
    end,

    find = function(self, predicate)
        for _, v in ipairs(self) do
            if predicate(v) then return v end
        end
        return nil
    end,

    find_index = function(self, predicate)
        for i, v in ipairs(self) do
            if predicate(v) then return i - 1 end
        end
        return -1
    end,

    find_last = function(self, predicate)
        for i = #self, 1, -1 do
            if predicate(self[i]) then return self[i] end
        end
        return nil
    end,

    -- ═══════════════════════════════════════════
    --  ФИЛЬТРАЦИЯ И АГРЕГАЦИЯ
    -- ═══════════════════════════════════════════

    filter = function(self, predicate)
        local res = {}
        for _, v in ipairs(self) do
            if predicate(v) then table.insert(res, v) end
        end
        return setmetatable(res, getmetatable(self))
    end,

    reject = function(self, predicate)
        local res = {}
        for _, v in ipairs(self) do
            if not predicate(v) then table.insert(res, v) end
        end
        return setmetatable(res, getmetatable(self))
    end,

    reduce = function(self, fn, initial)
        local acc = initial
        local start = 1
        if acc == nil then
            acc = self[1]
            start = 2
        end
        for i = start, #self do
            acc = fn(acc, self[i], i - 1)
        end
        return acc
    end,

    every = function(self, predicate)
        for _, v in ipairs(self) do
            if not predicate(v) then return false end
        end
        return true
    end,

    some = function(self, predicate)
        for _, v in ipairs(self) do
            if predicate(v) then return true end
        end
        return false
    end,

    count = function(self, predicate)
        if predicate == nil then return #self end
        local n = 0
        for _, v in ipairs(self) do
            if predicate(v) then n = n + 1 end
        end
        return n
    end,

    -- ═══════════════════════════════════════════
    --  АГРЕГАЦИЯ ЧИСЕЛ
    -- ═══════════════════════════════════════════

    min = function(self)
        if #self == 0 then return nil end
        local m = self[1]
        for i = 2, #self do
            if self[i] < m then m = self[i] end
        end
        return m
    end,

    max = function(self)
        if #self == 0 then return nil end
        local m = self[1]
        for i = 2, #self do
            if self[i] > m then m = self[i] end
        end
        return m
    end,

    avg = function(self)
        if #self == 0 then return 0 end
        local total = 0
        for _, v in ipairs(self) do total = total + v end
        return total / #self
    end,

    product = function(self)
        local p = 1
        for _, v in ipairs(self) do p = p * v end
        return p
    end,

    min_max = function(self)
        if #self == 0 then return nil, nil end
        local mn, mx = self[1], self[1]
        for i = 2, #self do
            if self[i] < mn then mn = self[i] end
            if self[i] > mx then mx = self[i] end
        end
        return mn, mx
    end,

    -- ═══════════════════════════════════════════
    --  ТРАНСФОРМАЦИИ
    -- ═══════════════════════════════════════════

    reverse = function(self)
        local res = {}
        for i = #self, 1, -1 do
            table.insert(res, self[i])
        end
        return setmetatable(res, getmetatable(self))
    end,

    sort = function(self, comp)
        local copy = {}
        for _, v in ipairs(self) do table.insert(copy, v) end
        table.sort(copy, comp)
        return setmetatable(copy, getmetatable(self))
    end,

    sort_by = function(self, key_fn)
        local copy = {}
        for _, v in ipairs(self) do table.insert(copy, v) end
        table.sort(copy, function(a, b)
            return key_fn(a) < key_fn(b)
        end)
        return setmetatable(copy, getmetatable(self))
    end,

    unique = function(self)
        local seen = {}
        local res = {}
        for _, v in ipairs(self) do
            if not seen[v] then
                seen[v] = true
                table.insert(res, v)
            end
        end
        return setmetatable(res, getmetatable(self))
    end,

    unique_by = function(self, key_fn)
        local seen = {}
        local res = {}
        for _, v in ipairs(self) do
            local key = key_fn(v)
            if not seen[key] then
                seen[key] = true
                table.insert(res, v)
            end
        end
        return setmetatable(res, getmetatable(self))
    end,

    flatten = function(self, depth)
        depth = depth or 1
        local res = {}
        local function _flat(t, d)
            for _, v in ipairs(t) do
                if type(v) == "table" and d > 0 and rawget(v, 1) ~= nil then
                    _flat(v, d - 1)
                else
                    table.insert(res, v)
                end
            end
        end
        _flat(self, depth)
        return setmetatable(res, getmetatable(self))
    end,

    flat_map = function(self, fn)
        local res = {}
        for _, v in ipairs(self) do
            local mapped = fn(v)
            if type(mapped) == "table" and rawget(mapped, 1) ~= nil then
                for _, item in ipairs(mapped) do
                    table.insert(res, item)
                end
            else
                table.insert(res, mapped)
            end
        end
        return setmetatable(res, getmetatable(self))
    end,

    -- ═══════════════════════════════════════════
    --  СРЕЗЫ И ПОДМАССИВЫ
    -- ═══════════════════════════════════════════

    slice = function(self, start_idx, end_idx)
        local n = #self
        start_idx = start_idx or 0
        end_idx = end_idx or (n - 1)
        if start_idx < 0 then start_idx = n + start_idx end
        if end_idx < 0 then end_idx = n + end_idx end
        local res = {}
        for i = start_idx + 1, end_idx + 1 do
            if i >= 1 and i <= n then
                table.insert(res, self[i])
            end
        end
        return setmetatable(res, getmetatable(self))
    end,

    take = function(self, n)
        local res = {}
        for i = 1, math.min(n, #self) do
            table.insert(res, self[i])
        end
        return setmetatable(res, getmetatable(self))
    end,

    drop = function(self, n)
        local res = {}
        for i = n + 1, #self do
            table.insert(res, self[i])
        end
        return setmetatable(res, getmetatable(self))
    end,

    chunk = function(self, size)
        local res = {}
        local current = {}
        for _, v in ipairs(self) do
            table.insert(current, v)
            if #current == size then
                table.insert(res, setmetatable(current, getmetatable(self)))
                current = {}
            end
        end
        if #current > 0 then
            table.insert(res, setmetatable(current, getmetatable(self)))
        end
        return setmetatable(res, getmetatable(self))
    end,

    -- ═══════════════════════════════════════════
    --  КОМБИНИРОВАНИЕ
    -- ═══════════════════════════════════════════

    concat = function(self, other)
        local res = {}
        for _, v in ipairs(self) do table.insert(res, v) end
        if type(other) == "table" then
            for _, v in ipairs(other) do table.insert(res, v) end
        else
            table.insert(res, other)
        end
        return setmetatable(res, getmetatable(self))
    end,

    zip = function(self, other)
        local res = {}
        local n = math.min(#self, #other)
        for i = 1, n do
            table.insert(res, setmetatable({self[i], other[i]}, getmetatable(self)))
        end
        return setmetatable(res, getmetatable(self))
    end,

    interleave = function(self, other)
        local res = {}
        local n = math.max(#self, #other)
        for i = 1, n do
            if self[i] ~= nil then table.insert(res, self[i]) end
            if other[i] ~= nil then table.insert(res, other[i]) end
        end
        return setmetatable(res, getmetatable(self))
    end,

    -- ═══════════════════════════════════════════
    --  ИТЕРАЦИЯ
    -- ═══════════════════════════════════════════

    for_each = function(self, fn)
        for i, v in ipairs(self) do
            fn(v, i - 1)
        end
    end,

    enumerate = function(self)
        local i = 0
        return function()
            i = i + 1
            if i <= #self then
                return i - 1, self[i]
            end
            return nil
        end
    end,

    cycle = function(self, times)
        local res = {}
        times = times or 1
        for _ = 1, times do
            for _, v in ipairs(self) do
                table.insert(res, v)
            end
        end
        return setmetatable(res, getmetatable(self))
    end,

    -- ═══════════════════════════════════════════
    --  МУТАЦИИ
    -- ═══════════════════════════════════════════

    fill = function(self, val, start_idx, end_idx)
        start_idx = (start_idx or 0) + 1
        end_idx = (end_idx or (#self - 1)) + 1
        for i = start_idx, end_idx do
            self[i] = val
        end
        return self
    end,

    swap = function(self, i, j)
        i, j = i + 1, j + 1
        self[i], self[j] = self[j], self[i]
        return self
    end,

    insert_at = function(self, idx, val)
        table.insert(self, idx + 1, val)
        return self
    end,

    remove_at = function(self, idx)
        return table.remove(self, idx + 1)
    end,

    set = function(self, idx, val)
        self[idx + 1] = val
        return self
    end,

    -- ═══════════════════════════════════════════
    --  СЛУЧАЙНОСТЬ
    -- ═══════════════════════════════════════════

    shuffle = function(self)
        local res = {}
        for _, v in ipairs(self) do table.insert(res, v) end
        for i = #res, 2, -1 do
            local j = math.random(i)
            res[i], res[j] = res[j], res[i]
        end
        return setmetatable(res, getmetatable(self))
    end,

    sample = function(self)
        if #self == 0 then return nil end
        return self[math.random(#self)]
    end,

    sample_n = function(self, n)
        local shuffled = self:shuffle()
        return shuffled:take(n)
    end,

    -- ═══════════════════════════════════════════
    --  ГРУППИРОВКА И РАЗДЕЛЕНИЕ
    -- ═══════════════════════════════════════════

    group_by = function(self, key_fn)
        local res = setmetatable({}, getmetatable(self))
        for _, v in ipairs(self) do
            local key = key_fn(v)
            if rawget(res, key) == nil then
                rawset(res, key, setmetatable({}, getmetatable(self)))
            end
            rawget(res, key):add(v)
        end
        return res
    end,

    partition = function(self, predicate)
        local yes, no = {}, {}
        for _, v in ipairs(self) do
            if predicate(v) then
                table.insert(yes, v)
            else
                table.insert(no, v)
            end
        end
        return setmetatable(yes, getmetatable(self)), setmetatable(no, getmetatable(self))
    end,

    distinct_by = function(self, key_fn)
        local seen = {}
        local res = {}
        for _, v in ipairs(self) do
            local key = key_fn(v)
            if not seen[key] then
                seen[key] = true
                table.insert(res, v)
            end
        end
        return setmetatable(res, getmetatable(self))
    end,

    -- ═══════════════════════════════════════════
    --  СЛОВАРНЫЕ МЕТОДЫ (для dict-объектов)
    -- ═══════════════════════════════════════════

    keys = function(self)
        local res = {}
        for k, _ in next, self do
            if type(k) ~= "number" or k <= 0 or math.floor(k) ~= k then
                table.insert(res, k)
            end
        end
        return setmetatable(res, getmetatable(self))
    end,

    values = function(self)
        local res = {}
        for k, v in next, self do
            if type(k) ~= "number" or k <= 0 or math.floor(k) ~= k then
                table.insert(res, v)
            end
        end
        return setmetatable(res, getmetatable(self))
    end,

    entries = function(self)
        local res = {}
        for k, v in next, self do
            if type(k) ~= "number" or k <= 0 or math.floor(k) ~= k then
                table.insert(res, setmetatable({k, v}, getmetatable(self)))
            end
        end
        return setmetatable(res, getmetatable(self))
    end,

    has = function(self, key)
        return rawget(self, key) ~= nil
    end,

    get = function(self, key, default)
        local v = rawget(self, key)
        if v == nil then return default end
        return v
    end,

    set_key = function(self, key, value)
        rawset(self, key, value)
        return self
    end,

    remove_key = function(self, key)
        local v = rawget(self, key)
        rawset(self, key, nil)
        return v
    end,

    merge = function(self, other)
        local res = {}
        for k, v in next, self do res[k] = v end
        for k, v in next, other do res[k] = v end
        return setmetatable(res, getmetatable(self))
    end,

    size = function(self)
        local n = 0
        for _ in next, self do n = n + 1 end
        return n
    end,

    map_values = function(self, fn)
        local res = {}
        for k, v in next, self do
            if type(k) ~= "number" or k <= 0 or math.floor(k) ~= k then
                res[k] = fn(v, k)
            end
        end
        return setmetatable(res, getmetatable(self))
    end,

    -- ═══════════════════════════════════════════
    --  СТРОКОВОЕ ПРЕДСТАВЛЕНИЕ
    -- ═══════════════════════════════════════════

    join = function(self, sep)
        sep = sep or ", "
        local parts = {}
        for _, v in ipairs(self) do
            table.insert(parts, tostring(v))
        end
        return table.concat(parts, sep)
    end,

    tostr = function(self)
        local is_arr = true
        local count = 0

        local k = nil
        while true do
            k = next(self, k)
            if k == nil then break end
            count = count + 1
            if type(k) ~= "number" or k <= 0 or math.floor(k) ~= k then
                is_arr = false
                break
            end
        end

        if is_arr and count > 0 then
            for i = 1, count do
                if rawget(self, i) == nil then
                    is_arr = false
                    break
                end
            end
        end

        local items = {}

        if is_arr and count > 0 then
            for i = 1, count do
                local v = rawget(self, i)
                local val_str = type(v) == "string" and string.format("%q", v) or tostring(v)
                table.insert(items, val_str)
            end
            return "[" .. table.concat(items, ", ") .. "]"
        else
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
    end,

    -- ═══════════════════════════════════════════
    --  FFI / C-Interop
    -- ═══════════════════════════════════════════

    ptr = to_c_array,

    to_bytes = function(self)
        local buf = ffi.new("uint8_t[?]", #self)
        for i = 1, #self do
            buf[i - 1] = self[i] % 256
        end
        return buf
    end,

    -- ═══════════════════════════════════════════
    --  УТИЛИТЫ
    -- ═══════════════════════════════════════════

    is_empty = function(self)
        return #self == 0
    end,

    contains_all = function(self, items)
        local set = {}
        for _, v in ipairs(self) do set[v] = true end
        for _, item in ipairs(items) do
            if not set[item] then return false end
        end
        return true
    end,

    contains_any = function(self, items)
        local set = {}
        for _, v in ipairs(self) do set[v] = true end
        for _, item in ipairs(items) do
            if set[item] then return true end
        end
        return false
    end,

    diff = function(self, other)
        local set = {}
        for _, v in ipairs(other) do set[v] = true end
        local res = {}
        for _, v in ipairs(self) do
            if not set[v] then table.insert(res, v) end
        end
        return setmetatable(res, getmetatable(self))
    end,

    intersect = function(self, other)
        local set = {}
        for _, v in ipairs(other) do set[v] = true end
        local res = {}
        for _, v in ipairs(self) do
            if set[v] then table.insert(res, v) end
        end
        return setmetatable(res, getmetatable(self))
    end,

    union = function(self, other)
        local seen = {}
        local res = {}
        for _, v in ipairs(self) do
            if not seen[v] then seen[v] = true; table.insert(res, v) end
        end
        for _, v in ipairs(other) do
            if not seen[v] then seen[v] = true; table.insert(res, v) end
        end
        return setmetatable(res, getmetatable(self))
    end,

    repeat_ = function(self, times)
        local res = {}
        for _ = 1, times do
            for _, v in ipairs(self) do
                table.insert(res, v)
            end
        end
        return setmetatable(res, getmetatable(self))
    end,

    sorted_index_of = function(self, val)
        -- Бинарный поиск для отсортированного массива
        local lo, hi = 1, #self
        while lo <= hi do
            local mid = math.floor((lo + hi) / 2)
            if self[mid] == val then return mid - 1
            elseif self[mid] < val then lo = mid + 1
            else hi = mid - 1
            end
        end
        return -1
    end,
    rotate = function(self, n)
        local len = #self
        if len == 0 then return self end
        n = n % len
        if n < 0 then n = n + len end
        if n == 0 then return self end
        
        local res = {}
        for i = len - n + 1, len do table.insert(res, self[i]) end
        for i = 1, len - n do table.insert(res, self[i]) end
        return setmetatable(res, getmetatable(self))
    end,

    -- Очистка от nil и false значений
    compact = function(self)
        local res = {}
        for _, v in ipairs(self) do
            if v and v ~= false then table.insert(res, v) end
        end
        return setmetatable(res, getmetatable(self))
    end,
}

local array_mt = {
    __index = function(self, key)
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
    local result = _arr({})
    if sep == "" then
        for item in string.gmatch(self, ".") do
            result:add(item)
        end
    else
        local escaped = sep:gsub("[%(%)%.%%%+%-%*%?%[%^%$]", "%%%1")
        local pattern = "(.-)(" .. escaped .. ")"
        --                       ^^^^^^^^^^^^^^^^  теперь ДВА capture
        local last_end = 1
        for item, sep_found in string.gmatch(self, pattern) do
            result:add(item)
            last_end = last_end + #item + #sep_found
        end
        result:add(self:sub(last_end))
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
string.format = string.format
string.upper = string.upper
string.lower = string.lower

string.capitalize = function(self)
    if #self == 0 then return self end
    return self:sub(1, 1):upper() .. self:sub(2):lower()
end

string.pad_left = function(self, len, char)
    char = char or " "
    if #self >= len then return self end
    return string.rep(char, len - #self) .. self
end

string.pad_right = function(self, len, char)
    char = char or " "
    if #self >= len then return self end
    return self .. string.rep(char, len - #self)
end

string.isalpha = function(self)
    return self:match("^%a+$") ~= nil
end

string.isalnum = function(self)
    return self:match("^%w+$") ~= nil
end

-- Разбивает строку на массив отдельных символов
string.chars = function(self)
    local res = _arr({})
    for i = 1, #self do res:add(self:sub(i, i)) end
    return res
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
        end,
        lerp = function(self, target, t)
            return self + (target - self) * t
        end,

        -- Конвертация углов
        to_rad = function(self)
            return self * math.pi / 180.0
        end,

        to_deg = function(self)
            return self * 180.0 / math.pi
        end,

        -- Шестнадцатеричное и двоичное представление
        to_hex = function(self)
            return string.format("%x", math.floor(self))
        end,

        to_bin = function(self)
            local n = math.floor(self)
            if n == 0 then return "0" end
            local t = {}
            while n > 0 do
                local rest = math.floor(n % 2)
                table.insert(t, 1, rest)
                n = math.floor((n - rest) / 2)
            end
            return table.concat(t)
        end
    }
})

local function _idx(t, i)
    if type(t) == "cdata" then
        return t[i]
    elseif type(i) == "number" then
        return t[i + 1]
    else
        return t[i]
    end
end

local function _setidx(t, i, v)
    if type(t) == "cdata" then
        t[i] = v
    elseif type(i) == "number" then
        t[i + 1] = v
    else
        t[i] = v
    end
end

local function _safe_dot(obj, field)
    if obj == nil then return nil end
    return obj[field]
end

local function _safe_call(obj, method, ...)
    if obj == nil then return nil end
    return obj[method](obj, ...)
end
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