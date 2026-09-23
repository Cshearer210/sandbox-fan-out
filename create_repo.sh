#!/bin/bash
set -o pipefail
cd /home/noredfarms/corral-work || exit 1
export GH_TOKEN="$(cat ~/Tools/.gh_token 2>/dev/null)"
python3 -m unittest discover -s tests -q 2>&1 | tail -2
git init -q 2>/dev/null
git add -A
git -c user.name="Chris Shearer" -c user.email="cshearer210@gmail.com" commit -q -m "corral: fan test agents over a sandbox in isolation, merge results safely

Each agent clones only its slice's parts, tests in a private workdir, writes its OWN per-agent log,
and destroys its clone; a single merge step folds every log into one successes/failures pair after
the fan-out -- so no two agents ever write the same file and the shared results are written once.
Proven under real thread concurrency: disjoint/complete/balanced slices, isolation, exactly-once
merge across 16 agents over 200 units, no shared write during the run, a raising unit becomes a
logged failure, repeated runs never lose or corrupt. 7 tests, a rot-proof demo, a demo SVG."
gh repo create noredfarms/corral --private --source . --remote origin --push 2>&1 | tail -4
echo DONE
