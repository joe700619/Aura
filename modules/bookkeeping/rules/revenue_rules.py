from .base import BaseRule
from ..models import BookkeepingPeriod, BookkeepingYear

class EstimatedRevenueGrowthRule(BaseRule):
    code = "REV_ESTIMATED_GROWTH_20"
    name = "今年推估收入較去年成長超過設定值"
    description = "以本期收入推估今年全年收入（如前2個月x6），若較去年度全年銷售額成長超過設定比例(預設20%)則通知"
    default_threshold = 0.20  # 預設成長 20%
    
    @classmethod
    def evaluate(cls, client, period, current_threshold):
        """
        :param client: BookkeepingClient
        :param period: 觸發檢查的 BookkeepingPeriod 實例
        """
        year = period.year_record.year
        period_month = period.period_start_month  # 1, 3, 5, 7, 9, 11
        
        # 1. 取得去年度的全年總銷售額
        last_year_periods = BookkeepingPeriod.objects.filter(
            year_record__client=client,
            year_record__year=year - 1
        )
        
        if not last_year_periods.exists():
            return False, 0.0 # 沒有去年的資料可以比對
            
        last_year_total_sales = sum([p.sales_amount for p in last_year_periods if p.sales_amount])
        
        if last_year_total_sales == 0:
            return False, 0.0 # 去年沒過帳不列入異常比較
        
        # 2. 計算今年度「累計至本期為止」的總銷售額
        current_year_periods_so_far = BookkeepingPeriod.objects.filter(
            year_record__client=client,
            year_record__year=year,
            period_start_month__lte=period_month
        )
        current_year_sales_so_far = sum([p.sales_amount for p in current_year_periods_so_far if p.sales_amount])
        
        # 3. 推估全年收入
        # 為了知道「目前已過了幾個月」，假設單月申報起月是 period_month
        # 也就是累積到了 period_month + 1 個月。(因為1期=1,2月，3期=3,4月。所以如果是1代表過了2個月，3代表4個月)
        months_passed = period_month + 1
        
        # 推估公式：目前的累積 / 目前過的月數 * 12
        estimated_annual_sales = (float(current_year_sales_so_far) / months_passed) * 12
        
        # 4. 計算成長率 
        growth_rate = (estimated_annual_sales - float(last_year_total_sales)) / float(last_year_total_sales)
        
        # 判斷是否超過閾值
        if growth_rate > current_threshold:
            # 轉換成百分比數字做為 actual_value (例如 0.25 會變成 25.0回報)
            return True, round(growth_rate * 100, 2)
            
        return False, round(growth_rate * 100, 2)
