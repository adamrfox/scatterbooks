import logging

from sqlalchemy.orm import Session as DBSession

from app.config import settings
from app.models import User
from app.security import hash_password

logger = logging.getLogger(__name__)


def bootstrap_admin(db: DBSession) -> None:
    if db.query(User).first() is not None:
        return

    if not settings.initial_admin_username or not settings.initial_admin_password:
        logger.warning(
            "No users exist yet and INITIAL_ADMIN_USERNAME/INITIAL_ADMIN_PASSWORD are not "
            "set -- the app has no way to log in. Set those env vars and restart."
        )
        return

    admin = User(
        username=settings.initial_admin_username,
        password_hash=hash_password(settings.initial_admin_password),
        role="admin",
    )
    db.add(admin)
    db.commit()
    logger.info("Created initial admin user %r", admin.username)
