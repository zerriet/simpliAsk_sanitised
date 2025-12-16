# PowerShell script to push to simpliask_sanitised repository
# Replace YOUR_USERNAME with your GitHub username before running

Write-Host "Step 1: Adding .env.conf removal to staging..." -ForegroundColor Cyan
git add .gitignore

Write-Host "`nStep 2: Committing .gitignore changes..." -ForegroundColor Cyan
git commit -m "Add .env.conf to .gitignore and remove from tracking"

Write-Host "`nStep 3: Adding new remote repository..." -ForegroundColor Cyan
Write-Host "NOTE: Replace YOUR_USERNAME with your actual GitHub username!" -ForegroundColor Yellow
# Uncomment and modify the line below:
# git remote add sanitised https://github.com/YOUR_USERNAME/simpliask_sanitised.git

Write-Host "`nStep 4: Verify the new remote was added:" -ForegroundColor Cyan
Write-Host "Run: git remote -v" -ForegroundColor Yellow

Write-Host "`nStep 5: Push to the new repository:" -ForegroundColor Cyan
Write-Host "Run: git push sanitised smol_agent_auditEventBus:main" -ForegroundColor Yellow
Write-Host "Or to push all branches: git push sanitised --all" -ForegroundColor Yellow

Write-Host "`nIMPORTANT: Make sure the repository 'simpliask_sanitised' exists on GitHub before pushing!" -ForegroundColor Red

