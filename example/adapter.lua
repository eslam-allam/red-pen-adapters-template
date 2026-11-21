-- Example adapter for the Red Pen registry template.
-- It reads the submitted file inside the sandbox, counts non-empty lines,
-- and compares the count with the instructor's key answer.
--
-- API v2 runtime rule: when a manifest declares a managed runtime, its tool is
-- manifest.runtimes[1].tool. The legacy manifest.language and manifest.miseTool
-- hints no longer exist. This example has no runtime, so it uses none.
--
-- Every run ends with exactly one app.result call and an explicit status:
-- graded, previewed, declined, failed or timeout. A failure, timeout or
-- decline must never return score = 0, because the app would record that as a
-- wrong answer instead of leaving the question for manual marking.
local context = request.context or {}
local values = context.values or {}
local expected = tonumber(values.expectedLines or context.expected or "")
local max_points = tonumber(context.maxPoints) or 0

local function text_or_empty(value)
  if value == nil then return "" end
  return tostring(value)
end

local function decline(code, message, detail)
  app.result({
    status = "declined",
    code = code,
    message = message,
    detail = text_or_empty(detail),
  })
end

local function fail(code, message, detail)
  app.result({
    status = "failed",
    code = code,
    message = message,
    detail = text_or_empty(detail),
  })
end

local file = request.filePath
if type(file) ~= "string" or file == "" then
  decline("missing-input", "There is no submitted file to read.")
  return
end

local ok, content = pcall(app.read_file, file)
if not ok then
  fail("read-error", "The submitted file could not be read.", content)
  return
end

local lines = 0
for _ in (content or ""):gmatch("[^\r\n]+") do
  lines = lines + 1
end

if request.mode == "preview" then
  app.result({
    status = "previewed",
    text = "The file has " .. lines .. " non-empty line(s).",
  })
  return
end

if expected == nil then
  decline(
    "missing-key",
    "The key has no expected line count.",
    "Set the Expected non-empty lines key field."
  )
  return
end

local same = lines == expected
app.result({
  status = "graded",
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
