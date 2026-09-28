-- เพิ่มประเภทสมาชิก: พี่ / น้องใหม่
ALTER TABLE public.people
ADD COLUMN IF NOT EXISTS member_type text NOT NULL DEFAULT 'พี่';

UPDATE public.people
SET member_type = 'พี่'
WHERE member_type IS NULL OR member_type = '';

ALTER TABLE public.people
DROP CONSTRAINT IF EXISTS people_member_type_check;

ALTER TABLE public.people
ADD CONSTRAINT people_member_type_check
CHECK (member_type IN ('พี่','น้องใหม่'));

-- กำหนดจำนวนพี่/น้องใหม่ต่อวันของแต่ละเดือน
ALTER TABLE public.duty_months
ADD COLUMN IF NOT EXISTS senior_per_day integer NOT NULL DEFAULT 2;

ALTER TABLE public.duty_months
ADD COLUMN IF NOT EXISTS newbie_per_day integer NOT NULL DEFAULT 2;

ALTER TABLE public.duty_months
DROP CONSTRAINT IF EXISTS duty_months_team_rule_check;

ALTER TABLE public.duty_months
ADD CONSTRAINT duty_months_team_rule_check
CHECK (senior_per_day >= 0 AND newbie_per_day >= 0);

-- ตรวจสอบผล
SELECT id, name, member_type
FROM public.people
ORDER BY name;

SELECT id, year, month, senior_per_day, newbie_per_day
FROM public.duty_months
ORDER BY year DESC, month DESC;
