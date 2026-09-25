# Work•Sleep•Repeat — Rules for Claude Code

## Project
Computer Graphics Sessional final project. Python + PyOpenGL + GLUT pixel-art app.
All specs live in docs/: prd.md, design.md, techspec.md, appflow.md, plan.md, tracker.md.

## Always
- Read the docs sections named in the prompt before writing code.
- Follow docs/techspec.md exactly: module names, function signatures, dependency direction.
- Every number and color comes from config.py. Never hardcode a hex code or coordinate elsewhere.
- Every function (and every important block) gets this Bangla comment block:
  # কী করছে: ...
  # কেন লাগছে: ...
  # real world-এ এটা কোথায় দেখা যায়: ...
- CG algorithms in algorithms.py are written by hand. No library does the algorithm.
- Keep code simple and readable. The student must explain every line in a viva.
- Only do the current phase. Do not build ahead.
- Never use `git add -A` or `git add .`. Stage files explicitly by name. Before every commit,
  show `git status` and stop if any file is unexpectedly deleted or modified.

## When something is wrong
- Diagnose first: explain the cause before changing code.
- No blind fixes or workarounds. If blocked (e.g. freeglut missing), stop and explain.

## After finishing a phase
- Run the verification steps from the prompt and report each result.
- Update docs/tracker.md: tick completed tasks, set the phase status.
- Summarize every function you wrote in simple language.