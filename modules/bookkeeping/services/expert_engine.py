from ..rules import get_all_rules
from ..models import ClientRuleSetting, RuleAlert

class ExpertEngine:
    """專家系統的核心執行引擎"""
    
    @classmethod
    def run_checks(cls, client, period):
        """
        對指定的客戶與期別執行所有的專家系統檢查。
        
        :param client: BookkeepingClient 實例
        :param period: 相關帳務期別
        """
        rules = get_all_rules()
        created_alerts_count = 0
        
        for rule in rules:
            # 1. 取得該客戶對此規則的客製化設定
            setting = ClientRuleSetting.objects.filter(client=client, rule_code=rule.code).first()
            
            # 2. 如果客戶明確關閉此規則，則跳過不檢查
            if setting and not setting.is_active:
                continue
                
            # 3. 決定當前生效的閾值 (客製化優先，無則預設)
            threshold = rule.default_threshold
            if setting and setting.custom_threshold is not None:
                threshold = setting.custom_threshold
                
            # 4. 執行檢查邏輯
            try:
                is_triggered, actual_value = rule.evaluate(client, period, threshold)
                
                # 5. 如果觸發警報，寫入資料庫
                if is_triggered:
                    # 先看這期這個規則是否已經發布過警報，避免重複寫入
                    alert, created = RuleAlert.objects.get_or_create(
                         client=client,
                         period=period,
                         rule_code=rule.code,
                         defaults={
                             'actual_value': actual_value,
                             'alert_message': f"系統偵測異常: 【{rule.name}】，偵測時的數值為 {actual_value}"
                         }
                    )
                    
                    if created:
                        created_alerts_count += 1
                        # 如果非新建而是已經存在，視業務需求可能要更新 actual_value
                        
            except Exception as e:
                # 在執行單一規則時若發生錯誤，捕獲並記錄，以免整個引擎崩潰
                print(f"Error running rule {rule.code} for client {client.company.name}: {e}")
                
        return created_alerts_count

