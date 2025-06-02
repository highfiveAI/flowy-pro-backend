import sys
import os

if len(sys.argv) < 2:
    print("사용법: python post_revision_fix.py <revision_file_path>")
    sys.exit(1)

revision_path = sys.argv[1]

import_line = "from pgvector.sqlalchemy import Vector\n"

with open(revision_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# 이미 import 되어 있지 않다면 삽입
if import_line not in lines:
    # import 문 바로 아래에 삽입
    for i, line in enumerate(lines):
        if line.startswith("from alembic import op"):
            lines.insert(i + 1, import_line)
            break

    with open(revision_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print("✅ Vector import 삽입 완료")
else:
    print("ℹ️ 이미 Vector import 있음")
