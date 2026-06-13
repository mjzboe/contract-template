from pydantic import BaseModel


class RoleUpdate(BaseModel):
    role: str


class UserRoleResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}
