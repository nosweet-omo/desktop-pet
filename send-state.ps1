# 桌宠状态切换工具
# 用法: powershell -File send-state.ps1 <状态名>
# 例如: powershell -File send-state.ps1 thinking

param([string]$state = "idle")

$states = @(
  "idle", "thinking", "working", "done",
  "problem", "study", "tired", "cheer",
  "rest", "error", "loading", "bye"
)

$labels = @{
  "idle" = "空闲/待机";
  "thinking" = "思考中";
  "working" = "工作中";
  "done" = "完成啦";
  "problem" = "遇到问题";
  "study" = "学习中";
  "tired" = "有点累了";
  "cheer" = "加油";
  "rest" = "休息一下";
  "error" = "出错了";
  "loading" = "加载中";
  "bye" = "拜拜";
}

if ($states -notcontains $state) {
  Write-Host "未知状态: $state"
  Write-Host "可用状态: $($states -join ', ')"
  exit 1
}

$body = @{ state = $state } | ConvertTo-Json

try {
  $response = Invoke-RestMethod -Uri "http://127.0.0.1:9527/state" -Method POST -Body $body -ContentType "application/json"
  Write-Host "桌宠状态已切换: $($labels[$state]) ($state)"
} catch {
  Write-Host "切换失败，请确认桌宠应用正在运行"
}
