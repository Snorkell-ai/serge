import logging
import uuid

from serge.models.settings import Settings
from serge.models.user import User, UserAuth
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

settings = Settings()

engine = create_engine(settings.SERGE_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def seed_db(db: Session):
    """Seed the database with a default system user.

    This function checks if a user with the username "system" already exists
    in the database. If the user does not exist, it creates a new user with
    default attributes and adds it to the database. The function ensures
    that there is always a system user available for application use.

    Args:
        db (Session): The database session used to interact with the database.

    Returns:
        None: This function does not return any value.
    """

    sys_u = db.query(User).filter(User.username == "system").first()
    if sys_u:
        return
    system_user = User(
        id=uuid.uuid4(),
        username="system",
        email="",
        full_name="Default User",
        theme_light=False,
        default_prompt="Below is an instruction that describes a task. Write a response that appropriately completes the request.",
        is_active=True,
        auth=[UserAuth(secret="", auth_type=0)],
    )
    db.add(system_user)
    db.commit()
    logging.info("System user created")
