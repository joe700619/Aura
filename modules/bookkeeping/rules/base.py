class BaseRule:
    """
    專家系統規則的基礎類別
    所有的檢查規則都必須繼承此類別，並實作 evaluate 方法。
    """
    code = ""               # 規則唯一代碼 (必須為不重複字串，如: 'TAX_RETAINED_INC')
    name = ""               # 規則名稱 (供人類閱讀與介面顯示)
    description = ""        # 規則詳細說明
    default_threshold = 0.0 # 預設閾值 (例如 0.3 代表 30%，或 10000 絕對金額)

    @classmethod
    def evaluate(cls, client, period, current_threshold):
        """
        執行規則檢查的邏輯。
        必須由子類別實作。
        
        :param client: BookkeepingClient 實例
        :param period: 帳務期別 (BookkeepingPeriod 或相關資料)
        :param current_threshold: 此客戶當前生效的閾值 (已合併客製化設定與預設值)
        :return: (is_triggered: bool, actual_value: float)
                 - is_triggered: 是否觸發異常警報
                 - actual_value: 實際算出的數值 (用來顯示給客戶參考)
        """
        raise NotImplementedError("子類別必須實作 evaluate 方法")
