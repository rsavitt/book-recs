from fastapi import APIRouter

from app.api import account, admin, auth, books, imports, onboarding, recommendations, users

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(books.router, prefix="/books", tags=["books"])
router.include_router(imports.router, prefix="/imports", tags=["imports"])
router.include_router(recommendations.router, prefix="/recommendations", tags=["recommendations"])
router.include_router(admin.router, prefix="/admin", tags=["admin"])
router.include_router(account.router, prefix="/account", tags=["account"])
router.include_router(onboarding.router, prefix="/onboarding", tags=["onboarding"])
