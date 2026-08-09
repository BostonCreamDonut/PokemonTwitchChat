-- Load this first in mGBA to verify the scripting window actually runs scripts.
-- It does not use sockets or Pokemon memory.

local buffer = console:createBuffer("TPP Smoke Test")
buffer:setSize(52, 8)

local frame = 0

local function draw(message)
    buffer:clear()
    buffer:moveCursor(0, 0)
    buffer:print("TPP scripting smoke test\n")
    buffer:print(message .. "\n")
    buffer:print("If this number changes, scripts are running:\n")
    buffer:print(tostring(frame) .. "\n")
end

draw("Loaded successfully.")
console:log("TPP smoke test loaded.")

callbacks:add("frame", function()
    frame = frame + 1
    if frame % 60 == 0 then
        draw("Running.")
    end
end)
