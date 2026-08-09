-- Load this in mGBA: Tools -> Scripting -> File -> Load script.
-- It connects to auto_game_state.py and sends FireRed state about once per second.

local HOST = "127.0.0.1"
local PORT = 8765
local SEND_EVERY_FRAMES = 60
local RECONNECT_EVERY_FRAMES = 180

-- Pokemon FireRed US v1.0 symbols from pret/pokefirered.
local SAVE_BLOCK_1 = 0x0202552C
local OFFSET_LOCATION = 0x0004
local OFFSET_PARTY_COUNT = 0x0034
local OFFSET_BADGE_FLAGS_BYTE = 0x0FE4

local client = nil
local frame = 0
local lastPayload = ""
local lastConnectAttempt = -RECONNECT_EVERY_FRAMES

local buffer = console:createBuffer("TPP Bridge")
buffer:setSize(48, 8)

local function status(line1, line2, line3)
    buffer:clear()
    buffer:moveCursor(0, 0)
    buffer:print("Twitch Plays Pokemon state bridge\n")
    buffer:print((line1 or "") .. "\n")
    buffer:print((line2 or "") .. "\n")
    buffer:print((line3 or "") .. "\n")
end

local function connectBridge()
    if client then
        return true
    end
    if frame - lastConnectAttempt < RECONNECT_EVERY_FRAMES then
        return false
    end
    lastConnectAttempt = frame

    if not socket or not socket.connect then
        status("mGBA socket API is unavailable.", "Use mGBA 0.10+ desktop build.", "")
        return false
    end

    status("Connecting to Python bridge...", HOST .. ":" .. PORT, "Start ./run.sh before loading this script.")
    local ok, result, err = pcall(socket.connect, HOST, PORT)
    if ok and result then
        client = result
        status("Connected.", "Waiting for game memory...", "")
        return true
    end

    status("Not connected yet.", "Start ./run.sh, then wait a few seconds.", tostring(err or result or "connection failed"))
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

local function makePayload()
    if not emu then
        return nil, "No ROM/core loaded yet."
    end
    local ok, textOrErr = pcall(function()
        local mapGroup = read8(SAVE_BLOCK_1 + OFFSET_LOCATION)
        local mapNum = read8(SAVE_BLOCK_1 + OFFSET_LOCATION + 1)
        local partySize = read8(SAVE_BLOCK_1 + OFFSET_PARTY_COUNT)
        local badges = badgeCount()
        return string.format(
            '{"map_group":%d,"map_num":%d,"party_size":%d,"badges":%d}\n',
            mapGroup, mapNum, partySize, badges
        )
    end)
    if ok then
        return textOrErr, nil
    end
    return nil, textOrErr
end

local function sendState()
    if not connectBridge() or not client then
        return
    end

    local text, err = makePayload()
    if not text then
        status("Waiting for readable FireRed memory.", tostring(err), "")
        return
    end
    if text == lastPayload then
        return
    end
    lastPayload = text

    local ok, sentOrErr = pcall(function()
        return client:send(text)
    end)
    if not ok or not sentOrErr then
        if client then
            pcall(function() client:close() end)
        end
        client = nil
        status("Disconnected from Python bridge.", "Will retry automatically.", tostring(sentOrErr))
        return
    end

    status("Connected and sending.", text:gsub("\n", ""), "")
end

callbacks:add("frame", function()
    frame = frame + 1
    if frame % SEND_EVERY_FRAMES == 0 then
        sendState()
    end
end)

status("Script loaded.", "Start ./run.sh if it is not already running.", "The bridge will retry automatically.")
console:log("Twitch Plays Pokemon FireRed state bridge loaded.")
