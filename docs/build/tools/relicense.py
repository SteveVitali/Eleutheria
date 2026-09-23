import subprocess, sys
OLD_HASH = (
"# SPDX-License-Identifier: LicenseRef-SIG-Undetermined\n"
"# Copyright (C) 2026 The SIG project. Licence posture is a placeholder; final\n"
"# licences are decided in P00.2 (see LICENSE and docs/2_canonical_design_spec.md \u00a742).\n"
)
NEW_HASH = (
"# SPDX-License-Identifier: Apache-2.0\n"
"# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation\n"
"# carry per-artifact licences \u2014 see LICENSE and docs/2_canonical_design_spec.md \u00a742.\n"
)
OLD_SLASH = OLD_HASH.replace("# ", "// ")
NEW_SLASH = NEW_HASH.replace("# ", "// ")
files = subprocess.run(["git","ls-files"],capture_output=True,text=True).stdout.split()
skip = {"LICENSE","web/package.json"}
changed=[]
for f in files:
    if f in skip: continue
    try:
        t=open(f,encoding="utf-8").read()
    except (UnicodeDecodeError,IsADirectoryError):
        continue
    n=t
    if OLD_HASH in n: n=n.replace(OLD_HASH,NEW_HASH)
    if OLD_SLASH in n: n=n.replace(OLD_SLASH,NEW_SLASH)
    if n!=t:
        open(f,"w",encoding="utf-8").write(n); changed.append(f)
print(f"changed {len(changed)} files")
