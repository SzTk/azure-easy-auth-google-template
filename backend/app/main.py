"""Minimal FastAPI app showing how to wire up require_authorized_user.

Replace this file with your actual application. The only requirement is
to add `Depends(require_authorized_user)` to any endpoint you want to protect.
"""

from typing import Optional

from fastapi import Depends, FastAPI

from app.core.auth import require_authorized_user

app = FastAPI()


@app.get("/hello")
async def hello(email: Optional[str] = Depends(require_authorized_user)):
    return {"message": "Hello", "email": email}
