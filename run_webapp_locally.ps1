Write-Host "Starting development servers..." -ForegroundColor Green

Write-Host "Opening database proxy in new window..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& {flyctl proxy 15432:5432 -a small-night-2462}"

Write-Host "Opening backend server in new window..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& {.\venv\Scripts\Activate.ps1; cd backend; python -m uvicorn entrypoints.backend:app --reload}"

Write-Host "Opening frontend server in new window..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& {cd .\frontend\; npm start}"

Write-Host "Both servers are starting in separate windows." -ForegroundColor Green
Write-Host "Press any key to exit this script..." -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
