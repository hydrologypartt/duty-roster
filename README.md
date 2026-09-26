
# ระบบจัดเวรออนไลน์ MVP v2

## สิ่งที่เพิ่มจาก v1
- Admin สร้างเดือนใหม่จากหน้าเว็บได้
- ตั้งวันเปิด/ปิดรับวันไม่ว่าง และจำนวนครั้งแก้ไข
- เปิด/ปิด Admin override หลัง deadline
- เพิ่มสมาชิกถาวรและเลือกสมาชิกที่ใช้ในแต่ละเดือน
- ตั้งจำนวนคนต่อวัน
- Algorithm จัดเวรโดยถือวันไม่ว่างเป็น hard constraint และพยายามกระจายจำนวนเวร/เสาร์อาทิตย์/เวรติดกัน
- Admin แก้เวรหลัง Algorithm จัด
- ตรวจสอบตาราง
- Reset วันไม่ว่างรายคน/ทั้งหมด
- Reset ตารางเวรโดยไม่ลบวันไม่ว่าง
- เพิ่ม/ปิด Admin
- Audit log
- ค่าเวรและ export JPEG/CSV

## Deploy
1. สร้าง Supabase project
2. SQL Editor -> รัน `supabase_schema.sql`
3. สร้าง Admin ตัวแรก โดย hash password เป็น SHA-256 แล้ว insert ลง `admins`
4. สร้าง GitHub repository และอัปโหลด `app.py`, `requirements.txt`, `supabase_schema.sql`
5. Streamlit Community Cloud -> New app -> เลือก repository -> `app.py`
6. App settings -> Secrets:
SUPABASE_URL = "https://YOURPROJECT.supabase.co"
SUPABASE_KEY = "YOUR_SUPABASE_KEY"
7. Deploy
8. เปิด URL ที่ Streamlit ให้มา
9. Admin login -> สร้างเดือน -> เพิ่มสมาชิก -> เลือกสมาชิกประจำเดือน -> ตั้งจำนวนคน/วัน -> ตั้งค่าเงิน
10. ส่ง URL ให้สมาชิก

## สำคัญด้านความปลอดภัย
MVP นี้ใช้รหัสผ่านแบบ SHA-256 ในตารางเพื่อให้เริ่มทดลองได้ง่าย แต่ก่อนใช้งานจริงกับข้อมูลส่วนบุคคลควรเปลี่ยนเป็นระบบ authentication ที่เหมาะสมและเปิด RLS/Policies ใน Supabase
