from pydantic import BaseModel

class InpAllTimeScore(BaseModel):
    STEAM_ID: str  # "STEAM:1:12345678"
    Score: int = None # "999",
    IsPrivileged: bool = False