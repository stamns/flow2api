try:
    from pydantic.v1 import BaseSettings
    print('v1 BaseSettings found')
except ImportError:
    print('v1 BaseSettings not found')

try:
    from pydantic_settings import BaseSettings
    print('pydantic_settings found')
except ImportError:
    print('pydantic_settings not found')
