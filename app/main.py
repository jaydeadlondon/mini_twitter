from fastapi import FastAPI
from app.api.endpoints import router as api_router
from fastapi.staticfiles import StaticFiles
from sqladmin import Admin
from app.core.admin import UserAdmin, PostAdmin, CommentAdmin, MediaAdmin
from app.core.database import engine

app = FastAPI(title="Social Feed MVP")

app.mount("/static", StaticFiles(directory="uploaded_files"), name="static")

app.include_router(api_router)

admin = Admin(app, engine)

admin.add_view(UserAdmin)
admin.add_view(PostAdmin)
admin.add_view(CommentAdmin)
admin.add_view(MediaAdmin)


@app.get("/")
async def root():
    return {"message": "Social Feed MVP is running"}
