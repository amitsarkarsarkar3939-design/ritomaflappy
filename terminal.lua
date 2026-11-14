                                   local separator = package.config:sub(1, 1)
local windows = separator == "\\"
local script = arg[0]:match("^(.*[/\\])")

if not script then
    script = ""
end

local function quote_posix(value)
    return "'" .. value:gsub("'", "'\\''") .. "'"
end

local function quote_windows(value)
    return '"' .. value:gsub('"', '\\"') .. '"'
end

local python = os.getenv("PYTHON")
if not python or python == "" then
    python = windows and "python" or "python3"
end

local terminal_path = script .. "terminal.py"
local command
if windows then
    command = quote_windows(python) .. " " .. quote_windows(terminal_path) .. " --cli"
else
    command = quote_posix(python) .. " " .. quote_posix(terminal_path) .. " --cli"
end

local success, reason, code = os.execute(command)
if success == true or success == 0 then
    os.exit(0)
end

if type(code) == "number" then
    os.exit(code)
end

io.stderr:write("The Bix game terminal could not be started")
if reason then
    io.stderr:write(": ", tostring(reason))
end
io.stderr:write(".\n")
os.exit(1)
