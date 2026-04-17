"""
所得稅申報書媒體檔 (001) 解析器

此模組負責解析國稅局所得稅申報書 001 格式媒體檔。
001 檔案本質為 txt 純文字檔，編碼通常為 BIG5。

TODO: 待取得 001 範例檔後，填入具體的解析邏輯。
"""
import logging

logger = logging.getLogger(__name__)


class MediaFileParseError(Exception):
    """001 媒體檔解析失敗"""
    pass


def parse_001_file(file_obj) -> dict:
    """
    解析國稅局所得稅申報書 001 媒體檔。

    Args:
        file_obj: Django UploadedFile 或任何具有 .read() 方法的 file-like object

    Returns:
        dict: 解析後的結構化資料，key 為欄位名稱，value 為欄位值。
              至少包含以下 key：
              - industry_code: 行業代號
              - industry_name: 行業名稱
              - gross_revenue: 營業收入淨額
              - cost_of_goods: 營業成本
              - gross_profit: 營業毛利
              - operating_expenses: 營業費用
              - net_operating_income: 營業淨利
              - non_operating_income: 營業外收入
              - non_operating_expense: 營業外支出
              - pre_tax_income: 稅前淨利
              - taxable_income: 課稅所得額
              - annual_tax: 應納稅額
              - provisional_paid: 暫繳稅額
              - withholding_paid: 扣繳稅額
              - self_pay: 應自行繳納稅額
              - undistributed_earnings: 未分配盈餘
              - undistributed_surtax: 未分配盈餘加徵

    Raises:
        MediaFileParseError: 檔案格式不正確或解析失敗
    """
    content = file_obj.read()

    # ── Step 1: 解碼（嘗試 BIG5 → UTF-8） ──
    text = _decode_content(content)

    # ── Step 2: 依據 001 格式規格進行解析 ──
    # TODO: 待取得範例檔後填入具體解析邏輯
    result = _parse_content(text)

    return result


def _decode_content(content: bytes) -> str:
    """
    嘗試解碼 001 檔案內容。
    優先使用 BIG5，失敗後嘗試 UTF-8。
    """
    encodings = ['big5', 'utf-8', 'cp950']
    for encoding in encodings:
        try:
            return content.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    raise MediaFileParseError('無法解碼 001 檔案，請確認檔案編碼格式。')


def _parse_content(text: str) -> dict:
    """
    解析 001 檔案文字內容。

    TODO: 這是骨架函式，待取得 001 範例檔後填入具體解析邏輯。
    目前回傳空值字典以供上層正常運作。

    001 媒體檔常見的格式類型：
    1. 固定長度格式：每個欄位佔固定字元寬度
    2. 分隔符格式：以逗號或其他符號分隔
    3. Key-Value 格式：每行為 key=value

    請依實際範例檔格式選擇對應的解析策略。
    """
    logger.info('001 媒體檔解析：使用骨架 parser（尚未設定具體解析邏輯）')

    # 預設回傳值（所有欄位為空/零）
    result = {
        'industry_code': '',
        'industry_name': '',
        'gross_revenue': 0,
        'cost_of_goods': 0,
        'gross_profit': 0,
        'operating_expenses': 0,
        'net_operating_income': 0,
        'non_operating_income': 0,
        'non_operating_expense': 0,
        'pre_tax_income': 0,
        'taxable_income': 0,
        'annual_tax': 0,
        'provisional_paid': 0,
        'withholding_paid': 0,
        'self_pay': 0,
        'undistributed_earnings': 0,
        'undistributed_surtax': 0,
    }

    # TODO: 在此加入實際解析邏輯
    # 範例（固定長度格式）：
    # lines = text.strip().split('\n')
    # for line in lines:
    #     if line.startswith('IND'):
    #         result['industry_code'] = line[3:10].strip()
    #         result['industry_name'] = line[10:30].strip()
    #     elif line.startswith('REV'):
    #         result['gross_revenue'] = int(line[3:18].strip() or 0)
    #     ...

    return result


def apply_parsed_data(media_data_obj, parsed_dict: dict):
    """
    將解析結果寫入 IncomeTaxMediaData 物件。

    Args:
        media_data_obj: IncomeTaxMediaData instance
        parsed_dict: parse_001_file() 的回傳值
    """
    from django.utils import timezone

    # 結構化欄位對應
    field_mapping = {
        'industry_code': 'industry_code',
        'industry_name': 'industry_name',
        'gross_revenue': 'gross_revenue',
        'cost_of_goods': 'cost_of_goods',
        'gross_profit': 'gross_profit',
        'operating_expenses': 'operating_expenses',
        'net_operating_income': 'net_operating_income',
        'non_operating_income': 'non_operating_income',
        'non_operating_expense': 'non_operating_expense',
        'pre_tax_income': 'pre_tax_income',
        'taxable_income': 'taxable_income',
        'annual_tax': 'annual_tax',
        'provisional_paid': 'provisional_paid',
        'withholding_paid': 'withholding_paid',
        'self_pay': 'self_pay',
        'undistributed_earnings': 'undistributed_earnings',
        'undistributed_surtax': 'undistributed_surtax',
    }

    for src_key, model_field in field_mapping.items():
        if src_key in parsed_dict:
            setattr(media_data_obj, model_field, parsed_dict[src_key])

    # 完整原始資料存入 JSON
    media_data_obj.raw_parsed_data = parsed_dict
    media_data_obj.parsed_at = timezone.now()
    media_data_obj.save()

    logger.info(f'已將解析結果寫入 {media_data_obj}')
