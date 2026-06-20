"""registration 模組對外服務（供其他 module 以 service call 取用，避免直接 import model）。

跨 module 慣例見 docs/MODULE_DEPENDENCY.md §2.3：
case_management 收料 view 透過 create_collected_document 落檔，不直接 import RegistrationDocument。
"""
import os
import subprocess
import tempfile
from io import BytesIO

from .models import RegistrationDocument, BeneficialOwnerDeclaration


def create_collected_document(*, doc_type, progress, file,
                              owner_name='', source='client_upload',
                              uploaded_by=None, note=''):
    """收料當下建立一筆登記文件（獨立登記資料庫）。

    owner_id_number 刻意留空：收料當下對應的 Shareholder 可能還不存在（核准才投影進孤島），
    歸戶識別碼由承辦後製或 Phase 2 回填，不在此強制要求（已定案決策）。

    參數：
        doc_type:     RegistrationDocument.DocType 的值（字串）
        progress:     來源登記案 Progress 實例，可為 None（只記來源、刪案不傷檔）
        file:         上傳的檔案物件
        owner_name:   歸戶人姓名（提示用，非必填）
        source:       'client_upload' / 'staff_upload'
        uploaded_by:  上傳人員 User（客戶端上傳時為 None）
        note:         備註
    回傳建立的 RegistrationDocument。
    """
    return RegistrationDocument.objects.create(
        doc_type=doc_type,
        progress=progress,
        file=file,
        owner_name=owner_name,
        source=source,
        uploaded_by_user=uploaded_by,
        note=note,
    )


def remove_collected_document(document_id):
    """軟刪除一份收集文件（客戶端傳錯時移除）。

    供 case_management 收料 view 以 service call 呼叫，避免直接操作 RegistrationDocument。
    找不到（已刪 / 不存在）時靜默略過，呼叫端負責先驗證歸屬。
    """
    doc = RegistrationDocument.objects.filter(pk=document_id, is_deleted=False).first()
    if doc:
        doc.is_deleted = True
        doc.save(update_fields=['is_deleted', 'updated_at'])
    return doc


def _docx_to_pdf(docx_bytes):
    """以容器內 LibreOffice headless 把 docx bytes 轉成 PDF bytes。

    每次給獨立的 UserInstallation profile，避免多 worker 併發轉檔搶 profile lock。
    """
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, 'src.docx')
        with open(src, 'wb') as f:
            f.write(docx_bytes)
        profile = os.path.join(td, 'lo_profile')
        result = subprocess.run(
            ['soffice', '--headless', f'-env:UserInstallation=file://{profile}',
             '--convert-to', 'pdf', '--outdir', td, src],
            capture_output=True, timeout=120,
        )
        pdf_path = os.path.join(td, 'src.pdf')
        if result.returncode != 0 or not os.path.exists(pdf_path):
            raise RuntimeError(
                'LibreOffice 轉 PDF 失敗：'
                + (result.stderr.decode(errors='ignore')[:500] or '未知錯誤')
            )
        with open(pdf_path, 'rb') as f:
            return f.read()


def create_beneficial_owner_declaration(*, progress, company_name, transaction_description,
                                        representative_title, signature_file,
                                        signer_email='', signer_ip=None, signed_at=None):
    """客戶簽署所有權人/實質受益人聲明書 → 套版產 PDF + 建結構化簽署紀錄。

    供 case_management 客戶端簽署 view 以 service call 呼叫，不直接 import registration model。
    流程：docx 範本(含手寫簽名圖 InlineImage) → soffice 轉 PDF → 投影成一筆 RegistrationDocument
    (doc_type=aml_declaration) 落入獨立登記資料庫 → 建 BeneficialOwnerDeclaration 保留簽名圖與留痕。
    簽署即凍結快照（用當下範本產出後存檔，不事後重生）。

    參數：
        progress:                來源登記案 Progress 實例，可為 None
        company_name:            本法人名稱（客戶校對後值）
        transaction_description: 所從事之交易
        representative_title:    代表人職稱
        signature_file:          手寫簽名檔（file-like，PNG）
        signer_email / signer_ip / signed_at: 簽署留痕
    回傳簽好的 RegistrationDocument（供呼叫端掛上 CaseTask）。
    """
    from django.core.files.base import ContentFile
    from django.utils import timezone
    from docxtpl import DocxTemplate, InlineImage
    from docx.shared import Mm

    signed_at = signed_at or timezone.now()
    sig_bytes = signature_file.read()

    # 1) 套版產 PDF
    tpl_path = os.path.join(os.path.dirname(__file__),
                            'document_templates', 'aml_beneficial_owner_declaration.docx')
    tpl = DocxTemplate(tpl_path)
    tpl.render({
        'companyName': company_name,
        'transaction': transaction_description,
        'repTitle': representative_title,
        'signYear': str(signed_at.year - 1911),  # 民國年
        'signMonth': f'{signed_at.month:02d}',
        'signDay': f'{signed_at.day:02d}',
        'repSig': InlineImage(tpl, BytesIO(sig_bytes), width=Mm(45)),
    })
    docx_buf = BytesIO()
    tpl.save(docx_buf)
    pdf_bytes = _docx_to_pdf(docx_buf.getvalue())

    # 2) 簽好的 PDF 投影進獨立登記資料庫
    pdf_name = f'beneficial_owner_declaration_{company_name}_{signed_at:%Y%m%d}.pdf'
    document = RegistrationDocument.objects.create(
        doc_type=RegistrationDocument.DocType.AML_DECLARATION,
        progress=progress,
        file=ContentFile(pdf_bytes, name=pdf_name),
        owner_name=company_name,
        source='client_upload',
    )

    # 3) 結構化簽署紀錄（保留手寫簽名圖 + 留痕）
    BeneficialOwnerDeclaration.objects.create(
        progress=progress,
        company_name=company_name,
        transaction_description=transaction_description,
        representative_title=representative_title,
        representative_signature=ContentFile(sig_bytes, name='signature.png'),
        signed_at=signed_at,
        signer_email=signer_email,
        signer_ip=signer_ip,
        rendered_document=document,
    )
    return document
