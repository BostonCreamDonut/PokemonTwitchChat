-- Load this in mGBA: Tools -> Scripting -> Load Script.
-- It connects to auto_game_state.py and sends FireRed state once per second.

local socketOk, socket = pcall(require, "socket")
if not socketOk then
    console:error("LuaSocket is not available in this mGBA build. Auto game-state bridge cannot start.")
    return
end

local HOST = "127.0.0.1"
local PORT = 8765
local SEND_EVERY_FRAMES = 60

-- Pokemon FireRed US v1.0 symbols from pret/pokefirered.
local SAVE_BLOCK_1 = 0x0202552C
local OFFSET_LOCATION = 0x0004
local OFFSET_PARTY_COUNT = 0x0034
local OFFSET_BADGE_FLAGS_BYTE = 0x0FE4

local client = nil
local frame = 0
local lastPayload = ""

local function connect()
    if client then
        return true
    end
    local tcp = socket.tcp()
    tcp:settimeout(0.05)
    local ok = tcp:connect(HOST, PORT)
    if ok then
        tcp:settimeout(0)
        client = tcp
        return true
    end
    tcp:close()
    return false
end

local function read8(addr)
    return emu:read8(addr)
end

local function badgeCount()
    local byte = read8(SAVE_BLOCK_1 + OFFSET_BADGE_FLAGS_BYTE)
    local count = 0
    for bit = 0, 7 do
        if math.floor(byte / (2 ^ bit)) % 2 == 1 then
            count = count + 1
        end
    end
    return count
end

local function payload()
    local mapGroup = read8(SAVE_BLOCK_1 + OFFSET_LOCATION)
    local mapNum = read8(SAVE_BLOCK_1 + OFFSET_LOCATION + 1)
    local partySize = read8(SAVE_BLOCK_1 + OFFSET_PARTY_COUNT)
    local badges = badgeCount()
    return string.format(
        '{"map_group":%d,"map_num":%d,"party_size":%d,"badges":%d}\n',
        mapGroup, mapNum, partySize, badges
    )
end

local function sendState()
    if not connect() or not client then
        return
    end
    local text = payload()
    if text == lastPayload then
        return
    end
    lastPayload = text
    local ok = client:send(text)
    if not ok then
        client:close()
        client = nil
    end
end

callbacks:add("frame", function()
    frame = frame + 1
    if frame % SEND_EVERY_FRAMES == 0 then
        sendState()
    end
end)

console:log("FireRed state bridge loaded. Start the Python app, then keep this script running.")
