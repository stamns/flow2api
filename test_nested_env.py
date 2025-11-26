import os
import sys
from pydantic import BaseModel, Field, AliasChoices
from pydantic_settings import BaseSettings

os.environ["MY_NESTED_VAR"] = "from_env"

class Nested(BaseModel):
    var: str = Field(validation_alias=AliasChoices("var", "MY_NESTED_VAR"))

class Settings(BaseSettings):
    nested: Nested

try:
    print("Starting...", flush=True)
    s = Settings()
    print(f"Result: {s.nested.var}", flush=True)
except Exception as e:
    print(f"Error: {e}", flush=True)
