-- WARNING: It is LimeLang executing code, so it can be with uncorrected work without lime.exe executing
-- You can run it without parsing with "lime [PATH] --lua"
ffi.cdef([[

    typedef struct _STARTUPINFOA {
        unsigned long cb;
        char* lpReserved;
        char* lpDesktop;
        char* lpTitle;
        unsigned long dwX;
        unsigned long dwY;
        unsigned long dwXSize;
        unsigned long dwYSize;
        unsigned long dwXCountChars;
        unsigned long dwYCountChars;
        unsigned long dwFillAttribute;
        unsigned long dwFlags;
        unsigned short wShowWindow;
        unsigned short cbReserved2;
        unsigned char* lpReserved2;
        void* hStdInput;
        void* hStdOutput;
        void* hStdError;
    } STARTUPINFOA;

    typedef struct _PROCESS_INFORMATION {
        void* hProcess;
        void* hThread;
        unsigned long dwProcessId;
        unsigned long dwThreadId;
    } PROCESS_INFORMATION;

    bool CreateProcessA(
        const char* lpApplicationName,
        char* lpCommandLine,
        void* lpProcessAttributes,
        void* lpThreadAttributes,
        bool bInheritHandles,
        unsigned long dwCreationFlags,
        void* lpEnvironment,
        const char* lpCurrentDirectory,
        STARTUPINFOA* lpStartupInfo,
        PROCESS_INFORMATION* lpProcessInformation
    );

    unsigned long WaitForSingleObject(void* hHandle, unsigned long dwMilliseconds);
    bool CloseHandle(void* hObject);
]])
local kernel32 = ffi.load('C:/Windows/System32/kernel32.dll')
local function run_process(cmd)
local si = ffi.new(("STARTUPINFOA"))
si.cb = ffi.sizeof(si)
local pi = ffi.new(("PROCESS_INFORMATION"))
local cmd_buf = ffi.new(("char[?]"), (cmd:len()+1), cmd)
local success = kernel32.CreateProcessA(ffi.NULL, cmd_buf, ffi.NULL, ffi.NULL, true, 0, ffi.NULL, ffi.NULL, si, pi)
if success then
kernel32.WaitForSingleObject(pi.hProcess, 4294967295)
kernel32.CloseHandle(pi.hProcess)
kernel32.CloseHandle(pi.hThread)
return
true

end
return
false

end

ffi.cdef([[

    typedef size_t (*curl_write_callback)(char *ptr, size_t size, size_t nmemb, void *userdata);
    void* curl_easy_init();
    void curl_easy_cleanup(void* curl);
    int curl_easy_setopt(void* curl, int option, ...);
    int curl_easy_perform(void* curl);
    int curl_easy_getinfo(void* curl, int info, ...);
    const char* curl_version();
    const char* curl_easy_strerror(int code);
    void* curl_slist_append(void* list, const char* str);
    void curl_slist_free_all(void* list);
]])
local curl = ffi.load('C:/Users/ilya2/.lime/libs/nicehttp/libs/libcurl.dll')
local CURLOPT_URL = 10002
local CURLOPT_WRITEFUNCTION = 20011
local CURLOPT_WRITEDATA = 10001
local CURLOPT_FOLLOWLOCATION = 52
local CURLOPT_TIMEOUT = 13
local CURLOPT_POST = 47
local CURLOPT_POSTFIELDS = 10015
local CURLOPT_POSTFIELDSIZE = 60
local CURLOPT_CUSTOMREQUEST = 10036
local CURLOPT_HTTPHEADER = 10023
local CURLOPT_VERBOSE = 41
local CURLINFO_RESPONSE_CODE = 2097154
local _response = ("")
local _headers = _arr({})
local function clong(n)
return ffi.cast(("long"), n)

end
local function cnull()
return ffi.cast(("void*"), 0)

end
local function _write_callback(data, size, nmemb, userdata)
local len = (size*nmemb)
local chunk = ffi.string(data, len)
_response = (_response..chunk)
return len

end
local _write_callback_ptr = ffi.cast(("curl_write_callback"), _write_callback)
local function copt(n)
return ffi.cast(("int"), n)

end
local function clong(n)
return ffi.cast(("long"), n)

end
local function cnull()
return ffi.cast(("void*"), 0)

end
local function _request(method, url, data, headers)
local handle = curl.curl_easy_init()
if (handle==ffi.NULL) then
return _arr({[("error")] = ("curl_easy_init failed"), [("status")] = -1, [("body")] = ("")})

end
curl.curl_easy_setopt(handle, copt(CURLOPT_URL), url)
if (method==("POST")) then
curl.curl_easy_setopt(handle, copt(CURLOPT_POST), clong(1))
if (data~=("")) then
curl.curl_easy_setopt(handle, copt(CURLOPT_POSTFIELDS), data)
curl.curl_easy_setopt(handle, copt(CURLOPT_POSTFIELDSIZE), clong(#data))

end

elseif (((method==("PUT")) or (method==("DELETE"))) or (method==("PATCH"))) then
curl.curl_easy_setopt(handle, copt(CURLOPT_CUSTOMREQUEST), method)
if (data~=("")) then
curl.curl_easy_setopt(handle, copt(CURLOPT_POSTFIELDS), data)

end

end
local header_list = nil
if (headers:size()>0) then
for k, v in pairs(headers) do
local h = ((k..(": "))..v)
header_list = curl.curl_slist_append(header_list, h)


::next_1::
end
if (header_list~=nil) then
curl.curl_easy_setopt(handle, copt(CURLOPT_HTTPHEADER), header_list)

end

end
curl.curl_easy_setopt(handle, copt(CURLOPT_WRITEFUNCTION), _write_callback_ptr)
curl.curl_easy_setopt(handle, copt(CURLOPT_WRITEDATA), cnull())
curl.curl_easy_setopt(handle, copt(CURLOPT_FOLLOWLOCATION), clong(1))
curl.curl_easy_setopt(handle, copt(CURLOPT_TIMEOUT), clong(30))
_response = ("")
local res = curl.curl_easy_perform(handle)
local status = 0
local status_box = ffi.new(("long[1]"))
if (res==0) then
curl.curl_easy_getinfo(handle, copt(CURLINFO_RESPONSE_CODE), ffi.cast(("long*"), status_box))
status = tonumber(ffi.cast(("long&"), status_box))

end
if (header_list~=nil) then
curl.curl_slist_free_all(header_list)

end
curl.curl_easy_cleanup(handle)
if (res==0) then
return _arr({[("status")] = status, [("body")] = _response})

else
local err = ffi.string(curl.curl_easy_strerror(res))
return _arr({[("error")] = err, [("status")] = -1, [("body")] = _response})

end

end
local function get(url, headers)
if (headers==nil) then
headers = _arr({})

end
return _request(("GET"), url, (""), headers)

end
local function post(url, data, headers)
if (headers==nil) then
headers = _arr({})

end
return _request(("POST"), url, data, headers)

end
local function put(url, data, headers)
if (headers==nil) then
headers = _arr({})

end
return _request(("PUT"), url, data, headers)

end
local function delete(url, headers)
if (headers==nil) then
headers = _arr({})

end
return _request(("DELETE"), url, (""), headers)

end
local function patch(url, data, headers)
if (headers==nil) then
headers = _arr({})

end
return _request(("PATCH"), url, data, headers)

end
local function version()
return ffi.string(curl.curl_version())

end

ffi.cdef([[

    int CreateDirectoryA(const char* lpPathName, void* lpSecurityAttributes);
    int RemoveDirectoryA(const char* lpPathName);
    int DeleteFileA(const char* lpFileName);
    void* CreateFileA(const char* path, int access, int share, void* sec, int creation, int flags, void* template);
    int WriteFile(void* handle, const void* buf, int size, void* written, void* overlapped);
    int ReadFile(void* handle, void* buf, int size, void* read, void* overlapped);
    int CloseHandle(void* handle);
    int GetLastError();
    int GetFileSize(void* handle, void* high);
    int GetFileAttributesA(const char* lpFileName);
    int CopyFileA(const char* lpExistingFileName, const char* lpNewFileName, int bFailIfExists);
    int MoveFileA(const char* lpExistingFileName, const char* lpNewFileName);

    // Для обхода директорий
    typedef struct {
        unsigned long dwFileAttributes;
        unsigned long ftCreationTime[2];
        unsigned long ftLastAccessTime[2];
        unsigned long ftLastWriteTime[2];
        unsigned long nFileSizeHigh;
        unsigned long nFileSizeLow;
        unsigned long dwReserved0;
        unsigned long dwReserved1;
        char cFileName[260];
        char cAlternateFileName[14];
    } WIN32_FIND_DATAA;

    void* FindFirstFileA(const char* lpFileName, WIN32_FIND_DATAA* lpFindFileData);
    int FindNextFileA(void* hFindFile, WIN32_FIND_DATAA* lpFindFileData);
    int FindClose(void* hFindFile);
]])
local os_ = ffi.load('C:/Windows/System32/kernel32.dll')
local GENERIC_READ = 2147483648
local GENERIC_WRITE = 1073741824
local CREATE_NEW = 1
local CREATE_ALWAYS = 2
local OPEN_EXISTING = 3
local OPEN_ALWAYS = 4
local TRUNCATE_EXISTING = 5
local FILE_SHARE_READ = 1
local FILE_SHARE_WRITE = 2
local FILE_SHARE_DELETE = 4
local FILE_ATTRIBUTE_NORMAL = 128
local INVALID_FILE_ATTRIBUTES = -1
local FILE_ATTRIBUTE_DIRECTORY = 16
local INVALID_HANDLE_VALUE = ffi.cast(("void*"), -1)
local function mkdir(path)
if (type(path)~=("string")) then
return false

end
return (os_.CreateDirectoryA(path, ffi.cast(("void*"), 0))~=0)

end
local function rmdir(path)
if (type(path)~=("string")) then
return false

end
return (os_.RemoveDirectoryA(path)~=0)

end
local function del(path)
if (type(path)~=("string")) then
return false

end
return (os_.DeleteFileA(path)~=0)

end
local function exists(path)
if (type(path)~=("string")) then
return false

end
local attr = os_.GetFileAttributesA(path)
return (attr~=INVALID_FILE_ATTRIBUTES)

end
local function is_dir(path)
if (type(path)~=("string")) then
return false

end
local attr = os_.GetFileAttributesA(path)
if (attr==INVALID_FILE_ATTRIBUTES) then
return false

end
return ((attr%32)>=16)

end
local function copy(src, dst, overwrite)
if ((type(src)~=("string")) or (type(dst)~=("string"))) then
return false

end
local fail_if_exists = 1
if overwrite then
fail_if_exists = 0

end
return (os_.CopyFileA(src, dst, fail_if_exists)~=0)

end
local function move(src, dst)
if ((type(src)~=("string")) or (type(dst)~=("string"))) then
return false

end
return (os_.MoveFileA(src, dst)~=0)

end
local function write(path, content)
if (type(path)~=("string")) then
return false

end
local handle = os_.CreateFileA(path, GENERIC_WRITE, 0, ffi.cast(("void*"), 0), CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, ffi.cast(("void*"), 0))
if (handle==INVALID_HANDLE_VALUE) then
return false

end
local written = ffi.new(("int[1]"), 0)
local content_str = tostring((content or ("")))
local ok = os_.WriteFile(handle, content_str, #content_str, written, ffi.cast(("void*"), 0))
os_.CloseHandle(handle)
return (ok~=0)

end
local function append(path, content)
if (type(path)~=("string")) then
return false

end
local handle = os_.CreateFileA(path, GENERIC_WRITE, FILE_SHARE_READ, ffi.cast(("void*"), 0), OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, ffi.cast(("void*"), 0))
if (handle==INVALID_HANDLE_VALUE) then
return false

end
local size = os_.GetFileSize(handle, ffi.cast(("void*"), 0))
local written = ffi.new(("int[1]"), 0)
local content_str = tostring((content or ("")))
local ok = os_.WriteFile(handle, content_str, #content_str, written, ffi.cast(("void*"), 0))
os_.CloseHandle(handle)
return (ok~=0)

end
local function read(path)
if (type(path)~=("string")) then
return _arr({[("error")] = -1, [("data")] = ("")})

end
local handle = os_.CreateFileA(path, GENERIC_READ, FILE_SHARE_READ, ffi.cast(("void*"), 0), OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, ffi.cast(("void*"), 0))
if (handle==INVALID_HANDLE_VALUE) then
local err = os_.GetLastError()
return _arr({[("error")] = err, [("data")] = ("")})

end
local size = os_.GetFileSize(handle, ffi.cast(("void*"), 0))
if (size<=0) then
os_.CloseHandle(handle)
return _arr({[("error")] = 0, [("data")] = ("")})

end
local buf = ffi.new(("char[?]"), size)
local bytes_read = ffi.new(("int[1]"), 0)
local ok = os_.ReadFile(handle, buf, size, bytes_read, ffi.cast(("void*"), 0))
os_.CloseHandle(handle)
if (ok==0) then
local err = os_.GetLastError()
return _arr({[("error")] = err, [("data")] = ("")})

end
local data = ffi.string(buf, bytes_read[0 + 1 ])
return _arr({[("error")] = 0, [("data")] = data})

end
local function list(dir_path)
local items = _arr({})
if (type(dir_path)~=("string")) then
return items

end
local search_path = (dir_path..("\\*"))
local find_data = ffi.new(("WIN32_FIND_DATAA"))
local hFind = os_.FindFirstFileA(search_path, find_data)
if (hFind==INVALID_HANDLE_VALUE) then
return items

end
local has_next = 1
while (has_next~=0) do
local name = ffi.string(find_data.cFileName)
if ((name~=(".")) and (name~=(".."))) then
items:add(name)

end
has_next = os_.FindNextFileA(hFind, find_data)


::next_1::
end
os_.FindClose(hFind)
return items

end

os = defpyt(("os"))
local path = os.getcwd()
local github_token = ("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")
ffi.cdef(("void* fopen(const char* path, const char* mode);"))
ffi.cdef(("size_t fwrite(const void* ptr, size_t size, size_t nmemb, void* stream);"))
ffi.cdef(("int fclose(void* stream);"))
local function write_binary(filepath, data)
local f = ffi.C.fopen(filepath, ("wb"))
if (f==ffi.NULL) then
error((("[LPM] Cannot open file for writing: ")..filepath))

end
ffi.C.fwrite(data, 1, #data, f)
ffi.C.fclose(f)

end
local function split(self, sep)
local result = _arr({})
local start = 1
while true do
local pos = string.find(self, sep, start, true)
if (pos==nil) then
result:add(string.sub(self, start))
break

end
result:add(string.sub(self, start, (pos-1)))
start = (pos+#sep)


::next_1::
end
return result

end
local function parse_github_tree_url(url)
local parts = split(url, ("/"))
local owner = parts[3 + 1 ]
local repo = parts[4 + 1 ]
local branch = parts[6 + 1 ]
local pkg_path = ("")
for i = 7
, (parts:len()-1), 1 do
if (pkg_path~=("")) then
pkg_path = (pkg_path..("/"))

end
pkg_path = (pkg_path..parts[i + 1 ])


::next_2::
end
return _arr({[("owner")] = owner, [("repo")] = repo, [("branch")] = branch, [("path")] = pkg_path})

end
local function extract_json_values(body, key)
local result = _arr({})
local search = ((("\"")..key)..("\""))
local start = 1
while true do
local pos = string.find(body, search, start, true)
if (pos==nil) then
break

end
local i = (pos+#search)
while true do
local ch = string.sub(body, i, i)
if (ch==(":")) then
i = (i+1)
break

end
if ((((ch~=(" ")) and (ch~=("\t"))) and (ch~=("\n"))) and (ch~=("\r"))) then
break

end
i = (i+1)


::next_4::
end
while true do
local ch = string.sub(body, i, i)
if ((((ch~=(" ")) and (ch~=("\t"))) and (ch~=("\n"))) and (ch~=("\r"))) then
break

end
i = (i+1)


::next_5::
end
if (string.sub(body, i, i)==("\"")) then
i = (i+1)
local val_end = string.find(body, ("\""), i, true)
if (val_end~=nil) then
result:add(string.sub(body, i, (val_end-1)))
start = (val_end+1)

else
break

end

else
start = (pos+#search)

end


::next_3::
end
return result

end
local function parse_entries(body)
local names = extract_json_values(body, ("name"))
local types = extract_json_values(body, ("type"))
local result = _arr({})
local n = names:len()
for i = 0
, (n-1), 1 do
if (i<types:len()) then
result:add(_arr({[("name")] = names[i + 1 ], [("type")] = types[i + 1 ]}))

end


::next_6::
end
return result

end
local function install_sub_libs(owner, repo, branch, pkg_path)
local api_url = ((((((((("https://api.github.com/repos/")..owner)..("/"))..repo)..("/contents/"))..pkg_path)..("/libs"))..("?ref="))..branch)
print((("[LPM] Checking: ")..api_url))
local headers = _arr({[("User-Agent")] = ("LimeLPM")})
if (github_token~=("")) then
headers[("Authorization")] = (("Bearer ")..github_token)
print(("[LPM] Using GitHub token for API request"))

end
local response = get(api_url, headers)
if (response.status~=200) then
print(((("[LPM] No libs/ folder (HTTP ")..response.status)..(")")))
return nil

end
local entries = parse_entries(response.body)
local total = entries:len()
if (total==0) then
print(("[LPM] libs/ is empty"))
return nil

end
print(((("[LPM] Found ")..total)..(" item(s) in libs/")))
for i = 0
, (total-1), 1 do
local entry = entries[i + 1 ]
local name = entry.name
local typ = entry.type
if (typ==("dir")) then
local sub_url = (((((((((("https://github.com/")..owner)..("/"))..repo)..("/tree/"))..branch)..("/"))..pkg_path)..("/libs/"))..name)
print((("[LPM] Sub-library: ")..name))
install_package(sub_url)

elseif (typ==("file")) then
local file_url = (((((((((("https://raw.githubusercontent.com/")..owner)..("/"))..repo)..("/"))..branch)..("/"))..pkg_path)..("/libs/"))..name)
local file_resp = get(file_url)
if (file_resp.status==200) then
local dest = (("./libs/")..name)
write(dest, file_resp.body)
print((("[LPM] Downloaded: ")..name))

else
print((("[LPM] Warning: failed to download ")..name))

end

end


::next_7::
end

end
local cmds = _arr({})
local last_cmd = ("")
local l_args = _arr({})
for i in pairs(args) do
if i:startswith(("--")) then
if (last_cmd~=("")) then
cmds:add(_arr({[("name")] = last_cmd, [("args")] = l_args}))

end
last_cmd = i
l_args = _arr({})

else
l_args:add(i)

end


::next_8::
end
if (last_cmd~=("")) then
cmds:add(_arr({[("name")] = last_cmd, [("args")] = l_args}))

end
local function add_dependency_to_config(pkg_name)
if exists(("./lime.toml")) then
local content = read(("./lime.toml"))[("data") ]
if  not content:contains(pkg_name) then
local updated = (((content..("\n"))..pkg_name)..(" = \"latest\""))
write(("./lime.toml"), updated)
print((("[LPM] Updated lime.toml with ")..pkg_name))

end

end

end
local function install_package(pkg_name)
print(((("[LPM] Installing ")..pkg_name)..("...")))
if  not exists(("./libs")) then
mkdir(("./libs"))

end
local clean_name = split(pkg_name, ("/")):last()
local pkg_dir = (("./libs/")..clean_name)
if (pkg_name:contains(("github.com")) and pkg_name:contains(("/tree/"))) then
local info = parse_github_tree_url(pkg_name)
local download_url = ((((((((("https://raw.githubusercontent.com/")..info.owner)..("/"))..info.repo)..("/"))..info.branch)..("/"))..info.path)..("/setup.lm"))
local headers = _arr({[("User-Agent")] = ("LimeLPM")})
if (github_token~=("")) then
headers[("Authorization")] = (("Bearer ")..github_token)
print(("[LPM] Using GitHub token for API request"))

end
local response = get(download_url, headers)
if (response.status==200) then
if  not exists(pkg_dir) then
mkdir(pkg_dir)

end
local target_path = (pkg_dir..("/setup.lm"))
write(target_path, response.body)
print((((("[LPM] Successfully installed ")..clean_name)..(" to "))..target_path))
add_dependency_to_config(pkg_name)
install_sub_libs(info.owner, info.repo, info.branch, info.path)

else
error((("[LPM] Failed to download 'setup.lm'. HTTP Status: ")..response.status))

end

elseif ((pkg_name:contains(("/")) and  not pkg_name:startswith(("http"))) or pkg_name:endswith((".zip"))) then
local download_url = ("")
if pkg_name:endswith((".zip")) then
download_url = pkg_name

else
download_url = ((("https://github.com/")..pkg_name)..("/archive/refs/heads/main.zip"))

end
local temp_zip = ((("./libs/temp_")..clean_name)..(".zip"))
local response = get(download_url)
if (response.status==200) then
write_binary(temp_zip, response.body)
local zipfile = defpyt(("zipfile"))
local shutil = defpyt(("shutil"))
local zip_ref = zipfile.ZipFile(temp_zip, ("r"))
local temp_extract_path = (("./libs/temp_ext_")..clean_name)
zip_ref.extractall(temp_extract_path)
zip_ref.close()
os.remove(temp_zip)
local extracted_folders = os.listdir(temp_extract_path)
if (#extracted_folders>0) then
local inner_folder = ((temp_extract_path..("/"))..extracted_folders[0 + 1 ])
if exists(pkg_dir) then
shutil.rmtree(pkg_dir)

end
shutil.move(inner_folder, pkg_dir)
shutil.rmtree(temp_extract_path)

end
print((("[LPM] Successfully extracted package to ")..pkg_dir))
add_dependency_to_config(pkg_name)

else
error((("[LPM] Failed to download ZIP. HTTP Status: ")..response.status))

end

else
local response = get(pkg_name)
if (response.status==200) then
local target_path = (("./libs/")..clean_name)
if  not target_path:endswith((".lm")) then
target_path = (target_path..(".lm"))

end
write(target_path, response.body)
print((("[LPM] Successfully installed to ")..target_path))
add_dependency_to_config(pkg_name)

else
error((("[LPM] Failed to download package. HTTP Status: ")..response.status))

end

end

end
for i in pairs(cmds) do
if (i.name==("--run")) then
run_process(((("lime.exe ")..path)..(" --notime")))

elseif (i.name==("--init")) then
if  not exists(("./libs")) then
mkdir(("./libs"))

end
write(("./main.lm"), ("print('Hello, World!')"))
local dir_name = split(os.getcwd(), ("\\")):last()
write(("./lime.toml"), ((((("name = \"")..dir_name)..("\"\n"))..("description = \"New project on LimeLang\"\n\n"))..("[dependencies]\n")))
print(("[LPM] Project initialized!"))

elseif (i.name==("--install")) then
if (i.args:len()>0) then
local pkg = i.args[0 + 1 ]
install_package(pkg)

else
print(("[LPM] Installing dependencies from lime.toml..."))
if exists(("./lime.toml")) then
local config = read(("./lime.toml"))
print(("[LPM] All dependencies up to date."))

else
error(("[LPM] lime.toml not found. Run 'lpm --init' first."))

end

end

end


::next_9::
end
