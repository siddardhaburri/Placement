import os
import psycopg2
from dotenv import load_dotenv
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

# Load .env variables automatically
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv()

# 1. Check if DATABASE_URL is set in environment (e.g. on Render/Heroku)
env_db_url = os.environ.get("DATABASE_URL")
DATABASE_URL = None

if env_db_url:
    # SQLAlchemy requires 'postgresql://' instead of legacy 'postgres://'
    if env_db_url.startswith("postgres://"):
        env_db_url = env_db_url.replace("postgres://", "postgresql://", 1)
    
    # Try connecting to make sure it's valid
    try:
        temp_conn = psycopg2.connect(env_db_url, connect_timeout=10)
        temp_conn.close()
        DATABASE_URL = env_db_url
        print("Database detection: Successfully connected using env DATABASE_URL")
    except Exception as e:
        print(f"Database detection: Failed to connect using env DATABASE_URL: {e}")

if not DATABASE_URL:
    # Common connection credentials to probe on local system
    CONNECTION_STRINGS = [
        "postgresql://postgres:postgres@localhost:5432",
        "postgresql://postgres:admin@localhost:5432",
        "postgresql://postgres:root@localhost:5432",
        "postgresql://postgres:password@localhost:5432",
        "postgresql://postgres@localhost:5432",
    ]

    DATABASE_NAME = "placement_ops"
    WORKING_BASE_URL = None

    # Autodetect credentials
    for conn_str in CONNECTION_STRINGS:
        try:
            # Try connecting to default database 'postgres' to check connection
            temp_conn = psycopg2.connect(f"{conn_str}/postgres", connect_timeout=3)
            temp_conn.close()
            WORKING_BASE_URL = conn_str
            print(f"Database detection: Connected successfully using base URL: {conn_str.replace(conn_str.split('@')[0].split(':')[-1], '****') if ':' in conn_str.split('@')[0] else conn_str}")
            break
        except Exception:
            continue

    if not WORKING_BASE_URL:
        # Fallback to SQLite if Postgres is unavailable
        print("Database detection: Could not connect to PostgreSQL. Fallback to SQLite.")
        DATABASE_URL = "sqlite:///./placement_ops.db"
    else:
        # Ensure database exists
        try:
            conn = psycopg2.connect(f"{WORKING_BASE_URL}/postgres", connect_timeout=3)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{DATABASE_NAME}'")
            exists = cursor.fetchone()
            if not exists:
                cursor.execute(f"CREATE DATABASE {DATABASE_NAME}")
                print(f"Database detection: Created database '{DATABASE_NAME}'")
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Database detection: Error checking/creating database: {e}")
        
        DATABASE_URL = f"{WORKING_BASE_URL}/{DATABASE_NAME}"

print(f"Database URL in use: {DATABASE_URL.replace(DATABASE_URL.split('@')[0].split(':')[-1], '****') if '@' in DATABASE_URL and ':' in DATABASE_URL.split('@')[0] else DATABASE_URL}")

# Create engine
engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["execution_options"] = {
        "schema_translate_map": {
            "studentlife": None,
            "curriculum": None,
            "people": None,
            "research": None,
            "agentops": None,
            "outcomes": None,
        }
    }

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    """Create all tables if they don't exist yet.
    Called at application startup (see main.py @app.on_event('startup')).
    Safe to call repeatedly -- create_all is a no-op for tables that already exist.
    """
    # Import all models so their metadata is registered before create_all runs.
    import importlib
    try:
        importlib.import_module("backend.models")
    except Exception:
        try:
            importlib.import_module("models")
        except Exception:
            pass

    # Agent 13 models use custom Postgres schemas. CREATE SCHEMA IF NOT EXISTS
    # is idempotent on Postgres — safe to run on startup for Postgres.
    if not engine.url.drivername.startswith("sqlite"):
        agent13_schemas = [
            "studentlife", "curriculum", "people", "research", "agentops", "outcomes"
        ]
        try:
            with engine.connect() as conn:
                for schema in agent13_schemas:
                    conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema}"))
                conn.commit()
        except Exception:
            pass

    # SQL migration files are the authoritative schema source of truth on PostgreSQL.
    # Base.metadata.create_all is only used for SQLite local fallback environments.
    if engine.url.drivername.startswith("sqlite"):
        with engine.connect().execution_options(schema_translate_map={
            "studentlife": None, "curriculum": None, "people": None, "research": None, "agentops": None, "outcomes": None
        }) as conn:
            Base.metadata.create_all(bind=conn)
        print("Database: SQLite local fallback tables created via Base.metadata.create_all")
    else:
        print("Database: PostgreSQL connected — SQL migrations serve as authoritative schema source of truth")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
