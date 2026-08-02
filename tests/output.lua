-- WARNING: It is LimeLang executing code, so it can be with uncorrected work without lime.exe executing
-- You can run it without parsing with "lime [PATH] --lua"
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
local curl = ffi.load('C:/Users/ilya2/PycharmProjects/LimeLuaJIT/libs/nicehttp/libs/libcurl.dll')
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

local post_data = ("name=LIME&age=123&city=Somewhere")
local post_headers = _arr({[("Content-Type")] = ("application/x-www-form-urlencoded")})
res = post(("https://httpbin.org/post"), post_data, post_headers)
print(("Status:"), res[("status")])
if (res[("status")]==200) then
print(("Body:"), res[("body")])

else
print(("Error:"), res[("error")])

end
