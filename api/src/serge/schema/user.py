import uuid

from pydantic import BaseModel


class UserBase(BaseModel):
    username: str


class UserAuth(UserBase):
    secret: str
    auth_type: int


class Chat(BaseModel):
    chat_id: str
    owner: str


class User(UserBase):
    id: uuid.UUID
    is_active: bool = True
    email: str = ""
    full_name: str = ""
    theme_light: bool = False
    default_prompt: str = "Below is an instruction that describes a task. Write a response that appropriately completes the request."
    auth: list[UserAuth] = []
    chats: list[Chat] = []

    class Config:
        orm_mode = True

    def to_public_dict(self):
        """Convert the object to a public dictionary representation.

        This method transforms the object's attributes into a dictionary format
        suitable for public exposure. It specifically masks the "secret" field
        in the "auth" section of the dictionary to ensure sensitive information
        is not disclosed. The resulting dictionary can be used for serialization
        or API responses.

        Returns:
            dict: A dictionary representation of the object with sensitive information
                masked.
        """

        user_dict = self.dict()
        for auth in user_dict["auth"]:
            auth["secret"] = "********"
        return user_dict


class Token(BaseModel):
    access_token: str
    token_type: str
