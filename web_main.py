from fastapi import FastAPI, Request, Form, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
from config import bot, ADMIN_ID
from database import init_db, save_report, get_reports, get_report_by_id, delete_report
from utils import save_file, send_to_admin
import os
from uuid import uuid4
from datetime import datetime, timedelta
import hashlib
import hmac
import base64
from config import bot, ADMIN_ID, BOT_TOKEN

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
security = HTTPBearer()


# Session data with expiration
sessions = {}  # Key: session_id, Value: {data: dict, expires_at: datetime}

# Initialize database
@app.on_event("startup")
async def startup_event():
    await init_db()

# Verify Telegram init_data (basic check)
def verify_telegram_init_data(init_data: str, bot_token: str) -> bool:
    if not init_data:
        return False
    params = dict(param.split('=') for param in init_data.split('&') if '=' in param)
    if 'hash' not in params:
        return False
    check_hash = params.pop('hash')
    data_check_string = '\n'.join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return calculated_hash == check_hash

# Web App uchun asosiy sahifa
@app.get("/webapp", response_class=HTMLResponse)
async def webapp(request: Request):
    init_data = request.query_params.get("initData", "")
    if not verify_telegram_init_data(init_data, BOT_TOKEN):
        return HTMLResponse("Unauthorized!", status_code=403)
    session_id = str(uuid4())
    sessions[session_id] = {"data": {}, "expires_at": datetime.now() + timedelta(minutes=30)}
    return templates.TemplateResponse("webapp_step1.html", {"request": request, "session_id": session_id, "init_data": init_data})

# Step-by-step registration within Web App
@app.post("/webapp/step1")
async def webapp_step1(request: Request, session_id: str = Form(...), fullname: str = Form(...)):
    if session_id not in sessions or datetime.now() > sessions[session_id]["expires_at"]:
        return HTMLResponse("Session topilmadi yoki muddati tugagan!", status_code=400)
    sessions[session_id]["data"]["fullname"] = fullname
    return templates.TemplateResponse("webapp_step2.html", {"request": request, "session_id": session_id})

@app.post("/webapp/step2")
async def webapp_step2(request: Request, session_id: str = Form(...), lastname: str = Form(...)):
    if session_id not in sessions or datetime.now() > sessions[session_id]["expires_at"]:
        return HTMLResponse("Session topilmadi yoki muddati tugagan!", status_code=400)
    sessions[session_id]["data"]["fullname"] = f"{sessions[session_id]['data'].get('fullname')} {lastname}"
    return templates.TemplateResponse("webapp_step3.html", {"request": request, "session_id": session_id})

@app.post("/webapp/step3")
async def webapp_step3(request: Request, session_id: str = Form(...), age: str = Form(...)):
    if session_id not in sessions or datetime.now() > sessions[session_id]["expires_at"]:
        return HTMLResponse("Session topilmadi yoki muddati tugagan!", status_code=400)
    try:
        age_int = int(age)
        if not 0 <= age_int <= 150:
            raise ValueError
        sessions[session_id]["data"]["age"] = age_int
        return templates.TemplateResponse("webapp_step4.html", {"request": request, "session_id": session_id})
    except ValueError:
        return templates.TemplateResponse("webapp_step3.html", {"request": request, "session_id": session_id, "error": "Iltimos, raqam kiriting (0-150)!"})

@app.post("/webapp/step4")
async def webapp_step4(request: Request, session_id: str = Form(...), phone: str = Form(...)):
    if session_id not in sessions or datetime.now() > sessions[session_id]["expires_at"]:
        return HTMLResponse("Session topilmadi yoki muddati tugagan!", status_code=400)
    sessions[session_id]["data"]["phone"] = phone
    return templates.TemplateResponse("webapp_step5.html", {"request": request, "session_id": session_id})

@app.post("/webapp/step5")
async def webapp_step5(request: Request, session_id: str = Form(...), role: str = Form(...)):
    if session_id not in sessions or datetime.now() > sessions[session_id]["expires_at"]:
        return HTMLResponse("Session topilmadi yoki muddati tugagan!", status_code=400)
    sessions[session_id]["data"]["role"] = "Xodim" if role == "employee" else "Mijoz"
    return templates.TemplateResponse("webapp_step6.html", {"request": request, "session_id": session_id})

@app.post("/webapp/step6")
async def webapp_step6(request: Request, session_id: str = Form(...), anonymous: str = Form(...)):
    if session_id not in sessions or datetime.now() > sessions[session_id]["expires_at"]:
        return HTMLResponse("Session topilmadi yoki muddati tugagan!", status_code=400)
    sessions[session_id]["data"]["anonymous"] = anonymous == "true"
    return templates.TemplateResponse("webapp_step7.html", {"request": request, "session_id": session_id})

@app.post("/webapp/step7")
async def webapp_step7(request: Request, session_id: str = Form(...), message: str = Form(...)):
    if session_id not in sessions or datetime.now() > sessions[session_id]["expires_at"]:
        return HTMLResponse("Session topilmadi yoki muddati tugagan!", status_code=400)
    sessions[session_id]["data"]["message"] = message
    return templates.TemplateResponse("webapp_confirm.html", {"request": request, "data": sessions[session_id]["data"], "session_id": session_id})

@app.post("/webapp/confirm")
async def webapp_confirm(request: Request, session_id: str = Form(...), action: str = Form(...), file: UploadFile = File(None)):
    if session_id not in sessions or datetime.now() > sessions[session_id]["expires_at"]:
        return HTMLResponse("Session topilmadi yoki muddati tugagan!", status_code=400)
    if action == "yes":
        sessions[session_id]["data"]["file_path"] = None
        if file:
            allowed_extensions = {".jpg", ".jpeg", ".png", ".pdf", ".docx"}  # Ruxsat etilgan kengaytmalar
            file_extension = os.path.splitext(file.filename.lower())[1]
            if file_extension not in allowed_extensions:
                return JSONResponse({"status": "error", "message": "Faqat .jpg, .jpeg, .png, .pdf yoki .docx fayllari ruxsat etilgan!"})
            file_path = os.path.join("uploads", f"file_{uuid4().hex()}{file_extension}")
            with open(file_path, "wb") as f:
                f.write(await file.read())
            sessions[session_id]["data"]["file_path"] = file_path
        try:
            report_id = await save_report(sessions[session_id]["data"])
            await send_to_admin(report_id)
            del sessions[session_id]
            return JSONResponse({"status": "success", "message": "Murojaatingiz qabul qilindi!"})
        except Exception as e:
            return JSONResponse({"status": "error", "message": str(e)})
    else:
        del sessions[session_id]
        return JSONResponse({"status": "cancel", "message": "Murojaat bekor qilindi!"})

# Admin routes
@app.get("/admin", response_class=HTMLResponse, dependencies=[Depends(security)])
async def admin_panel(request: Request):
    if int(request.headers.get("X-User-ID", "0")) != ADMIN_ID:
        return HTMLResponse("Ruxsat yo'q!", status_code=403)
    try:
        reports = await get_reports()
        return templates.TemplateResponse("admin_panel.html", {"request": request, "reports": reports})
    except Exception as e:
        return HTMLResponse(f"Ma'lumotlarni yuklashda xatolik: {str(e)}", status_code=500)

@app.get("/admin/view/{report_id}")
async def admin_view_report(request: Request, report_id: int, token: str = Depends(security)):
    if int(request.headers.get("X-User-ID", "0")) != ADMIN_ID:
        return HTMLResponse("Ruxsat yo'q!", status_code=403)
    try:
        report = await get_report_by_id(report_id)
        if not report:
            return HTMLResponse("Murojaat topilmadi!", status_code=404)
        return templates.TemplateResponse("admin_view.html", {"request": request, "report": report})
    except Exception as e:
        return HTMLResponse(f"Ma'lumot yuklanmadi: {str(e)}", status_code=500)

@app.get("/admin/delete/{report_id}")
async def admin_delete_report(request: Request, report_id: int, token: str = Depends(security)):
    if int(request.headers.get("X-User-ID", "0")) != ADMIN_ID:
        return HTMLResponse("Ruxsat yo'q!", status_code=403)
    try:
        await delete_report(report_id)
        return RedirectResponse(url="/admin", status_code=303)
    except Exception as e:
        return HTMLResponse(f"O'chirishda xatolik: {str(e)}", status_code=500)

# Run with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)