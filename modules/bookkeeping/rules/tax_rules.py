from .base import BaseRule
from ..models import TaxFilingPeriod

class RetainedTaxConsecutiveRule(BaseRule):
    code = "TAX_RETAINED_50K_3P"
    name = "留抵稅額連3期大於5萬"
    description = "檢查包含本期在內，是否連續三期的營業稅留抵稅額皆大於設定金額"
    default_threshold = 50000.0  # 預設 5 萬
    
    @classmethod
    def evaluate(cls, client, period, current_threshold):
        """
        :param client: BookkeepingClient
        :param period: 觸發檢查的 BookkeepingPeriod 實例
        """
        # 取出該年度
        year = period.year_record.year
        period_month = period.period_start_month
        
        # 我們需要找營業稅申報的紀錄 (TaxFilingPeriod)，因為留抵稅額記錄在那邊
        # 且必須往前找連續3期 (包含本期)
        
        # Aura 系統的設計是 BookkeepingPeriod 跟 TaxFilingPeriod 通常會對應 (透過 client, year, month)
        # 所以先撈出該客戶所有的營業稅期別，按時間倒序排列
        tax_periods = TaxFilingPeriod.objects.filter(
            year_record__client=client,
            year_record__year__lte=year
        ).order_by('-year_record__year', '-period_start_month')
        
        # 我們只要把時間點在「本期(含)之前」的期別留下來
        past_periods = []
        for tp in tax_periods:
            if tp.year_record.year < year or (tp.year_record.year == year and tp.period_start_month <= period_month):
                past_periods.append(tp)
                
            if len(past_periods) == 3:
                break
                
        # 如果客戶過往營業稅紀錄不足 3 期，則無法判斷連續 3 期，直接回傳 False
        if len(past_periods) < 3:
            return False, 0.0
            
        # 檢查這三期的 retained_tax 是否每一期都大於閾值
        for tp in past_periods:
            if tp.retained_tax is None or float(tp.retained_tax) <= current_threshold:
                return False, float(tp.retained_tax or 0)
                
        # 如果執行到這，代表連續三期都大於閾值
        # 我們回傳最新一期 (本期) 的留抵稅額當作實際數字供參考
        actual_val = float(past_periods[0].retained_tax)
        return True, actual_val
