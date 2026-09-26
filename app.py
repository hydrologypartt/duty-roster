
import os, io, hashlib
from datetime import date, datetime, timedelta
from collections import defaultdict
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from supabase import create_client

st.set_page_config(page_title="ระบบจัดเวรออนไลน์", page_icon="📅", layout="wide")

URL = st.secrets.get("SUPABASE_URL", os.getenv("SUPABASE_URL", ""))
KEY = st.secrets.get("SUPABASE_KEY", os.getenv("SUPABASE_KEY", ""))
if not URL or not KEY:
    st.error("ยังไม่ได้ตั้งค่า SUPABASE_URL และ SUPABASE_KEY")
    st.stop()
sb = create_client(URL, KEY)

MONTHS = ["มกราคม","กุมภาพันธ์","มีนาคม","เมษายน","พฤษภาคม","มิถุนายน",
          "กรกฎาคม","สิงหาคม","กันยายน","ตุลาคม","พฤศจิกายน","ธันวาคม"]
WD = ["จันทร์","อังคาร","พุธ","พฤหัสบดี","ศุกร์","เสาร์","อาทิตย์"]
SHORT_WD = ["จ.","อ.","พ.","พฤ.","ศ.","ส.","อา."]

def h(s): return hashlib.sha256(s.encode()).hexdigest()
def month_text(y,m): return f"{MONTHS[m-1]} {y+543}"
def admin(): return st.session_state.get("admin")
def get_month(mid):
    r=sb.table("duty_months").select("*").eq("id",mid).execute().data
    return r[0] if r else None
def people_for(mid):
    r=sb.table("month_members").select("person_id,people(id,name,phone,active)").eq("month_id",mid).execute().data
    return [x["people"] for x in r]
def unavailable(mid):
    return sb.table("unavailable_days").select("*").eq("month_id",mid).execute().data
def duties(mid):
    return sb.table("duties").select("*,people(name,phone)").eq("month_id",mid).order("duty_date").order("slot").execute().data
def log(action, mid=None, pid=None, details=None):
    try: sb.table("audit_logs").insert({"action":action,"month_id":mid,"person_id":pid,"admin_username":admin(),"details":details or {}}).execute()
    except Exception: pass
def month_days(y,m):
    start=date(y,m,1)
    end=date(y+1,1,1) if m==12 else date(y,m+1,1)
    return [start+timedelta(days=i) for i in range((end-start).days)]

# Sidebar
with st.sidebar:
    st.markdown("## 🔐 Admin")
    if not admin():
        u=st.text_input("Username")
        p=st.text_input("Password",type="password")
        if st.button("เข้าสู่ระบบ",use_container_width=True):
            r=sb.table("admins").select("*").eq("username",u).eq("active",True).execute().data
            if r and r[0]["password_hash"]==h(p):
                st.session_state.admin=u; st.rerun()
            else: st.error("Username หรือ Password ไม่ถูกต้อง")
    else:
        st.success(f"Admin: {admin()}")
        if st.button("ออกจากระบบ",use_container_width=True):
            st.session_state.pop("admin",None); st.rerun()

st.title("📅 ระบบจัดเวรออนไลน์")

months=sb.table("duty_months").select("*").order("year",desc=True).order("month",desc=True).execute().data

# =========================
# Member
# =========================
if not admin():
    if not months:
        st.info("ยังไม่มีเดือนที่เปิดให้ลงวันไม่ว่าง")
        st.stop()
    opts={m["id"]:f"{month_text(m['year'],m['month'])} — {m['status']}" for m in months}
    mid=st.selectbox("เลือกเดือน",list(opts),format_func=lambda x:opts[x])
    m=get_month(mid)
    people=people_for(mid)
    if not people:
        st.warning("เดือนนี้ยังไม่มีรายชื่อสมาชิก")
        st.stop()

    st.header(f"📝 ลงวันไม่ว่าง — {month_text(m['year'],m['month'])}")
    ids={p["id"]:p["name"] for p in people}
    pid=st.selectbox("เลือกชื่อของคุณ",list(ids),format_func=lambda x:ids[x])
    rows=[x for x in unavailable(mid) if x["person_id"]==pid]
    used=max([x["edit_no"] for x in rows],default=0)
    max_edits=int(m["max_unavailable_edits"])
    today=date.today()
    deadline=date.fromisoformat(str(m["unavailable_deadline"]))
    st.info(f"แก้ไขได้ {max_edits} ครั้ง • ใช้ไปแล้ว {used} ครั้ง • ปิดรับวันที่ {deadline.strftime('%d/%m/%Y')}")

    days=month_days(m["year"],m["month"])
    current={x["unavailable_date"] for x in rows}
    open_now=today<=deadline or bool(m["admin_override_open"])
    if open_now:
        chosen=st.multiselect(
            "เลือกวันที่ไม่สามารถอยู่เวรได้",
            days,
            default=[d for d in days if d.isoformat() in current],
            format_func=lambda d:f"{d.day:02d}/{d.month:02d}/{d.year+543} ({SHORT_WD[d.weekday()]})"
        )
        if st.button("💾 บันทึกวันไม่ว่าง",type="primary"):
            if used>=max_edits:
                st.error("คุณใช้สิทธิ์แก้ไขครบแล้ว")
            else:
                sb.table("unavailable_days").delete().eq("month_id",mid).eq("person_id",pid).execute()
                if chosen:
                    sb.table("unavailable_days").insert([
                        {"month_id":mid,"person_id":pid,"unavailable_date":d.isoformat(),"edit_no":used+1} for d in chosen
                    ]).execute()
                log("member_update_unavailable",mid,pid,{"edit_no":used+1,"dates":[d.isoformat() for d in chosen]})
                st.success("บันทึกแล้ว"); st.rerun()
    else:
        st.warning("ปิดรับวันไม่ว่างแล้ว หากต้องการแก้ไขให้ติดต่อ Admin")
        st.write("วันที่แจ้งไว้:", ", ".join(sorted(current)) if current else "ไม่มี")

    st.divider()
    st.subheader("📋 ตารางเวรที่ประกาศ")
    ds=duties(mid)
    if ds:
        st.dataframe(pd.DataFrame([{"วันที่":x["duty_date"],"เวรที่":x["slot"],"ผู้ปฏิบัติงาน":x["people"]["name"]} for x in ds]),
                     use_container_width=True,hide_index=True)
    else: st.info("ยังไม่มีตารางเวรที่ประกาศ")
    st.stop()

# =========================
# Admin
# =========================
st.header("🛠 Admin Dashboard")
tabs=st.tabs(["📊 ภาพรวม","📅 จัดการเดือน","👥 สมาชิก","🚫 วันไม่ว่าง","🤖 จัดเวร","💰 ค่าเวร","📜 ประวัติ","👑 Admin"])

if not months:
    st.info("ยังไม่มีเดือน กรุณาสร้างเดือนจากแท็บ 'จัดการเดือน'")
    create_only=True
    mid=None
else:
    labels={m["id"]:f"{month_text(m['year'],m['month'])} — {m['status']}" for m in months}
    mid=st.selectbox("เดือนที่กำลังจัดการ",list(labels),format_func=lambda x:labels[x])
    m=get_month(mid)
    create_only=False

with tabs[0]:
    if m:
        ps=people_for(mid); un=unavailable(mid); ds=duties(mid)
        a,b,c,d=st.columns(4)
        a.metric("สมาชิก",len(ps)); b.metric("ผู้แจ้งวันไม่ว่าง",len(set(x["person_id"] for x in un)))
        c.metric("รายการเวร",len(ds)); d.metric("สถานะ",m["status"])
        st.write(f"**ช่วงรับวันไม่ว่าง:** {m['unavailable_start']} ถึง {m['unavailable_deadline']}  |  **แก้ได้:** {m['max_unavailable_edits']} ครั้ง")

with tabs[1]:
    st.subheader("สร้าง/แก้ไขเดือน")
    cy=st.number_input("ปี ค.ศ.",2024,2100,date.today().year)
    cm=st.selectbox("เดือน",range(1,13),index=date.today().month-1,format_func=lambda x:month_text(cy,x))
    cs=st.date_input("วันเปิดรับวันไม่ว่าง",date(cy,cm,1))
    ce=st.date_input("วันปิดรับวันไม่ว่าง",date(cy,cm,5))
    me=st.number_input("จำนวนครั้งที่สมาชิกแก้วันไม่ว่างได้",1,10,2)
    override=st.checkbox("อนุญาตให้สมาชิกแก้หลัง Deadline",False)
    if st.button("➕ สร้างเดือนใหม่",type="primary"):
        if ce<cs: st.error("วันปิดต้องไม่ก่อนวันเปิด")
        elif any(x["year"]==cy and x["month"]==cm for x in months): st.error("เดือนนี้มีอยู่แล้ว")
        else:
            r=sb.table("duty_months").insert({
                "year":cy,"month":cm,"status":"รอรับวันไม่ว่าง",
                "unavailable_start":cs.isoformat(),"unavailable_deadline":ce.isoformat(),
                "max_unavailable_edits":me,"admin_override_open":override,
                "weekday_counts":{"0":4,"1":3,"2":4,"3":3,"4":3,"5":3,"6":3}
            }).execute()
            log("create_month",r.data[0]["id"],details={"year":cy,"month":cm})
            st.success("สร้างเดือนแล้ว"); st.rerun()
    if m:
        st.divider()
        st.subheader("แก้ไขการตั้งค่าเดือนปัจจุบัน")
        if st.button("💾 บันทึก Deadline/จำนวนครั้ง/สิทธิ์ Admin Override"):
            sb.table("duty_months").update({
                "unavailable_start":cs.isoformat(),"unavailable_deadline":ce.isoformat(),
                "max_unavailable_edits":me,"admin_override_open":override
            }).eq("id",mid).execute()
            log("update_month_settings",mid); st.success("บันทึกแล้ว"); st.rerun()
        st.warning("การลบเดือนควรทำเมื่อแน่ใจ เพราะข้อมูลเวรและวันไม่ว่างของเดือนนั้นจะถูกลบตามความสัมพันธ์ฐานข้อมูล")
        if st.button("🗑️ ลบเดือนนี้"):
            sb.table("duty_months").delete().eq("id",mid).execute()
            log("delete_month",mid); st.success("ลบแล้ว"); st.rerun()

with tabs[2]:
    if not m: st.stop()
    ps=people_for(mid)
    allp=sb.table("people").select("*").eq("active",True).order("name").execute().data
    active={p["id"] for p in ps}
    st.subheader("รายชื่อที่นำมาจัดเวรเดือนนี้")
    for p in allp:
        c1,c2,c3=st.columns([4,3,2]); c1.write(p["name"]); c2.write(p.get("phone") or "-")
        checked=p["id"] in active
        val=c3.checkbox("นำมาจัด",checked,key=f"mm_{mid}_{p['id']}")
        if val and not checked: sb.table("month_members").insert({"month_id":mid,"person_id":p["id"]}).execute(); st.rerun()
        if not val and checked: sb.table("month_members").delete().eq("month_id",mid).eq("person_id",p["id"]).execute(); st.rerun()
    st.divider()
    st.subheader("เพิ่มสมาชิกเข้าฐานข้อมูลถาวร")
    n=st.text_input("ชื่อ-นามสกุล",key="newname"); ph=st.text_input("เบอร์โทร",key="newphone")
    if st.button("เพิ่มสมาชิก"):
        if not n.strip(): st.error("กรุณาใส่ชื่อ")
        else:
            try:
                sb.table("people").insert({"name":n.strip(),"phone":ph.strip(),"active":True}).execute()
                st.success("เพิ่มสมาชิกแล้ว"); st.rerun()
            except Exception as e: st.error("ชื่ออาจซ้ำหรือข้อมูลไม่ถูกต้อง")

with tabs[3]:
    if not m: st.stop()
    ps=people_for(mid); un=unavailable(mid)
    st.subheader("ตรวจสอบวันไม่ว่าง")
    if un:
        pmap={p["id"]:p["name"] for p in ps}
        st.dataframe(pd.DataFrame([{"ชื่อ":pmap.get(x["person_id"],"?"),"วันที่":x["unavailable_date"],"แก้ครั้งที่":x["edit_no"]} for x in un]),
                     use_container_width=True,hide_index=True)
    else: st.info("ยังไม่มีใครแจ้งวันไม่ว่าง")
    pmap={p["id"]:p["name"] for p in ps}
    if ps:
        rp=st.selectbox("สมาชิก",list(pmap),format_func=lambda x:pmap[x],key="rp")
        if st.button("🔄 Reset วันไม่ว่างของคนนี้"):
            sb.table("unavailable_days").delete().eq("month_id",mid).eq("person_id",rp).execute()
            log("reset_person_unavailable",mid,rp); st.success("Reset แล้ว"); st.rerun()
        if st.button("⚠️ Reset วันไม่ว่างทุกคน"):
            sb.table("unavailable_days").delete().eq("month_id",mid).execute()
            log("reset_all_unavailable",mid); st.success("Reset ทุกคนแล้ว"); st.rerun()

with tabs[4]:
    if not m: st.stop()
    ps=people_for(mid); pids=[p["id"] for p in ps]; days=month_days(m["year"],m["month"])
    st.subheader("⚙️ จำนวนคนต่อวัน")
    wc=m["weekday_counts"] or {"0":4,"1":3,"2":4,"3":3,"4":3,"5":3,"6":3}
    cols=st.columns(7); newwc={}
    for i,col in enumerate(cols): newwc[str(i)]=col.number_input(SHORT_WD[i],1,20,int(wc.get(str(i),3)),key=f"wc{i}")
    if st.button("บันทึกจำนวนคนต่อวัน"): sb.table("duty_months").update({"weekday_counts":newwc}).eq("id",mid).execute(); log("update_staffing",mid,details=newwc); st.success("บันทึกแล้ว"); st.rerun()

    st.subheader("🤖 จัดเวรอัตโนมัติ")
    if st.button("จัดเวรอัตโนมัติ",type="primary"):
        un={(x["person_id"],x["unavailable_date"]) for x in unavailable(mid)}
        # Greedy balancing with hard constraints + fairness terms.
        total=defaultdict(int); wknd=defaultdict(int); last=defaultdict(list); chosen_rows=[]; failures=[]
        for d in days:
            need=int(newwc[str(d.weekday())])
            eligible=[pid for pid in pids if (pid,d.isoformat()) not in un]
            def score(pid):
                consecutive=1 if last[pid] and (d-last[pid][-1]).days==1 else 0
                gap_penalty=1 if last[pid] and (d-last[pid][-1]).days==2 else 0
                return (total[pid]*100 + wknd[pid]*12 + consecutive*30 + gap_penalty*5, total[pid])
            eligible.sort(key=score)
            if len(eligible)<need: failures.append((d.isoformat(),need,len(eligible))); continue
            for slot,pid in enumerate(eligible[:need],1):
                chosen_rows.append({"month_id":mid,"duty_date":d.isoformat(),"slot":slot,"person_id":pid})
                total[pid]+=1; wknd[pid]+=d.weekday()>=5; last[pid].append(d)
        if failures:
            st.error("一部วันจัดไม่ครบ เพราะคนที่ว่างไม่พอ")
            st.dataframe(pd.DataFrame(failures,columns=["วันที่","ต้องการ","จัดได้"]),use_container_width=True,hide_index=True)
        else:
            sb.table("duties").delete().eq("month_id",mid).execute()
            sb.table("duties").insert(chosen_rows).execute()
            sb.table("duty_months").update({"status":"ร่างตาราง"}).eq("id",mid).execute()
            log("auto_schedule",mid,details={"rows":len(chosen_rows)})
            st.success("จัดเวรสำเร็จเป็นร่างตาราง"); st.rerun()

    ds=duties(mid)
    if ds:
        st.divider(); st.subheader("✏️ แก้ไขเวรที่ Algorithm จัด")
        pmap={p["id"]:p["name"] for p in ps}
        did=st.selectbox("เลือกเวร", [x["id"] for x in ds], format_func=lambda x: next(f"{z['duty_date']} — เวร {z['slot']} — {z['people']['name']}" for z in ds if z["id"]==x))
        row=next(x for x in ds if x["id"]==did)
        np=st.selectbox("เปลี่ยนเป็น",list(pmap),format_func=lambda x:pmap[x],key="np")
        if st.button("บันทึกการแก้เวร"):
            if any(x["person_id"]==np and x["unavailable_date"]==row["duty_date"] for x in unavailable(mid)):
                st.error("สมาชิกคนนี้แจ้งไม่ว่างในวันดังกล่าว")
            else:
                sb.table("duties").update({"person_id":np}).eq("id",did).execute()
                log("admin_edit_duty",mid,details={"duty_id":did,"new_person":np}); st.success("แก้เวรแล้ว"); st.rerun()

        c1,c2,c3=st.columns(3)
        with c1:
            if st.button("🔄 Reset ตารางเวร"):
                sb.table("duties").delete().eq("month_id",mid).execute()
                sb.table("duty_months").update({"status":"รอจัดเวร"}).eq("id",mid).execute()
                log("reset_schedule",mid); st.success("Reset ตารางแล้ว"); st.rerun()
        with c2:
            if st.button("🔍 ตรวจสอบตาราง"):
                # report hard violations and fairness stats
                unset={(x["person_id"],x["unavailable_date"]) for x in unavailable(mid)}
                violations=[x for x in ds if (x["person_id"],x["duty_date"]) in unset]
                counts=defaultdict(int)
                for x in ds: counts[x["person_id"]]+=1
                st.write("🟢 ไม่มีการชนวันไม่ว่าง" if not violations else f"🔴 พบ {len(violations)} รายการชนวันไม่ว่าง")
                st.write(f"จำนวนเวรต่ำสุด {min(counts.values())} / สูงสุด {max(counts.values())}")
        with c3:
            if st.button("✅ ประกาศตาราง"):
                sb.table("duty_months").update({"status":"ประกาศแล้ว"}).eq("id",mid).execute()
                log("publish_schedule",mid); st.success("ประกาศแล้ว"); st.rerun()

        # Export
        st.divider(); st.subheader("📤 Export")
        edf=pd.DataFrame([{"วันที่":x["duty_date"],"เวรที่":x["slot"],"ชื่อ":x["people"]["name"],"เบอร์โทร":x["people"]["phone"]} for x in ds])
        st.download_button("📊 ดาวน์โหลด CSV (เปิดด้วย Excel ได้)",edf.to_csv(index=False,encoding="utf-8-sig").encode("utf-8-sig"),
                           file_name=f"เวร_{m['year']}_{m['month']:02d}.csv",mime="text/csv")
        W,H=1800,max(900,180+len(days)*55)
        im=Image.new("RGB",(W,H),"white"); dr=ImageDraw.Draw(im)
        try: fb=ImageFont.truetype("DejaVuSans-Bold.ttf",34); fn=ImageFont.truetype("DejaVuSans.ttf",25)
        except: fb=fn=ImageFont.load_default()
        dr.text((50,30),f"ตารางเวร {month_text(m['year'],m['month'])}",fill="black",font=fb)
        y=100; by=defaultdict(list)
        for x in ds: by[x["duty_date"]].append(x["people"]["name"])
        for d in sorted(by):
            dr.text((50,y),d,fill="black",font=fn); dr.text((330,y)," / ".join(by[d]),fill="black",font=fn); y+=55
        bio=io.BytesIO(); im.save(bio,"JPEG",quality=92)
        st.download_button("🖼️ ดาวน์โหลด JPEG",bio.getvalue(),file_name=f"เวร_{m['year']}_{m['month']:02d}.jpg",mime="image/jpeg")
    else: st.info("ยังไม่มีตารางเวร")

with tabs[5]:
    if not m: st.stop()
    st.subheader("💰 อัตราค่าเวร")
    rr=sb.table("duty_rates").select("*").eq("month_id",mid).execute().data
    rm={x["rate_type"]:float(x["amount"]) for x in rr}
    wd=st.number_input("วันธรรมดา",0.0,100000.0,rm.get("weekday",0.0),10.0)
    we=st.number_input("เสาร์-อาทิตย์",0.0,100000.0,rm.get("weekend",0.0),10.0)
    hd=st.number_input("วันหยุดราชการ/วันหยุดพิเศษ",0.0,100000.0,rm.get("holiday",0.0),10.0)
    if st.button("บันทึกอัตรา"):
        for t,v in [("weekday",wd),("weekend",we),("holiday",hd)]:
            sb.table("duty_rates").upsert({"month_id":mid,"rate_type":t,"amount":v},on_conflict="month_id,rate_type").execute()
        log("update_rates",mid); st.success("บันทึกแล้ว"); st.rerun()
    ds=duties(mid)
    if ds:
        sums=defaultdict(lambda:{"วันธรรมดา":0,"เสาร์-อาทิตย์":0,"วันหยุด":0,"รวม":0})
        for x in ds:
            d=date.fromisoformat(x["duty_date"]); typ="weekend" if d.weekday()>=5 else "weekday"
            nm=x["people"]["name"]; val=we if typ=="weekend" else wd
            sums[nm]["เสาร์-อาทิตย์" if typ=="weekend" else "วันธรรมดา"]+=val; sums[nm]["รวม"]+=val
        st.dataframe(pd.DataFrame([{"ชื่อ":k,**v} for k,v in sums.items()]),use_container_width=True,hide_index=True)

with tabs[6]:
    if not m: st.stop()
    logs=sb.table("audit_logs").select("*").eq("month_id",mid).order("created_at",desc=True).execute().data
    st.dataframe(pd.DataFrame(logs)[["created_at","admin_username","action","details"]] if logs else pd.DataFrame(),
                 use_container_width=True,hide_index=True)

with tabs[7]:
    st.subheader("👑 จัดการ Admin")
    admins=sb.table("admins").select("id,username,role,active,created_at").order("username").execute().data
    st.dataframe(pd.DataFrame(admins),use_container_width=True,hide_index=True)
    au=st.text_input("Username ใหม่"); ap=st.text_input("Password ใหม่",type="password")
    if st.button("เพิ่ม Admin"):
        if au.strip() and ap:
            sb.table("admins").insert({"username":au.strip(),"password_hash":h(ap),"role":"admin","active":True}).execute()
            st.success("เพิ่ม Admin แล้ว"); st.rerun()
    if admins:
        sel=st.selectbox("เลือก Admin", [x["id"] for x in admins], format_func=lambda x:next(a["username"] for a in admins if a["id"]==x))
        if st.button("ปิดการใช้งาน Admin"):
            sb.table("admins").update({"active":False}).eq("id",sel).execute()
            st.success("ปิดการใช้งานแล้ว"); st.rerun()
