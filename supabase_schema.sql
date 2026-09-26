
create extension if not exists "pgcrypto";

create table if not exists people (
 id uuid primary key default gen_random_uuid(),
 name text not null unique,
 phone text,
 active boolean not null default true,
 created_at timestamptz not null default now()
);

create table if not exists admins (
 id uuid primary key default gen_random_uuid(),
 username text not null unique,
 password_hash text not null,
 role text not null default 'admin',
 active boolean not null default true,
 created_at timestamptz not null default now()
);

create table if not exists duty_months (
 id uuid primary key default gen_random_uuid(),
 year int not null,
 month int not null check(month between 1 and 12),
 status text not null default 'รอรับวันไม่ว่าง',
 unavailable_start date not null,
 unavailable_deadline date not null,
 max_unavailable_edits int not null default 2,
 admin_override_open boolean not null default false,
 weekday_counts jsonb not null default '{"0":4,"1":3,"2":4,"3":3,"4":3,"5":3,"6":3}'::jsonb,
 created_at timestamptz not null default now(),
 unique(year,month)
);

create table if not exists month_members (
 month_id uuid references duty_months(id) on delete cascade,
 person_id uuid references people(id) on delete cascade,
 primary key(month_id,person_id)
);

create table if not exists unavailable_days (
 id uuid primary key default gen_random_uuid(),
 month_id uuid references duty_months(id) on delete cascade,
 person_id uuid references people(id) on delete cascade,
 unavailable_date date not null,
 edit_no int not null default 1,
 created_at timestamptz not null default now(),
 unique(month_id,person_id,unavailable_date)
);

create table if not exists duties (
 id uuid primary key default gen_random_uuid(),
 month_id uuid references duty_months(id) on delete cascade,
 duty_date date not null,
 slot int not null,
 person_id uuid references people(id),
 created_at timestamptz not null default now(),
 unique(month_id,duty_date,slot)
);

create table if not exists duty_rates (
 id uuid primary key default gen_random_uuid(),
 month_id uuid references duty_months(id) on delete cascade,
 rate_type text not null,
 amount numeric(12,2) not null default 0,
 unique(month_id,rate_type)
);

create table if not exists audit_logs (
 id uuid primary key default gen_random_uuid(),
 created_at timestamptz not null default now(),
 action text not null,
 month_id uuid,
 person_id uuid,
 admin_username text,
 details jsonb
);

-- สร้าง Admin ตัวแรกด้วยคำสั่งตัวอย่างด้านล่าง หลังจากคำนวณ SHA-256 ของ password:
-- insert into admins(username,password_hash,role,active)
-- values ('admin','ใส่_sha256_ตรงนี้','admin',true);

-- ถ้าใช้ Supabase ฝั่ง production ควรเพิ่ม RLS/Policies ตามรูปแบบการ authentication
-- ของระบบที่เลือกก่อนเปิดใช้จริงกับข้อมูลบุคคล
