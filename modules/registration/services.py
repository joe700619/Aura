"""registration 模組對外服務（供其他 module 以 service call 取用，避免直接 import model）。

跨 module 慣例見 docs/MODULE_DEPENDENCY.md §2.3：
case_management 收料 view 透過 create_collected_document 落檔，不直接 import RegistrationDocument。
"""
import os
import subprocess
import tempfile
from io import BytesIO

from .models import RegistrationDocument, BeneficialOwnerDeclaration, DraftConfirmation, Progress


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


# ── 公司法22-1申報：供記帳側年度批次下推建立（idempotent）─────────────────
# 記帳客戶勾選「由本所申報 22-1」為唯一真相，每年由記帳模組批次呼叫，
# 依統編 get_or_create CompanyFiling 主檔 + 當年度 ANNUAL FilingHistory 子檔。
# 帳單不在此處理——500 服務費由 5 月年度帳單批次自動帶入。

def create_or_refresh_annual_filing(year, *, unified_business_no, company_name,
                                    line_id='', room_id='', main_contact='',
                                    mobile='', phone='', address=''):
    """依統編建/取 CompanyFiling 主檔，並確保當年度有一筆「年度申報」歷程。

    idempotent：同統編、同年度重跑只會 get、不會重建。
    回傳 (filing_history, created)；無統編則回傳 (None, False)。

    註：CompanyFiling.unified_business_no 非 unique，這裡用 filter().first()
    而非 get_or_create，避免歷史重複資料造成 MultipleObjectsReturned 中斷批次。
    """
    from django.utils import timezone
    from .models import CompanyFiling, FilingHistory

    ubn = (unified_business_no or '').strip()
    if not ubn:
        return None, False

    filing_parent = CompanyFiling.objects.filter(unified_business_no=ubn).first()
    if filing_parent is None:
        filing_parent = CompanyFiling.objects.create(
            unified_business_no=ubn,
            company_name=company_name or '',
            line_id=line_id or '',
            room_id=room_id or '',
            main_contact=main_contact or '',
            mobile=mobile or '',
            phone=phone or '',
            address=address or '',
            note='由記帳客戶年度22-1批次自動建立基本資料',
        )

    history, created = FilingHistory.objects.get_or_create(
        company_filing=filing_parent,
        year=year,
        category=FilingHistory.FilingCategory.ANNUAL,
        defaults={'filing_date': timezone.now().date()},
    )
    return history, created


# ── 商工登記稿本確認：正式送件前給客戶線上校對 + 手寫簽名 ──────────────
# 承辦上傳稿本（doc_type=draft）→ 發送 token 連結（LINE/Email）→ 客戶唯讀檢視 + 手寫簽名 →
# 簽署即凍結快照。一個 Progress 同時只一筆 active(sent)；重傳/重發舊筆自動 voided。

DRAFT_CONFIRMATION_VALID_DAYS = 7

# 用印授權標準文字的後備預設：實際以 SystemParameter 'SEAL_AUTHORIZATION_TEXT' 為準
# （admin 可改）。發送當下會把當時文字凍進 authorization_text_snapshot。
DEFAULT_SEAL_AUTHORIZATION_TEXT = (
    '本人/本公司茲此授權 貴所就上列經本人確認無誤之登記稿本，'
    '於辦理本案商工登記期間，代為使用本人/本公司之印鑑章（大、小章）'
    '用印於各項登記申請書件，並據以向主管機關提出申請。'
    '本授權之效力以辦竣本案登記為限。'
)


def get_seal_authorization_text():
    """取得用印授權標準文字（SystemParameter 優先，未設則用後備預設）。"""
    from modules.system_config.helpers import get_system_param
    return get_system_param('SEAL_AUTHORIZATION_TEXT', default=DEFAULT_SEAL_AUTHORIZATION_TEXT)


def list_draft_documents(progress):
    """回傳某登記案目前的稿本清單（未刪除），給工作台與發送時取用。"""
    return RegistrationDocument.objects.filter(
        progress=progress,
        doc_type=RegistrationDocument.DocType.DRAFT,
        is_deleted=False,
    ).order_by('created_at')


def _void_active_draft_confirmations(progress):
    """把該登記案目前 active(sent) 的確認單轉為 voided（重傳/重發時呼叫）。

    已確認(confirmed)的歷史紀錄不動，保留留痕。
    """
    from django.utils import timezone
    DraftConfirmation.objects.filter(
        progress=progress, status=DraftConfirmation.Status.SENT,
    ).update(status=DraftConfirmation.Status.VOIDED, updated_at=timezone.now())


def create_draft_document(*, progress, file, note='', uploaded_by=None):
    """承辦上傳一份稿本（doc_type=draft）。

    上傳新稿本代表內容有變，會把該案目前 active 的確認單自動作廢（客戶須就新版重新確認）。
    回傳建立的 RegistrationDocument。
    """
    _void_active_draft_confirmations(progress)
    return RegistrationDocument.objects.create(
        doc_type=RegistrationDocument.DocType.DRAFT,
        progress=progress,
        file=file,
        owner_name=progress.company_name,
        source=RegistrationDocument.Source.STAFF_UPLOAD,
        uploaded_by_user=uploaded_by,
        note=note,
    )


def remove_draft_document(progress, document_id):
    """承辦移除一份稿本（軟刪）。移除也代表稿本集有變，連帶作廢 active 確認單。

    回傳被刪的文件（找不到/非本案則回 None）。
    """
    doc = RegistrationDocument.objects.filter(
        pk=document_id, progress=progress,
        doc_type=RegistrationDocument.DocType.DRAFT, is_deleted=False,
    ).first()
    if doc:
        _void_active_draft_confirmations(progress)
        doc.is_deleted = True
        doc.save(update_fields=['is_deleted', 'updated_at'])
    return doc


def create_draft_confirmation(*, progress, documents, seal_authorization,
                              recipient_email='', recipient_line_id=''):
    """建立並寄發一筆稿本確認單（status=sent），凍結要確認的文件清單。

    先作廢該案既有 active 確認單（保證同時只一筆），再建新單：
    - documents：凍結進 M2M 的稿本文件 queryset/list
    - seal_authorization：含用印授權時，把標準文字凍進 authorization_text_snapshot
    - recipient_*：留痕「寄給誰」（實際發送由 view 處理）

    回傳建立的 DraftConfirmation。連結到期 = 現在 + 7 天。
    """
    from django.utils import timezone

    _void_active_draft_confirmations(progress)

    now = timezone.now()
    confirmation = DraftConfirmation.objects.create(
        progress=progress,
        status=DraftConfirmation.Status.SENT,
        seal_authorization=bool(seal_authorization),
        authorization_text_snapshot=get_seal_authorization_text() if seal_authorization else '',
        sent_at=now,
        expires_at=now + timezone.timedelta(days=DRAFT_CONFIRMATION_VALID_DAYS),
        recipient_email=recipient_email or '',
        recipient_line_id=recipient_line_id or '',
    )
    confirmation.documents.set(documents)
    return confirmation


def confirm_draft_confirmation(confirmation, *, signature_file, signer_name,
                               signer_email='', signer_ip=None):
    """客戶按「確認並簽署」時呼叫：凍結手寫簽名 + 留痕，狀態轉 confirmed。

    idempotent：已確認則直接回傳，不重複寫入（防重複送出）。
    用印授權旗標 seal_authorized 依當初是否含授權一併落定。
    """
    from django.core.files.base import ContentFile
    from django.db import transaction
    from django.utils import timezone

    with transaction.atomic():
        if confirmation.status == DraftConfirmation.Status.CONFIRMED:
            return confirmation

        sig_bytes = signature_file.read() if hasattr(signature_file, 'read') else signature_file
        confirmation.signature_image = ContentFile(sig_bytes, name='signature.png')
        confirmation.signed_at = timezone.now()
        confirmation.signer_name = signer_name or ''
        confirmation.signer_email = signer_email or ''
        confirmation.signer_line_id = confirmation.recipient_line_id
        confirmation.signer_ip = signer_ip
        confirmation.seal_authorized = confirmation.seal_authorization
        confirmation.status = DraftConfirmation.Status.CONFIRMED
        confirmation.save()
    return confirmation


# ── 公司登記委任書：發送 token 連結給客戶線上閱覽 + 手寫簽名 ──────────────
# 承辦在委任書工作台按發送 → 用 active 範本 + 進度表資料渲染並凍結快照（含報價明細）→
# 客戶免登入閱覽 → 簽署/婉拒，service 同步回寫 Progress.mandate_return。
# 一個 Progress 同時只一筆 active(sent)；重發舊筆自動 voided。

MANDATE_VALID_DAYS = 7


def summarize_quotation(quotation_data):
    """把進度表的報價單資料整理成「明細 + 合計」的快照結構。

    分類規則與報價單前端（components/quotation_table.html）一致：
    服務項目名稱 8 開頭＝預收款（−）、9 開頭＝代墊款（+）、其餘＝服務費用（+），
    未收款合計 = 服務費用 + 代墊款 − 預收款。
    """
    items = [i for i in quotation_data if isinstance(i, dict)] \
        if isinstance(quotation_data, list) else []

    def _amount(item):
        try:
            return int(item.get('amount') or 0)
        except (TypeError, ValueError):
            return 0

    service_fee_total = advance_total = pre_collection_total = 0
    for item in items:
        name = (item.get('service_name') or '').strip()
        amount = _amount(item)
        if name.startswith('9'):
            advance_total += amount
        elif name.startswith('8'):
            pre_collection_total += amount
        else:
            service_fee_total += amount

    return {
        'items': [
            {
                'service_name': (i.get('service_name') or '').strip(),
                'amount': _amount(i),
                'remark': (i.get('remark') or '').strip(),
            }
            for i in items
        ],
        'service_fee_total': service_fee_total,
        'advance_total': advance_total,
        'pre_collection_total': pre_collection_total,
        'uncollected_total': service_fee_total + advance_total - pre_collection_total,
    }


def render_mandate_html(template, progress, quotation_summary):
    """用範本版本 + 進度表資料渲染委任書條款本文。

    工作台預覽與發送凍結都走這支，確保所見即所簽。
    """
    from django.template import Context, Template
    from django.utils import timezone

    case_type_labels = dict(Progress.CASE_TYPE_CHOICES)
    case_types = '、'.join(
        case_type_labels.get(ct, ct) for ct in (progress.case_type or [])
    )
    tpl = Template(template.body_html)
    ctx = Context({
        'company_name': progress.company_name,
        'unified_business_no': progress.unified_business_no or '',
        'main_contact': progress.main_contact or '',
        'acceptance_date': progress.acceptance_date,
        'case_types': case_types,
        'service_fee_total': quotation_summary['service_fee_total'],
        'advance_total': quotation_summary['advance_total'],
        'pre_collection_total': quotation_summary['pre_collection_total'],
        'uncollected_total': quotation_summary['uncollected_total'],
        'today': timezone.now().date(),
    })
    return tpl.render(ctx)


def _void_active_mandates(progress):
    """把該登記案目前 active(sent) 的委任書轉為 voided（重發時呼叫）。

    已簽署/已婉拒的歷史紀錄不動，保留留痕。
    """
    from django.utils import timezone
    from .models import RegistrationMandate
    RegistrationMandate.objects.filter(
        progress=progress, status=RegistrationMandate.Status.SENT,
    ).update(status=RegistrationMandate.Status.VOIDED, updated_at=timezone.now())


def create_registration_mandate(*, progress, recipient_email='', recipient_line_id=''):
    """建立並寄發一筆登記委任書（status=sent），發送當下凍結內容。

    先作廢該案既有 active 委任書（保證同時只一筆），再建新單：
    - 用 active 範本 + 進度表資料渲染條款，凍進 rendered_snapshot
    - 報價單明細與合計凍進 quotation_snapshot
    - 同步 Progress.mandate_return → 簽核中
    無 active 範本時 raise ValueError（部署須先跑 init_registration_mandate）。

    回傳建立的 RegistrationMandate。連結到期 = 現在 + 7 天。
    """
    from django.utils import timezone
    from .models import RegistrationMandate, RegistrationMandateTemplate

    template = RegistrationMandateTemplate.get_active()
    if template is None:
        raise ValueError('尚無使用中的登記委任書範本，請先於後台建立（或執行 init_registration_mandate）。')

    _void_active_mandates(progress)

    quotation_summary = summarize_quotation(progress.quotation_data)
    now = timezone.now()
    mandate = RegistrationMandate.objects.create(
        progress=progress,
        status=RegistrationMandate.Status.SENT,
        template_version=template,
        rendered_snapshot=render_mandate_html(template, progress, quotation_summary),
        quotation_snapshot=quotation_summary,
        sent_at=now,
        expires_at=now + timezone.timedelta(days=MANDATE_VALID_DAYS),
        recipient_email=recipient_email or '',
        recipient_line_id=recipient_line_id or '',
    )
    if progress.mandate_return != Progress.MandateReturn.SIGNING:
        progress.mandate_return = Progress.MandateReturn.SIGNING
        progress.save(update_fields=['mandate_return', 'updated_at'])
    return mandate


def sign_registration_mandate(mandate, *, signature_file, signer_name,
                              signer_email='', signer_ip=None):
    """客戶按「同意委任並簽署」時呼叫：凍結手寫簽名 + 留痕，狀態轉 signed。

    idempotent：已簽署則直接回傳，不重複寫入（防重複送出）。
    同步 Progress.mandate_return → 核准。
    """
    from django.core.files.base import ContentFile
    from django.db import transaction
    from django.utils import timezone
    from .models import RegistrationMandate

    with transaction.atomic():
        if mandate.status == RegistrationMandate.Status.SIGNED:
            return mandate

        sig_bytes = signature_file.read() if hasattr(signature_file, 'read') else signature_file
        mandate.signature_image = ContentFile(sig_bytes, name='signature.png')
        mandate.signed_at = timezone.now()
        mandate.signer_name = signer_name or ''
        mandate.signer_email = signer_email or ''
        mandate.signer_line_id = mandate.recipient_line_id
        mandate.signer_ip = signer_ip
        mandate.status = RegistrationMandate.Status.SIGNED
        mandate.save()

        progress = mandate.progress
        progress.mandate_return = Progress.MandateReturn.APPROVED
        progress.save(update_fields=['mandate_return', 'updated_at'])
    return mandate


def decline_registration_mandate(mandate, *, reason='', signer_ip=None):
    """客戶按「暫不委任」時呼叫：留痕婉拒原因，狀態轉 declined。

    已簽署/已婉拒則直接回傳不動（防重複送出）。
    同步 Progress.mandate_return → 拒絕。
    """
    from django.db import transaction
    from django.utils import timezone
    from .models import RegistrationMandate

    with transaction.atomic():
        if mandate.status in (RegistrationMandate.Status.SIGNED,
                              RegistrationMandate.Status.DECLINED):
            return mandate

        mandate.status = RegistrationMandate.Status.DECLINED
        mandate.declined_at = timezone.now()
        mandate.decline_reason = reason or ''
        mandate.signer_ip = signer_ip
        mandate.save(update_fields=['status', 'declined_at', 'decline_reason',
                                    'signer_ip', 'updated_at'])

        progress = mandate.progress
        progress.mandate_return = Progress.MandateReturn.REJECTED
        progress.save(update_fields=['mandate_return', 'updated_at'])
    return mandate


def list_paper_mandates(progress):
    """回傳某登記案的紙本簽回委任書掃描檔清單（未刪除）。"""
    return RegistrationDocument.objects.filter(
        progress=progress,
        doc_type=RegistrationDocument.DocType.SIGNED_MANDATE,
        is_deleted=False,
    ).order_by('created_at')


def create_paper_mandate(*, progress, file, note='', uploaded_by=None):
    """承辦上傳一份客戶紙本簽回的委任書掃描檔。

    不走電子簽署的客戶用這條路：掃描檔落入登記資料庫（doc_type=signed_mandate），
    並同步 Progress.mandate_return → 核准（視同已簽回）。
    回傳建立的 RegistrationDocument。
    """
    doc = RegistrationDocument.objects.create(
        doc_type=RegistrationDocument.DocType.SIGNED_MANDATE,
        progress=progress,
        file=file,
        owner_name=progress.company_name,
        owner_id_number=progress.unified_business_no or '',
        source=RegistrationDocument.Source.STAFF_UPLOAD,
        uploaded_by_user=uploaded_by,
        note=note,
    )
    if progress.mandate_return != Progress.MandateReturn.APPROVED:
        progress.mandate_return = Progress.MandateReturn.APPROVED
        progress.save(update_fields=['mandate_return', 'updated_at'])
    return doc


def remove_paper_mandate(progress, document_id):
    """承辦移除一份紙本簽回掃描檔（軟刪，傳錯檔時用）。

    刻意不回退 mandate_return：委任狀態由承辦在進度表自行調整，避免誤刪連動。
    回傳被刪的文件（找不到/非本案則回 None）。
    """
    doc = RegistrationDocument.objects.filter(
        pk=document_id, progress=progress,
        doc_type=RegistrationDocument.DocType.SIGNED_MANDATE, is_deleted=False,
    ).first()
    if doc:
        doc.is_deleted = True
        doc.save(update_fields=['is_deleted', 'updated_at'])
    return doc


def get_ubns_with_annual_filing(year):
    """回傳「該年度已建年度申報歷程」的統編集合。

    一條 query，給記帳側 22-1 清單頁標示「今年已建記錄」狀態用，避免 N+1。
    """
    from .models import FilingHistory
    return set(
        FilingHistory.objects
        .filter(year=year, category=FilingHistory.FilingCategory.ANNUAL)
        .values_list('company_filing__unified_business_no', flat=True)
    )
