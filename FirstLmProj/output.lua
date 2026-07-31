-- WARNING: It is LimeLang executing code, so it can be with uncorrected work without lime.exe executing
-- You can run it without parsing with "lime [PATH] --lua"
ffi.cdef([[

    typedef void* HWND; typedef void* HMENU; typedef void* HINSTANCE;
    typedef void* HICON; typedef void* HCURSOR; typedef void* HBRUSH;
    typedef unsigned int UINT; typedef unsigned long DWORD;
    typedef long long LRESULT; typedef unsigned long long WPARAM;
    typedef long long LPARAM; typedef void* HDC;

    typedef LRESULT (*WNDPROC)(HWND, UINT, WPARAM, LPARAM);

    typedef struct _WNDCLASSEXA {
        UINT cbSize; UINT style; WNDPROC lpfnWndProc; int cbClsExtra; int cbWndExtra;
        HINSTANCE hInstance; HICON hIcon; HCURSOR hCursor; HBRUSH hbrBackground;
        const char* lpszMenuName; const char* lpszClassName; HICON hIconSm;
    } WNDCLASSEXA;
    typedef struct _POINT { long x; long y; } POINT;
    typedef struct _MSG {
        HWND hwnd; UINT message; WPARAM wParam; LPARAM lParam;
        DWORD time; POINT pt; DWORD lPrivate;
    } MSG;

    unsigned short RegisterClassExA(const WNDCLASSEXA*);
    HWND CreateWindowExA(DWORD dwExStyle, const char* lpClassName, const char* lpWindowName, DWORD dwStyle, int X, int Y, int nWidth, int nHeight, HWND hWndParent, HMENU hMenu, HINSTANCE hInstance, void* lpParam);
    int ShowWindow(HWND hWnd, int nCmdShow);
    int UpdateWindow(HWND hWnd);
    int GetMessageA(MSG* lpMsg, HWND hWnd, UINT wMsgFilterMin, UINT wMsgFilterMax);
    int TranslateMessage(const MSG* lpMsg);
    LRESULT DispatchMessageA(const MSG* lpMsg);
    LRESULT DefWindowProcA(HWND hWnd, UINT Msg, WPARAM wParam, LPARAM lParam);
    void PostQuitMessage(int nExitCode);
    int SetWindowTextA(HWND hWnd, const char* lpString);
    int GetWindowTextA(HWND hWnd, char* lpString, int nMaxCount);
    int MoveWindow(HWND hWnd, int X, int Y, int nWidth, int nHeight, int bRepaint);
    int DestroyWindow(HWND hWnd);
    LRESULT SendMessageA(HWND hWnd, UINT Msg, WPARAM wParam, LPARAM lParam);
    HBRUSH GetSysColorBrush(int nIndex);
    int InvalidateRect(HWND hWnd, void* lpRect, int bErase);
]])
local user32 = ffi.load('C:/Windows/System32/user32.dll')
ffi.cdef([[
void* GetModuleHandleA(const char* lpModuleName);]])
local kernel32 = ffi.load('C:/Windows/System32/kernel32.dll')
ffi.cdef([[

    typedef void* HFONT;
    typedef unsigned long COLORREF;
    HFONT CreateFontA(int cHeight, int cWidth, int cEscapement, int cOrientation, int cWeight, DWORD bItalic, DWORD bUnderline, DWORD bStrikeOut, DWORD iCharSet, DWORD iOutPrecision, DWORD iClipPrecision, DWORD iQuality, DWORD iPitchAndFamily, const char* pszFaceName);
    COLORREF SetTextColor(void* hdc, COLORREF color);
    int SetBkMode(void* hdc, int mode);
    int DeleteObject(void* hObject);
]])
local gdi32 = ffi.load('C:/Windows/System32/gdi32.dll')
local function rgb(r, g, b)
return ((r+(g*256))+(b*65536))

end
local font_cache = _arr({})
local function get_font(size, is_bold, is_italic, name)
if (size==nil) then
size = 16

end
if (is_bold==nil) then
is_bold = false

end
if (is_italic==nil) then
is_italic = false

end
if (name==nil) then
name = ("Segoe UI")

end
local cache_key = ((((((name..("_"))..size)..("_"))..tostring(is_bold))..("_"))..tostring(is_italic))
if (font_cache[cache_key]~=nil) then
return font_cache[cache_key]

end
local weight = 400
if is_bold then
weight = 700

end
local italic_flag = 0
if is_italic then
italic_flag = 1

end
local font = gdi32.CreateFontA(-size, 0, 0, 0, weight, italic_flag, 0, 0, 1, 0, 0, 5, 0, name)
font_cache[cache_key] = font
return font

end
local next_id = 1
local function gen_id()
local id = next_id
next_id = (next_id+1)
return id

end
local function vnode(type, props, children)
if (props==nil) then
props = _arr({})

end
if (children==nil) then
children = _arr({})

end
if (props.key==nil) then
props.key = (("auto_")..gen_id())

end
return _arr({[("type")] = type, [("props")] = props, [("children")] = children, [("id")] = props.key})

end
local function column(props, children)
if (children==nil) then
return vnode(("column"), _arr({}), props)

end
return vnode(("column"), props, children)

end
local function row(props, children)
if (children==nil) then
return vnode(("row"), _arr({}), props)

end
return vnode(("row"), props, children)

end
local function text(content, props)
if (props==nil) then
props = _arr({})

end
props.text = tostring(content)
return vnode(("text"), props, _arr({}))

end
local function button(label, on_click, props)
if (props==nil) then
props = _arr({})

end
props.text = tostring(label)
props.on_click = on_click
return vnode(("button"), props, _arr({}))

end
local function input(text_val, on_change, props)
if (props==nil) then
props = _arr({})

end
props.text = tostring(text_val)
props.on_change = on_change
return vnode(("input"), props, _arr({}))

end
local function checkbox(label, on_change, props)
if (props==nil) then
props = _arr({})

end
props.text = tostring(label)
props.on_change = on_change
return vnode(("checkbox"), props, _arr({}))

end
local function slider(min_val, max_val, value, on_change, props)
if (props==nil) then
props = _arr({})

end
props.min = min_val
props.max = max_val
props.value = value
props.on_change = on_change
return vnode(("slider"), props, _arr({}))

end
local function card(props, children)
if (props==nil) then
props = _arr({})

end
if (props.bg_color==nil) then
props.bg_color = rgb(245, 245, 245)

end
if (props.padding==nil) then
props.padding = 15

end
return vnode(("card"), props, children)

end
local function layout(vnode, x, y, w, h)
local node = _arr({[("vnode")] = vnode, [("x")] = x, [("y")] = y, [("w")] = w, [("h")] = h, [("children")] = _arr({})})
local pad = 10
if (vnode.props.padding~=nil) then
pad = vnode.props.padding

end
local spacing = 8
if (vnode.props.spacing~=nil) then
spacing = vnode.props.spacing

end
local ix = (x+pad)
local iy = (y+pad)
local iw = (w-(pad*2))
local ih = (h-(pad*2))
local count = vnode.children:len()
if (count==0) then
return node

end
local total_weight = 0
local fixed_size = 0
for child in pairs(vnode.children) do
if (child.props.weight~=nil) then
total_weight = (total_weight+child.props.weight)

else
if (vnode.type==("column")) then
fixed_size = (fixed_size+(child.props.height or 40))

else
fixed_size = (fixed_size+(child.props.width or 100))

end

end


::next_1::
end
local flex_space = 0
if (vnode.type==("column")) then
flex_space = ((ih-fixed_size)-(spacing*(count-1)))

else
flex_space = ((iw-fixed_size)-(spacing*(count-1)))

end
if (flex_space<0) then
flex_space = 0

end
local curr_x = ix
local curr_y = iy
for child in pairs(vnode.children) do
local cw = iw
local ch = ih
if (vnode.type==("column")) then
if (child.props.weight~=nil) then
ch = ((flex_space*child.props.weight)/total_weight)

else
ch = (child.props.height or 40)

end
node.children:push(layout(child, ix, curr_y, iw, ch))
curr_y = ((curr_y+ch)+spacing)

else
if (child.props.weight~=nil) then
cw = ((flex_space*child.props.weight)/total_weight)

else
cw = (child.props.width or 100)

end
node.children:push(layout(child, curr_x, iy, cw, ih))
curr_x = ((curr_x+cw)+spacing)

end


::next_2::
end
return node

end
local click_handlers = _arr({})
local change_handlers = _arr({})
local node_registry = _arr({})
local global_wndproc = ffi.cast(("WNDPROC"), function(hwnd, msg, wparam, lparam)
if (msg==2) then
user32.PostQuitMessage(0)
return 0

end
if (msg==312) then
local hdc = ffi.cast(("HDC"), wparam)
local child_hwnd = ffi.cast(("HWND"), lparam)
local v = node_registry[tostring(child_hwnd)]
if ((v~=nil) and (v.props.color~=nil)) then
gdi32.SetTextColor(hdc, v.props.color)

end
gdi32.SetBkMode(hdc, 1)
return ffi.cast(("LRESULT"), user32.GetSysColorBrush(15))

end
if (msg==273) then
local child_hwnd = ffi.cast(("HWND"), lparam)
local key = tostring(child_hwnd)
local wp_num = tonumber(wparam)
local notification = math.floor((wp_num/65536))
if (notification==0) then
local handler = click_handlers[key]
if (handler~=nil) then
handler()

end
local v = node_registry[key]
if (((v~=nil) and (v.type==("checkbox"))) and (v.props.on_change~=nil)) then
local state = user32.SendMessageA(child_hwnd, 240, 0, 0)
v.props.on_change((state==1))

end

elseif (notification==768) then
local handler = change_handlers[key]
if (handler~=nil) then
local buffer = ffi.new(("char[1024]"))
user32.GetWindowTextA(child_hwnd, buffer, 1024)
handler(ffi.string(buffer))

end

end

end
if ((msg==276) or (msg==277)) then
local child_hwnd = ffi.cast(("HWND"), lparam)
if (child_hwnd~=ffi.NULL) then
local key = tostring(child_hwnd)
local handler = change_handlers[key]
if (handler~=nil) then
local pos = user32.SendMessageA(child_hwnd, 1024, 0, 0)
handler(pos)

end

end

end
return user32.DefWindowProcA(hwnd, msg, wparam, lparam)

end)
local function apply_styles(hwnd, v)
local key = tostring(hwnd)
node_registry[key] = v
local font = get_font(v.props.size, v.props.bold, v.props.italic, v.props.font)
user32.SendMessageA(hwnd, 48, ffi.cast(("WPARAM"), font), ffi.cast(("LPARAM"), 1))

end
local function patch(parent, old_node, new_node)
if (new_node==nil) then
if ((old_node~=nil) and (old_node.hwnd~=nil)) then
local key = tostring(old_node.hwnd)
if (old_node.vnode.props.on_unmount~=nil) then
old_node.vnode.props.on_unmount(old_node.hwnd)

end
click_handlers[key] = nil
change_handlers[key] = nil
node_registry[key] = nil
user32.DestroyWindow(old_node.hwnd)

end
return nil

end
if (((old_node==nil) or (old_node.vnode.type~=new_node.vnode.type)) or (old_node.vnode.props.key~=new_node.vnode.props.key)) then
if ((old_node~=nil) and (old_node.hwnd~=nil)) then
patch(parent, old_node, nil)

end
local v = new_node.vnode
local hwnd = nil
local hInst = kernel32.GetModuleHandleA(ffi.NULL)
if (v.type==("button")) then
hwnd = user32.CreateWindowExA(0, ("BUTTON"), v.props.text, 1342177280, new_node.x, new_node.y, new_node.w, new_node.h, parent, ffi.NULL, hInst, ffi.NULL)

elseif (v.type==("text")) then
local style = 1342177280
if (v.props.align==("center")) then
style = 1342177281

end
hwnd = user32.CreateWindowExA(0, ("STATIC"), v.props.text, style, new_node.x, new_node.y, new_node.w, new_node.h, parent, ffi.NULL, hInst, ffi.NULL)

elseif (v.type==("input")) then
hwnd = user32.CreateWindowExA(512, ("EDIT"), v.props.text, 1342242944, new_node.x, new_node.y, new_node.w, new_node.h, parent, ffi.NULL, hInst, ffi.NULL)

elseif (v.type==("checkbox")) then
hwnd = user32.CreateWindowExA(0, ("BUTTON"), v.props.text, 1342242819, new_node.x, new_node.y, new_node.w, new_node.h, parent, ffi.NULL, hInst, ffi.NULL)

elseif (v.type==("slider")) then
hwnd = user32.CreateWindowExA(0, ("msctls_trackbar32"), (""), 1342242816, new_node.x, new_node.y, new_node.w, new_node.h, parent, ffi.NULL, hInst, ffi.NULL)
if (v.props.value~=nil) then
user32.SendMessageA(hwnd, 1024, 0, v.props.value)

end

elseif (v.type==("card")) then
hwnd = user32.CreateWindowExA(0, ("STATIC"), (""), 1342177280, new_node.x, new_node.y, new_node.w, new_node.h, parent, ffi.NULL, hInst, ffi.NULL)

end
if (hwnd~=nil) then
new_node.hwnd = hwnd
local key = tostring(hwnd)
if (v.props.on_mount~=nil) then
v.props.on_mount(hwnd)

end
apply_styles(hwnd, v)
if ((v.type==("button")) and (v.props.on_click~=nil)) then
click_handlers[key] = v.props.on_click

end
if ((((v.type==("input")) or (v.type==("checkbox"))) or (v.type==("slider"))) and (v.props.on_change~=nil)) then
change_handlers[key] = v.props.on_change

end
for child in pairs(new_node.children) do
patch(hwnd, nil, child)


::next_3::
end

end
return new_node

end
new_node.hwnd = old_node.hwnd
local v = new_node.vnode
local hwnd = new_node.hwnd
local key = tostring(hwnd)
if ((((new_node.x~=old_node.x) or (new_node.y~=old_node.y)) or (new_node.w~=old_node.w)) or (new_node.h~=old_node.h)) then
user32.MoveWindow(hwnd, new_node.x, new_node.y, new_node.w, new_node.h, 1)

end
if ((v.props.text~=old_node.vnode.props.text) and (v.type~=("input"))) then
user32.SetWindowTextA(hwnd, v.props.text)

end
if ((v.type==("button")) and (v.props.on_click~=old_node.vnode.props.on_click)) then
click_handlers[key] = v.props.on_click

end
if ((((v.type==("input")) or (v.type==("checkbox"))) or (v.type==("slider"))) and (v.props.on_change~=old_node.vnode.props.on_change)) then
change_handlers[key] = v.props.on_change

end
apply_styles(hwnd, v)
local old_children = old_node.children
local new_children = new_node.children
local n_children = _arr({})
local old_map = _arr({})
for i = 0
, (old_children:len()-1), 1 do
if (old_children[i]~=nil) then
old_map[tostring(old_children[i].vnode.props.key)] = old_children[i]

end


::next_4::
end
for i = 0
, (new_children:len()-1), 1 do
local new_child = new_children[i]
local child_key = tostring(new_child.vnode.props.key)
local old_child = old_map[child_key]
local patched_child = patch(hwnd, old_child, new_child)
if (patched_child~=nil) then
n_children:push(patched_child)
old_map[child_key] = nil

end


::next_5::
end
for k, orphan in pairs(pairs(old_map)) do
patch(hwnd, orphan, nil)


::next_6::
end
new_node.children = n_children
return new_node

end
local function window(title, config)
local width = 500
if (config.width~=nil) then
width = config.width

end
local height = 400
if (config.height~=nil) then
height = config.height

end
local hInstance = kernel32.GetModuleHandleA(ffi.NULL)
local wc = ffi.new(("WNDCLASSEXA"))
wc.cbSize = ffi.sizeof(("WNDCLASSEXA"))
wc.lpfnWndProc = global_wndproc
wc.hInstance = hInstance
wc.hbrBackground = user32.GetSysColorBrush(15)
wc.lpszClassName = ("LimeUIApp")
user32.RegisterClassExA(wc)
local hwnd = user32.CreateWindowExA(0, ("LimeUIApp"), title, 13565952, -2147483648, -2147483648, width, height, ffi.NULL, ffi.NULL, hInstance, ffi.NULL)
local current_tree = nil
watch(function()
local tree = config.render()
local laid = layout(tree, 0, 0, (width-16), (height-39))
current_tree = patch(hwnd, current_tree, laid)

end)
user32.ShowWindow(hwnd, 5)
local msg = ffi.new(("MSG"))
while (user32.GetMessageA(msg, ffi.NULL, 0, 0)>0) do
user32.TranslateMessage(msg)
user32.DispatchMessageA(msg)


::next_7::
end

end

local username = ref((""))
local task_count = ref(0)
local mode = ref(("Greeting"))
window(("LimeUI 2.0 - Advanced App"), _arr({[("width")] = 800, [("height")] = 650, [("render")] = function()
if (mode.value==("Greeting")) then
return column(_arr({[("padding")] = 30, [("spacing")] = 20}), _arr({text(("Welcome to the LimeUI!"), _arr({[("size")] = 24, [("bold")] = true, [("color")] = rgb(40, 100, 200), [("align")] = ("center"), [("height")] = 50})), text(("Enter your name:"), _arr({[("size")] = 16, [("color")] = rgb(80, 80, 80), [("height")] = 30})), input(username.value, function(val)
username.value = val

end, _arr({[("height")] = 40, [("size")] = 18})), column(_arr({[("weight")] = 1}), _arr({})), button(("Start working"), function()
if (username.value~=("")) then
mode.value = ("Tasks")
print(mode.value)

end

end, _arr({[("height")] = 50, [("size")] = 16, [("bold")] = true}))}))

else
return column(_arr({[("padding")] = 15, [("spacing")] = 15}), _arr({row(_arr({[("height")] = 40}), _arr({text(("Рабочий стол"), _arr({[("size")] = 20, [("bold")] = true, [("color")] = rgb(200, 50, 50), [("weight")] = 1})), button(("Выход"), function()
mode.value = ("Приветствие")

end, _arr({[("width")] = 100}))})), text((("Пользователь: ")..username.value), _arr({[("size")] = 16, [("italic")] = true, [("height")] = 25})), row(_arr({[("height")] = 100, [("spacing")] = 10}), _arr({column(_arr({[("weight")] = 1}), _arr({text(("Счетчик задач:"), _arr({[("size")] = 14, [("height")] = 25})), text(task_count.value, _arr({[("size")] = 36, [("bold")] = true, [("color")] = rgb(0, 150, 0), [("align")] = ("center"), [("height")] = 60}))})), column(_arr({[("weight")] = 1, [("padding")] = 0}), _arr({button(("+ Добавить задачу"), function()
task_count.value = (task_count.value+1)

end, _arr({[("height")] = 45})), button(("- Удалить задачу"), function()
if (task_count.value>0) then
task_count.value = (task_count.value-1)

end

end, _arr({[("height")] = 45}))}))})), column(_arr({[("weight")] = 1}), _arr({}))}))

end

end}))
