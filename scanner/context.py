from .models import is_pharmacist


def role(request):
    user = getattr(request, "user", None)
    return {"is_pharmacist": bool(user and user.is_authenticated and is_pharmacist(user))}
