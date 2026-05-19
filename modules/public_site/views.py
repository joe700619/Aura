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
     "prepare": ["負責人身分證正反面", "預計營業項目清單", "預計資本額（無最低資本額限制）", "是否有合夥人或股東（若有，請提供名單）"]},
    {"n": "02", "t": "名稱預查", "dur": "3-5 天", "weeks": "Day 3-7",
     "summary": "向經濟部申請公司名稱預查，確認名稱可使用。",
     "prepare": ["預備 3-5 個公司名稱候選（依優先序排列）", "確認業別（中文行業分類）", "確認公司所在縣市"]},
    {"n": "03", "t": "資本額簽證", "dur": "2-3 天", "weeks": "Day 7-9",
     "summary": "股東將資本額匯入籌備帳戶，由會計師出具驗資報告。",
     "prepare": ["股東名單與出資比例", "各股東匯款至籌備帳戶", "銀行存款餘額證明（由銀行開立）"]},
    {"n": "04", "t": "設立登記", "dur": "5-7 天", "weeks": "Day 9-14",
     "summary": "向經濟部商業司送件，完成公司法人資格設立。",
     "prepare": ["公司章程（可由我們代為擬定）", "股東同意書 / 股東會議事錄", "房屋稅單及租約", "公司印章（大小章，可委託我們刻製）"]},
    {"n": "05", "t": "營業登記", "dur": "3-5 天", "weeks": "Day 14-18",
     "summary": "向國稅局申請統一發票，完成稅籍登記。",
     "prepare": ["公司設立登記表（設立後取得）", "營業地址租約或產權證明", "負責人身分證", "決定開立發票週期（雙月 or 月開）"]},
    {"n": "06", "t": "開業就緒", "dur": "依需求", "weeks": "Day 18+",
     "summary": "銀行開戶、勞健保加保、取得發票，正式開始營業。",
     "prepare": ["公司設立相關文件", "第一位員工資料（勞健保加保用）", "選定往來銀行（建議提前預約）", "領取購票證(購買發票使用)"]},
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
        ctx["sa_steps"] = [
            {
                "id": "purpose", "title": "您的設立目的為何？",
                "options": ["最省稅", "減少法律責任", "募集資金"],
                "tips": [
                    {"q": "什麼情況下最省稅？", "a": "因為稅制的關係，公司需要額外繳納20%的營利事業所得稅，每年分配股利給股東時，還需再繳納一次個人所得稅；因此設立行號繳納的稅捐將小於公司。"},
                    {"q": "什麼情況下可以減少法律責任？", "a": "設立公司可以減少法律責任，因為公司有獨立的法人格，股東只需要負擔有限責任，最多賠光出資額即可，但如果是行號，一旦發生食物中毒等情況，股東需要負擔無限的賠償責任，換言之，需要拿自己的財產出來賠償。"},
                    {"q": "什麼情況下適合募集資金？", "a": "股份有限公司及閉鎖型股份有限公司，均可對外招募資金，也能夠採用特別股/無面額股份等設計，打造保障原始股東的股權架構，因此適合需要募資的團隊；就算以後團隊經營方向有紛爭，也能透過股權設計來保障原始股東的權益。"},
                ],
            },
            {
                "id": "shareholders", "title": "股東人數？",
                "options": ["1 人", "2 ～ 5 人", "5 人以上"],
                "tips": [
                    {"q": "1 人可以開公司嗎？", "a": "絕對可以! 1 個人也可以成立「有限公司」並擔任唯一的股東兼董事，無須尋找其他人掛名，決議也最為快速。"},
                    {"q": "只有一個人可以開設股份有限公司嗎？", "a": "不行喔，股份有限公司至少需要兩名自然人股東，或是由單一法人股東成立，因此只有自己一個人不能設立股份有限公司。"},
                    {"q": "董事一定是股東嗎？", "a": "不一定喔，「有限公司」是一定具備股東身分；「股份有限公司」董事可以不用是股東，例如很多獨立董事是沒有持股的，但是也能擔任獨立董事。"},
                    {"q": "股東人數5人以上，適合怎樣的組織型態?", "a": "相較於有限公司的基礎是「人合」的概念，股份有限公司的基礎是「資合」的概念，因此股東人數較多時，股份有限公司會更適合，當有重大決議時，採用「股東會」決議，股東可以依照持股比例表決，因此更適合股東人數較多的情況。"},
                ],
            },
            {
                "id": "entity", "title": "您偏好的組織型態？",
                "options": ["行號", "有限公司", "股份有限公司", "尚未決定 — 想要建議"],
                "tips": [
                    {"q": "公司和行號最大的差別在哪？", "a": "行號需要負擔無限責任，且無法人格，因此不適合有風險的業務；公司則有獨立法人格，股東只需要負擔有限責任，適合各種規模與風險的業務。"},
                    {"q": "行號以後做大賺錢了，可以直接改成公司嗎？", "a": "不行，由於行號沒有法人格，因此若要改成公司，只能重新設立一個公司。"},
                    {"q": "個人工作室、企業社、商行等是甚麼組織型態？", "a": "這些都是屬於行號，只要是結尾不是「有限公司」或「股份有限公司」的，都屬於行號。"},
                    {"q": "有限公司和股份有限公司怎麼選？", "a": "有限公司適合小型親友團隊，手續簡單無須頻繁召開董事會。若未來想找各大外部天使投資人或創投募資，則需設立股份有限公司以便於彈性交易股權。"},
                ],
            },
            {
                "id": "capital", "title": "預估資本額？",
                "options": ["未滿 25 萬", "25 萬 ～ 50 萬", "50 萬以上"],
                "tips": [
                    {"q": "資本額要多少才合理？", "a": "資本額的設定應考慮業務規模、資金需求及風險承受能力。一般而言，資本額越高，公司的信用度越高，但也要考慮實際的資金投入。"},
                    {"q": "有最低資本額限制嗎？", "a": "沒有!多少錢都可以開公司，但實際投入資金，還是回歸到實際需求。"},
                    {"q": "資本額到位後可以動用嗎？", "a": "資本額到位後，可以作為公司運作的資金來源，但不能無故退還股款給股東，否則違反公司法規定。"},
                ],
            },
            {
                "id": "address", "title": "預計的設立地址？",
                "options": ["商務中心", "自有房屋", "承租實體辦公室"],
                "tips": [
                    {"q": "可以用我自己家的住址當作營業登記地址嗎？", "a": "可以的，這是最省建置成本的方式。但提醒您，該地址建築的房屋稅與地價稅可能會被主管機關主動依比例調漲為較高的「營業用費率」。"},
                    {"q": "房子是我自己的，還需要付租金給自己嗎？", "a": "雖然沒有實際支付給自己，但是由於公司組織具備獨立的法人格，因此國稅局還是會依照「當地租金行情」設算您的租金，並且併入個人所得，換句話說，雖然沒拿到錢，但是您仍要繳稅。"},
                    {"q": "租賃實體辦公室有什麼好處？", "a": "可以避免被國稅局認定為「虛設行號」，並且可以節稅，因為租金可以列為公司的費用，降低公司的所得，進而減少稅負。"},
                    {"q": "甚麼是租賃稅？", "a": "如果房東是自然人，那麼每次給付租金時，公司需要代扣 10% 的所得稅以及2.11%的補充保費，並且申報扣繳憑單；房東可能會藉此要求調漲租金。"},
                    {"q": "租屋處的地方可以當登記地址嗎？", "a": "可以的，只要取得房東的同意書以及房屋稅稅單即可，或是取得租約，並且承租人是公司而非個人，這樣也能替代房屋使用同意書。"},
                    {"q": "二房東可以轉租給我當登記地址嗎？", "a": "由於二房東不是合法的房屋所有權人，因此還是要取得房東的同意。"},
                ],
            },
            {
                "id": "insurance", "title": "負責人的全民健保是否已投保在其他公司？",
                "hint": "投保在職業工會或地方公所者，請選「否」。",
                "options": ["是", "否"],
                "tips": [
                    {"q": "聽說自己當老闆負責人，健保費會變很貴？", "a": "是的。除非您在其他公司有正職工作，否則法規強制負責人必須在自己公司成立健保投保單位，且目前的「負責人最低投保薪資規定」為（115年）36,300 元起跳，因此整體負擔通常會明顯增加。"},
                    {"q": "我在另外一家公司有上班正職，能保在那邊就好嗎？", "a": "如果您在其他公司有正職工作，且該公司已為您投保健保，則您可以在該公司繼續投保，無需在自己公司重新投保。"},
                    {"q": "負責人最低投保薪資規定？", "a": "目前的「負責人最低投保薪資規定」為（115年）36,300 元起跳。"},
                    {"q": "負責人的勞保及勞工退休金？", "a": "如果負責人實際工作並且自願加入勞保，可以投保在自己公司，否則是可以不用加保的。"},
                ],
            },
        ]
        return ctx


class WithholdingTaxView(_ToolView):
    template_name = "public_site/tools/withholding_tax.html"
    current_tool = "withholding"


class ProcessFlowView(TemplateView):
    template_name = "public_site/tools/process_flow.html"
