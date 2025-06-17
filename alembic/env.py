from logging.config import fileConfig
import asyncio # 새로 추가: asyncio 임포트
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import AsyncEngine # 새로 추가: AsyncEngine 임포트
from alembic import context

from app.models.base import Base
from app.models import (
    flowy_user, company_position, interdoc, profile_img, signup_log,
    sysrole, company, admin, meeting_user, meeting, project_user,
    project, role, summary_log, task_assign_log, draft_log,
    feedback, feedbacktype, prompt_log, calendar
)

from pgvector.sqlalchemy import Vector
from sqlalchemy.ext.compiler import compiles
import os
from alembic.script.write_hooks import register
from dotenv import load_dotenv


load_dotenv()

# Alembic 설정 객체
config = context.config

database_url = os.getenv("CONNECTION_STRING")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)
else:
    raise ValueError("환경변수 CONNECTION_STRING이 설정되어 있지 않습니다.")

# logging 설정 적용
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# metadata 대상 설정
target_metadata = Base.metadata

# Vector 타입 SQL 렌더링 설정
@compiles(Vector)
def compile_vector(element, compiler, **kw):
    return f"VECTOR({element.dim})"

# autogenerate 시 Vector 타입을 문자열로 표현하도록 설정
def render_item(type_, obj, autogen_context):
    if type_ == "type" and isinstance(obj, Vector):
        return f"Vector({obj.dim})"
    return False

# process_revision_directives 함수는 더 이상 사용되지 않음
# def process_revision_directives(context, revision, directives):
#    pass

# ✅ 마이그레이션 파일에 Vector import 자동 삽입 (쓰기 훅)
@register('add_vector_import') # 'add_vector_import'라는 이름으로 훅 등록
def add_vector_import_hook(context, script, file_output):
    """
    마이그레이션 스크립트 파일이 생성된 후 호출되어 Vector 임포트 문을 추가합니다.
    """
    import_line = "from pgvector.sqlalchemy import Vector\\n"
    lines = file_output.splitlines(keepends=True)
    modified_lines = []
    imported = False
    for line in lines:
        modified_lines.append(line)
        # 'from alembic import op' 줄을 찾아서 그 뒤에 임포트 문 삽입
        if line.strip().startswith("from alembic import op") and not imported:
            if import_line.strip() not in [l.strip() for l in lines]: # 이미 import 되어 있지 않다면 추가 (strip() 추가)
                modified_lines.append(import_line)
                imported = True # 중복 삽입 방지

    if imported:
        # script 객체는 훅에서 path 속성을 가집니다.
        print(f"✅ Vector import automatically inserted into {os.path.basename(script.path)}")
    else:
        # import_line이 이미 존재하거나 'from alembic import op' 줄을 찾지 못한 경우
        if import_line.strip() in [l.strip() for l in lines]:
            print("ℹ️ Vector import already present.")
        else:
            print("⚠️ Could not find 'from alembic import op' to insert Vector import.")
    return "".join(modified_lines) # 수정된 내용 반환


# 오프라인 마이그레이션
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_item=render_item,
        # process_revision_directives=process_revision_directives, # <-- 이 줄 제거 (기존에 주석 처리되어 있었음)
    )

    with context.begin_transaction():
        context.run_migrations()


# --- 온라인 마이그레이션 (주요 변경 부분) ---

# SQLAlchemy 2.0 스타일 사용 (Future=True) 및 비동기 엔진 설정
# config에 설정된 URL을 직접 사용합니다.
connectable = AsyncEngine(
    engine_from_config(
        config.get_section(config.config_ini_section, {}),
        url=config.get_main_option("sqlalchemy.url"), # config에서 직접 URL을 가져와 사용
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True # SQLAlchemy 1.4+ / 2.0 스타일 사용을 명시
    )
)

# 비동기적으로 마이그레이션을 실행할 핵심 함수
async def run_async_migrations() -> None:
    """
    비동기 엔진을 사용하여 데이터베이스 연결을 얻고 마이그레이션을 실행합니다.
    """
    async with connectable.connect() as connection:
        # 이 부분을 수정합니다: connection=connection 인자를 제거합니다.
        await connection.run_sync(do_run_migrations) # 수정된 부분


# 동기 컨텍스트에서 실행되는 마이그레이션 로직
def do_run_migrations(connection) -> None:
    """
    Alembic의 context.configure와 context.run_migrations를 실행하는 동기 함수.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_item=render_item,
        # process_revision_directives=process_revision_directives, # <-- 이 줄 제거 (기존에 주석 처리되어 있었음)
    )
    with context.begin_transaction():
        context.run_migrations()

# 온라인 마이그레이션 (비동기 함수를 호출)
def run_migrations_online() -> None:
    """
    온라인 모드에서 마이그레이션을 실행합니다 (비동기 지원).
    """
    asyncio.run(run_async_migrations())

# 실행 분기
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()