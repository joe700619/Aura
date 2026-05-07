from django.views.generic import TemplateView


class LandingView(TemplateView):
    template_name = "public_site/landing.html"


FO_STEPS = [
    {"n": "01", "t": "信任建立", "dur": "1-2 個月", "weeks": "約 4-8 週",
     "summary": "與家族成員一對一訪談，理解每個人的真實想法與顧慮。",
     "prepare": ["家族成員名單（含配偶、子女、未來想納入的對象）",
                 "現任經營者的簡歷與接班想法",
                 "過去曾諮詢過的律師、會計師資料（若有）"]},
    {"n": "02", "t": "財富盤點", "dur": "2-3 個月", "weeks": "約 8-12 週",
     "summary": "建立完整的家族資產地圖，召開第一次家族共識會議。",
     "prepare": ["公司股權結構（各家公司、持股比例、董監名單）",
                 "不動產清冊（含登記名義、貸款、租賃狀況）",
                 "金融資產（PB 對帳單、保單、海外帳戶）",
                 "近三年個人與公司報稅資料"]},
    {"n": "03", "t": "結構設計", "dur": "4-6 個月", "weeks": "約 16-24 週",
     "summary": "規劃傳承架構與稅務藍圖，逐項與家族確認後執行。",
     "prepare": ["家族成員的婚姻、財產協議現況",
                 "公司章程、股東協議、員工持股辦法",
                 "已執行的信託、保險、贈與紀錄",
                 "希望保留與希望調整的項目清單"]},
    {"n": "04", "t": "治理落地", "dur": "長期陪跑", "weeks": "12 個月起 · 持續",
     "summary": "簽訂家族憲章，建立家族會議節奏，每季度回顧與調整。",
     "prepare": ["家族會議的固定時間與召集人",
                 "下一代的職涯規劃與接班時程",
                 "重大決策的授權範圍",
                 "家族慈善、品牌、共同資產的方向"]},
]


class FamilyOfficeView(TemplateView):
    template_name = "public_site/family_office.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["fo_steps"] = FO_STEPS
        return ctx


class BookkeepingView(TemplateView):
    template_name = "public_site/services/bookkeeping.html"


class AttestationView(TemplateView):
    template_name = "public_site/services/attestation.html"


REG_STEPS = [
    {"n": "01", "t": "前置諮詢", "dur": "1-2 天", "weeks": "Day 1-2",
     "summary": "確認公司型態與資本額，選擇最適合的登記方式。",
     "prepare": ["負責人身分證正反面", "預計營業項目清單", "預計資本額（建議 100 萬以上）", "是否有合夥人或股東（若有，請提供名單）"]},
    {"n": "02", "t": "名稱預查", "dur": "3-5 天", "weeks": "Day 3-7",
     "summary": "向經濟部申請公司名稱預查，確認名稱可使用。",
     "prepare": ["預備 3-5 個公司名稱候選（依優先序排列）", "確認業別（中文行業分類）", "確認公司所在縣市"]},
    {"n": "03", "t": "資本額簽證", "dur": "2-3 天", "weeks": "Day 7-9",
     "summary": "股東將資本額匯入籌備帳戶，由會計師出具驗資報告。",
     "prepare": ["股東名單與出資比例", "各股東匯款至籌備帳戶（需同日匯入）", "銀行存款餘額證明（由銀行開立）"]},
    {"n": "04", "t": "設立登記", "dur": "5-7 天", "weeks": "Day 9-14",
     "summary": "向經濟部商業司送件，完成公司法人資格設立。",
     "prepare": ["公司章程（我們代為擬定）", "股東同意書 / 股東會議事錄", "負責人印鑑章（個人）", "公司印章（大小章，可委託我們刻製）"]},
    {"n": "05", "t": "營業登記", "dur": "3-5 天", "weeks": "Day 14-18",
     "summary": "向國稅局申請統一發票，完成稅籍登記。",
     "prepare": ["公司設立登記表（設立後取得）", "營業地址租約或產權證明", "負責人身分證", "決定開立發票週期（雙月 or 月開）"]},
    {"n": "06", "t": "開業就緒", "dur": "依需求", "weeks": "Day 18+",
     "summary": "銀行開戶、勞健保加保、取得發票，正式開始營業。",
     "prepare": ["公司設立相關文件（全套）", "第一位員工資料（勞健保加保用）", "選定往來銀行（建議提前預約）", "開業 30 天清單（我們提供）"]},
]


class RegistrationView(TemplateView):
    template_name = "public_site/services/registration.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["reg_steps"] = REG_STEPS
        return ctx


class AdvisoryView(TemplateView):
    template_name = "public_site/services/advisory.html"


class _ToolView(TemplateView):
    current_tool = ""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["current_tool"] = self.current_tool
        return ctx


class LaborInsuranceView(_ToolView):
    template_name = "public_site/tools/labor_insurance.html"
    current_tool = "labor"


class PaymentReceiptView(_ToolView):
    template_name = "public_site/tools/payment_receipt.html"
    current_tool = "payment"


class StartupAnalysisView(_ToolView):
    template_name = "public_site/tools/startup_analysis.html"
    current_tool = "startup"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["concerns"] = [
            "不知道該登記行號還是公司",
            "不知道要不要開發票 / 開哪種發票",
            "不確定要不要請會計師記帳",
            "對勞健保投保沒概念",
            "想知道有哪些政府補助或減稅",
            "擔心稅務申報出錯被罰",
            "想規劃股東結構（多人合資）",
            "其他（諮詢時詳談）",
        ]
        return ctx


class WithholdingTaxView(_ToolView):
    template_name = "public_site/tools/withholding_tax.html"
    current_tool = "withholding"
