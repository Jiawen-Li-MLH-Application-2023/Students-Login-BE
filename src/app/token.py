from itsdangerous import URLSafeSerializer
from src.app import config


def generate_confirmation_token(email):
    serializer = URLSafeSerializer(config.BaseConfig.SECRET_KEY)
    return serializer.dumps(email, salt=config.BaseConfig.SECURITY_PASSWORD_SALT)


def confirm_token(token, expiration=3600):
    serializer = URLSafeSerializer(config.BaseConfig.SECRET_KEY)
    try:
        email = serializer.loads(
            token,
            salt=config.BaseConfig.SECURITY_PASSWORD_SALT,
            max_age=expiration
        )
    except:
        return False
    return email
