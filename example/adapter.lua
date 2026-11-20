-- Example adapter for the Red Pen registry template.
-- It reads the submitted file inside the sandbox, counts non-empty lines,
-- and compares the count with the instructor's key answer.
local context = request.context or {}
local values = context.values or {}
local expected = tonumber(values.expectedLines or context.expected or "")
local max_points = tonumber(context.maxPoints) or 0

local ok, content = pcall(app.read_file, request.filePath)
if not ok then
  app.result({
    score = 0,
    comment = "The file could not be read.",
    rationale = "app.read_file failed inside the sandbox.",
  })
  return
end

local lines = 0
for _ in (content or ""):gmatch("[^\r\n]+") do
  lines = lines + 1
end

if request.mode == "preview" then
  app.result({
    text = "The file has " .. lines .. " non-empty line(s).",
    rationale = "Example preview.",
  })
  return
end

if expected == nil then
  app.result({
    score = 0,
    comment = "The key has no expected line count.",
    rationale = "Set the Expected non-empty lines key field.",
  })
  return
end

local same = lines == expected
app.result({
  score = same and max_points or 0,
  comment = same
    and "The number of non-empty lines matches the expected answer."
    or "The number of non-empty lines does not match the expected answer.",
  rationale = same and "Line count matched the key." or "Line count differed from the key.",
  text = "The file has " .. lines .. " non-empty line(s).",
  output = {
    kind = "diff",
    title = "Line count",
    expected = tostring(expected),
    actual = tostring(lines),
    expectedLabel = "Expected",
    actualLabel = "Actual",
  },
})
