import logging
import uuid
from typing import List, Optional

from serge.schema import user as user_schema
from serge.utils.security import get_password_hash
from sqlalchemy.orm import Session

from serge.models import user as user_model


def get_user(db: Session, username: str) -> Optional[user_schema.User]:
    """Retrieve a user from the database by username.

    This function queries the database for a user with the specified
    username. If a user is found, it maps the user data to a view model,
    including authentication information. If no user is found, it returns
    None.

    Args:
        db (Session): The database session to use for the query.
        username (str): The username of the user to retrieve.

    Returns:
        Optional[user_schema.User]: The user object mapped to the view model,
        or None if no user is found.
    """
    return Mappers.user_db_to_view(
        db.query(user_model.User).filter(user_model.User.username == username).first(),
        include_auth=True,
    )


def get_user_by_email(db: Session, email: str) -> Optional[user_schema.User]:
    return Mappers.user_db_to_view(db.query(user_model.User).filter(user_model.User.email == email).first())


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[user_schema.User]:
    return [Mappers.user_db_to_view(u) for u in db.query(user_model.User).offset(skip).limit(limit).all()]


def create_user(db: Session, ua: user_schema.UserAuth) -> Optional[user_schema.User]:
    """Create a new user in the database.

    This function checks if a user with the given username already exists in
    the database. If the user does not exist, it processes the
    authentication type, hashes the user's secret if necessary, and then
    adds the user and their authentication information to the database.
    Finally, it commits the changes and returns the newly created user
    object.

    Args:
        db (Session): The database session to perform operations.
        ua (user_schema.UserAuth): The user authentication data containing username, secret, and auth type.

    Returns:
        Optional[user_schema.User]: The created user object if successful, or None if the user already
            exists
        or an unsupported authentication type is provided.
    """

    # Check already exists
    if get_user(db, ua.username):
        logging.error(f"Tried to create new user, but already exists: {ua.username}")
        return None

    match ua.auth_type:
        case 1:
            ua.secret = get_password_hash(ua.secret)
        case _:  # Todo: More auth types
            return None

    db_user, db_user_auth = Mappers.user_view_to_db(None, ua)
    db.add(db_user_auth)
    db.add(db_user)
    db.commit()
    return Mappers.user_db_to_view(db_user)


def update_user(db: Session, u: user_schema.User) -> Optional[user_schema.User]:
    """Update a user's information in the database.

    This function retrieves a user from the database based on the provided
    username. If the user is found, it updates the user's attributes with
    the values from the provided user schema, excluding specific fields such
    as 'auth' and 'chats'. After updating the user, the changes are
    committed to the database.

    Args:
        db (Session): The database session used to query and update the user.
        u (user_schema.User): The user schema containing updated user information.

    Returns:
        Optional[user_schema.User]: The updated user object if the user was found;
        otherwise, returns None.
    """

    user = db.query(user_model.User).filter(user_model.User.username == u.username).first()
    if not user:
        return None
    for k, v in u.dict().items():
        if k in ["auth", "chats"]:
            continue
        setattr(user, k, v)
    db.commit()
    return user


def create_chat(db: Session, chat: user_schema.Chat):
    """Create a new chat entry in the database.

    This function takes a chat object and creates a new chat entry in the
    database. It initializes a Chat model instance with the provided owner
    and chat_id, adds it to the session, and commits the transaction to save
    the changes.

    Args:
        db (Session): The database session used to interact with the database.
        chat (user_schema.Chat): The chat object containing the owner and chat_id.
    """

    c = user_model.Chat(owner=chat.owner, chat_id=chat.chat_id)
    db.add(c)
    db.commit()


def remove_chat(db: Session, chat: user_schema.Chat):
    """Remove a chat from the database.

    This function takes a chat object and removes the corresponding entry
    from the database. It queries the database for the chat using the
    chat_id and deletes the found chat record. After deletion, it commits
    the changes to the database.

    Args:
        db (Session): The database session used to interact with the database.
        chat (user_schema.Chat): The chat object containing the chat_id of the chat to be removed.
    """

    c = db.query(user_model.Chat).filter(user_model.Chat.chat_id == chat.chat_id).one()
    db.delete(c)
    db.commit()


class Mappers:
    @staticmethod
    def user_db_to_view(u: user_model.User, include_auth=False) -> user_schema.User:
        """Convert a user database model to a view model.

        This function takes a user model object and transforms it into a user
        schema view model. It extracts relevant attributes from the user model
        while optionally including authentication details and chat information.
        If the user model is not provided, it returns None. The function filters
        out private attributes and specific fields that are not needed in the
        view model.

        Args:
            u (user_model.User): The user model object to be converted.
            include_auth (bool): A flag indicating whether to include authentication details in the view
                model.

        Returns:
            user_schema.User: The transformed user schema view model, or None if the input user model
                is None.
        """

        if not u:
            return None
        auths = chats = []
        if include_auth:
            auths = u.auth
        # u.auth = []
        chats = u.chats
        # u.chats = []
        app_user = user_schema.User(**{k: v for k, v in u.__dict__.items() if not k.startswith("_") and k not in ["chats", "auth"]})

        app_user.auth = [user_schema.UserAuth(username=u.username, secret=x.secret, auth_type=x.auth_type) for x in auths]

        app_user.chats = [user_schema.Chat(chat_id=x.chat_id, owner=x.owner) for x in chats]

        return app_user

    @staticmethod
    def user_view_to_db(
        u: Optional[user_schema.User] = None, ua: Optional[user_schema.UserAuth] = None
    ) -> (user_model.User, Optional[user_model.UserAuth]):
        """Convert user view data to database models.

        This function takes user view data and converts it into database models
        for both the user and user authentication. If a user object is not
        provided, a new user is created using the information from the user
        authentication object. The function also maps any associated chats to
        the user model.

        Args:
            u (Optional[user_schema.User]): An optional user schema object containing user data.
            ua (Optional[user_schema.UserAuth]): An optional user authentication schema object.

        Returns:
            tuple: A tuple containing the user model and an optional user authentication
                model.
        """

        assert u or ua, "One of User or UserAuth must be passed"
        if not u:  # Creating a new user
            u = user_schema.User(id=uuid.uuid4(), username=ua.username)
        auth = []
        if ua:
            auth = Mappers.user_auth_view_to_db(ua, u.id)
        user = user_model.User(**u.dict())
        if auth:
            user.auth.append(auth)
        for chat in u.chats:
            user.chats.append(user_model.Chat(chat_id=chat.chat_id))
        return (user, auth)

    @staticmethod
    def user_auth_view_to_db(ua: user_schema.UserAuth, user_id: uuid.UUID) -> user_model.UserAuth:
        """Convert a user authentication view to a database model.

        This function takes a user authentication schema and a user ID, and
        returns a corresponding user authentication model. If the provided user
        authentication schema is None, the function will return None. Otherwise,
        it creates and returns a UserAuth model instance populated with the
        secret, auth type, and user ID.

        Args:
            ua (user_schema.UserAuth): The user authentication schema to convert.
            user_id (uuid.UUID): The unique identifier of the user.

        Returns:
            user_model.UserAuth: An instance of UserAuth populated with the
            provided data, or None if the input schema is None.
        """

        if not ua:
            return None
        return user_model.UserAuth(secret=ua.secret, auth_type=ua.auth_type, user_id=user_id)
