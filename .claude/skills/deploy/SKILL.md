# Skill: deploy

Push the current branch to GitHub to trigger a Render.com auto-deploy.

## Steps
1. Run `git status` — confirm there are no untracked sensitive files (.env, credentials)
2. Stage only relevant changed files (never git add -A blindly)
3. Ask user for a commit message if not provided
4. Commit with the message
5. Push to branch `claude/initial-setup-JhDmH`
6. Confirm push succeeded and remind user that Render auto-deploys on push

## Rules
- Never push .env or any file containing API keys
- Always confirm with user before pushing
- Never use --no-verify or --force
