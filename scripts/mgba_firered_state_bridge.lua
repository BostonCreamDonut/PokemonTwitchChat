-- Load this in mGBA: Tools -> Scripting -> File -> Load script.
-- It connects to auto_game_state.py and sends FireRed state about once per second.

local HOST = "127.0.0.1"
local PORT = 8765
local SEND_EVERY_FRAMES = 60
local RECONNECT_EVERY_FRAMES = 180

-- Pokemon FireRed US v1.0 symbols from pret/pokefirered.
local SAVE_BLOCK_1 = 0x0202552C
local SAVE_BLOCK_1_PTR = 0x03005008
local PLAYER_PARTY_COUNT = 0x02024029
local PLAYER_PARTY = 0x02024284
local OFFSET_LOCATION = 0x0004
local OFFSET_PARTY_COUNT = 0x0034
local OFFSET_BADGE_FLAGS_BYTE = 0x0FE4
local PARTY_MON_SIZE = 100
local PARTY_MON_PERSONALITY_OFFSET = 0x00
local PARTY_MON_OTID_OFFSET = 0x04
local PARTY_MON_DATA_OFFSET = 0x20
local PARTY_MON_HP_OFFSET = 0x56

local SUBSTRUCT_ORDERS = {
    {0, 1, 2, 3}, {0, 1, 3, 2}, {0, 2, 1, 3}, {0, 2, 3, 1},
    {0, 3, 1, 2}, {0, 3, 2, 1}, {1, 0, 2, 3}, {1, 0, 3, 2},
    {1, 2, 0, 3}, {1, 2, 3, 0}, {1, 3, 0, 2}, {1, 3, 2, 0},
    {2, 0, 1, 3}, {2, 0, 3, 1}, {2, 1, 0, 3}, {2, 1, 3, 0},
    {2, 3, 0, 1}, {2, 3, 1, 0}, {3, 0, 1, 2}, {3, 0, 2, 1},
    {3, 1, 0, 2}, {3, 1, 2, 0}, {3, 2, 0, 1}, {3, 2, 1, 0},
}

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

local function read32(addr)
    return read8(addr)
        + read8(addr + 1) * 0x100
        + read8(addr + 2) * 0x10000
        + read8(addr + 3) * 0x1000000
end

local function read16(addr)
    return read8(addr) + read8(addr + 1) * 0x100
end

local function saneSaveBlockAddress(addr)
    return addr and addr >= 0x02000000 and addr < 0x02040000
end

local function badgeCount(saveBlock)
    local byte = read8(saveBlock + OFFSET_BADGE_FLAGS_BYTE)
    local count = 0
    for bit = 0, 7 do
        if math.floor(byte / (2 ^ bit)) % 2 == 1 then
            count = count + 1
        end
    end
    return count
end

local function partyHpJson(partySize)
    local parts = {}
    local count = math.max(0, math.min(6, partySize))
    for i = 0, count - 1 do
        parts[#parts + 1] = tostring(read16(PLAYER_PARTY + i * PARTY_MON_SIZE + PARTY_MON_HP_OFFSET))
    end
    return "[" .. table.concat(parts, ",") .. "]"
end

local function growthSlot(personality)
    local order = SUBSTRUCT_ORDERS[(personality % 24) + 1]
    for slot = 1, 4 do
        if order[slot] == 0 then
            return slot - 1
        end
    end
    return 0
end

local function partySpeciesJson(partySize)
    local parts = {}
    local count = math.max(0, math.min(6, partySize))
    for i = 0, count - 1 do
        local base = PLAYER_PARTY + i * PARTY_MON_SIZE
        local personality = read32(base + PARTY_MON_PERSONALITY_OFFSET)
        local otId = read32(base + PARTY_MON_OTID_OFFSET)
        local key = personality ~ otId
        local slot = growthSlot(personality)
        local encrypted = read32(base + PARTY_MON_DATA_OFFSET + slot * 12)
        local decrypted = encrypted ~ key
        local species = decrypted % 0x10000
        parts[#parts + 1] = tostring(species)
    end
    return "[" .. table.concat(parts, ",") .. "]"
end

local function makePayload()
    if not emu then
        return nil, "No ROM/core loaded yet."
    end
    local ok, textOrErr = pcall(function()
        local ptr = read32(SAVE_BLOCK_1_PTR)
        local ptrValid = saneSaveBlockAddress(ptr)
        local ptrSaveBlock = ptrValid and ptr or SAVE_BLOCK_1

        local fixedMapGroup = read8(SAVE_BLOCK_1 + OFFSET_LOCATION)
        local fixedMapNum = read8(SAVE_BLOCK_1 + OFFSET_LOCATION + 1)
        local ptrMapGroup = read8(ptrSaveBlock + OFFSET_LOCATION)
        local ptrMapNum = read8(ptrSaveBlock + OFFSET_LOCATION + 1)
        local ptrPartySize = read8(ptrSaveBlock + OFFSET_PARTY_COUNT)
        local fixedPartySize = read8(SAVE_BLOCK_1 + OFFSET_PARTY_COUNT)
        local globalPartySize = read8(PLAYER_PARTY_COUNT)
        local partySize = globalPartySize
        if partySize < 0 or partySize > 6 then
            partySize = ptrPartySize
        end
        if partySize < 0 or partySize > 6 then
            partySize = 0
        end
        local partyHp = partyHpJson(partySize)
        local partySpecies = partySpeciesJson(partySize)
        local badges = badgeCount(ptrSaveBlock)
        return string.format(
            '{"map_group":%d,"map_num":%d,"fixed_map_group":%d,"fixed_map_num":%d,"ptr_map_group":%d,"ptr_map_num":%d,"save_block1_ptr":%d,"party_size":%d,"global_party_size":%d,"ptr_party_size":%d,"fixed_party_size":%d,"party_hp":%s,"party_species":%s,"badges":%d}\n',
            ptrMapGroup, ptrMapNum, fixedMapGroup, fixedMapNum, ptrMapGroup, ptrMapNum, ptr, partySize, globalPartySize, ptrPartySize, fixedPartySize, partyHp, partySpecies, badges
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
