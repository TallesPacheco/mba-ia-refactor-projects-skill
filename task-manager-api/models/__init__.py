"""Re-exporta os models para que `import models` registre todos no metadata do SQLAlchemy."""
from models.category import Category
from models.task import Task
from models.user import User

__all__ = ["Category", "Task", "User"]
