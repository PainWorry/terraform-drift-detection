# ร่างอีเมลประสานงาน: คำขอทรัพยากรสำหรับทดสอบระบบ Terraform Drift Detection

**Subject:** คำขอข้อมูลทรัพยากรสำหรับทดสอบระบบ Terraform Configuration Drift Detection (Staging Validation)  
**To:** Senior Developer  
**From:** HerrenK (Cloud Engineer)  

---

1. **ที่มาและความพร้อมของระบบ (Background & Readiness):**  
   ผมได้พัฒนาและตรวจสอบระบบ Automated Drift Detection Pipeline คือระบบแจ้งเตือนหากมีคนแก้ไข AWS Environment โดยไม่แจ้ง บนสถาปัตยกรรม Terraform 1.10+ (รองรับ S3 Native Lockfile และ Read-Only OIDC) พร้อมชุดทดสอบ Canary Security Group เสร็จสิ้นแล้วในระดับ Local

2. **รายการทรัพยากรที่จำเป็นสำหรับ Live Drill (Required AWS Resources):**  
   เพื่อดำเนินการทดสอบ End-to-End บน Staging Environment ขอความอนุเคราะห์ข้อมูล Configuration 3 รายการ:
   - **S3 State Bucket Name (`TF_STATE_BUCKET`):** สำหรับชี้ Backend State เก็บ State Canary
   - **AWS IAM Role ARN (`AWS_DRIFT_SCANNER_ROLE_ARN`):** Role สำหรับ GitHub Actions OIDC (สิทธิ์ Read-Only ตรวจสอบ Infrastructure และอ่าน State)
   - **Staging VPC ID (`vpc_id`):** สำหรับทดสอบการ Deploy `onelink-staging-drift-canary-sg`

3. **แผนการทดสอบเมื่อได้รับทรัพยากร (Next Action Steps):**  
   ทีมจะดำเนินการ Initial Apply ชุดทดสอบ Canary จากนั้นจะจำลองการแก้ไข Out-of-band ผ่าน AWS Console เพื่อยืนยันว่า Pipeline ตรวจจับความเปลี่ยนแปลงได้อย่างแม่นยำ พร้อมทดสอบขั้นตอน Reconcile State กลับสู่ Baseline โดยไม่ส่งผลกระทบต่อ Production Workload

4. **ประเด็นความจำเป็นของ ClickUp API (ClickUp API Requirement):**  
   **ClickUp API ไม่จำเป็นสำหรับการทดสอบ Phase 1** โดยระบบสามารถตรวจจับ Drift และแจ้งเตือนผ่าน GitHub Actions Log / Summary ได้อย่างสมบูรณ์ สำหรับ `CLICKUP_API_TOKEN` และ `CLICKUP_LIST_ID` สามารถส่งมอบใน Phase 2 เพื่อเปิดใช้งานระบบสร้างตั๋ว Urgent อัตโนมัติในภายหลังได้ครับ
