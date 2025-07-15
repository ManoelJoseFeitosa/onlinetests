import os
from logging.config import fileConfig

from flask import current_app
from alembic import context

# Importe o objeto 'app' e 'db' do seu arquivo principal da aplicação.
# Isso é crucial para que o Alembic tenha o contexto da sua aplicação.
# Certifique-se de que o nome do arquivo (main) está correto.
from main import app, db

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- A CORREÇÃO PRINCIPAL ESTÁ AQUI ---
# Aponte o target_metadata para o metadata do seu objeto db.
# É assim que o Alembic descobre seus modelos (tabelas).
target_metadata = db.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Para o modo offline, usamos a URL configurada diretamente no Flask.
    url = app.config.get('SQLALCHEMY_DATABASE_URI')
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Usamos o 'with app.app_context()' para garantir que o 'current_app'
    # e as extensões do Flask (como SQLAlchemy) estejam disponíveis.
    with app.app_context():
        connectable = db.get_engine()

        with connectable.connect() as connection:
            context.configure(
                connection=connection, target_metadata=target_metadata
            )

            with context.begin_transaction():
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
