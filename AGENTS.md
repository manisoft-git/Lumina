# Antigravity Git Synchronization Protocol

## MANDATORY WORKFLOW FOR ALL SESSIONS
The operator (Manifest Subeno) actively works across multiple concurrent Antigravity environments (the Mission Control Web Panel and the CLI Terminal).
To prevent merge conflicts, race conditions, or out-of-sync states across sessions, EVERY Antigravity agent operating in this workspace MUST follow this two-phase synchronization protocol:

### Phase 1: Always Pull Before Making Changes
Before inspecting existing code to make changes, modifying any file, creating new files, or running build/refactor tasks in any project repository:
1. Navigate to the repository root for that project.
2. If there are untracked or unstaged working changes, stage/commit them or stash them (`git stash`).
3. Run `git pull --rebase origin main` (or the active working branch) to pull in any latest commits made from the other panel or session.
4. If changes were stashed, reapply them with `git stash pop`.
5. Only then proceed with reading, editing, or creating files.

### Phase 2: Always Commit and Push Immediately After Changes
As soon as code modifications, fixes, or features are implemented and verified:
1. Check repository status: `git status`.
2. Stage modified and created files: `git add <files>`.
3. Create a clean, conventional commit: `git commit -m "<type>(<scope>): <concise description>"`.
4. Immediately push the commit to GitHub: `git push origin <branch>`.
5. Report the commit hash and sync status to the user.

NEVER skip pulling before starting changes.
NEVER finish a turn leaving uncommitted or unpushed modifications in any repository.

# Standard Form Field Placeholders Protocol

## MANDATORY PLACEHOLDERS ACROSS ALL PROJECTS (NOW AND FUTURE)
Whenever form inputs for user accounts, registration, login, profile editing, guest inputs, or identity information are implemented or modified in ANY project, agents MUST ALWAYS use these standardized placeholders:
- **Username**: 'tobiolive5850'
- **Surname**: 'Tobi'
- **Firstname**: 'Olive'
- **Full Name (Surname Firstname)**: 'Tobi Olive' (or 'Surname Firstname (e.g. Tobi Olive)' where format guidance is needed)
- **Email**: 'tobi585olive@gmail.com'
