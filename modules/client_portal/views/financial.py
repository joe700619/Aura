import json
import datetime

from django.views.generic import TemplateView

from modules.client_portal.mixins import ClientRequiredMixin
from modules.bookkeeping.models.business_tax import TaxFilingYear, TaxFilingPeriod
from modules.bookkeeping.models.progress import BookkeepingYear
from modules.bookkeeping.models.corporate_tax import CorporateTaxFiling


class FinancialAnalysisView(ClientRequiredMixin, TemplateView):
    template_name = 'client_portal/financial_analysis.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        client = self.request.user.bookkeeping_client_profile
        context['client'] = client

        # ── 年度選擇 ──
        available_years = list(
            TaxFilingYear.objects.filter(client=client)
            .values_list('year', flat=True)
            .distinct().order_by('-year')
        )
        default_year = datetime.datetime.now().year - 1911
        try:
            selected_year = int(self.request.GET.get('year', default_year))
        except (ValueError, TypeError):
            selected_year = default_year
        if available_years and selected_year not in available_years:
            selected_year = available_years[0]
        if not available_years:
            available_years = [default_year]
        context['available_years'] = available_years
        context['selected_year'] = selected_year

        # ── VAT 期別資料 ──
        vat_periods = []
        try:
            vat_year = TaxFilingYear.objects.get(client=client, year=selected_year)
            vat_periods = list(TaxFilingPeriod.objects.filter(year_record=vat_year).order_by('period_start_month'))
        except TaxFilingYear.DoesNotExist:
            pass

        available_periods = [p.period_start_month for p in vat_periods]
        try:
            selected_period = int(self.request.GET.get('period', available_periods[-1] if available_periods else 1))
        except (ValueError, TypeError):
            selected_period = available_periods[-1] if available_periods else 1
        if available_periods and selected_period not in available_periods:
            selected_period = available_periods[-1]
        context['available_periods'] = available_periods
        context['selected_period'] = selected_period

        # ── 累計 VAT KPI（截至選定期別）──
        ytd_periods = [p for p in vat_periods if p.period_start_month <= selected_period]
        context['total_sales'] = sum(p.sales_amount for p in ytd_periods)
        context['total_input'] = sum(p.input_amount for p in ytd_periods)
        context['total_payable'] = sum(p.payable_tax for p in ytd_periods)

        # ── 推估截至月份（由使用者選取的 VAT 期別推算）──
        try:
            freq = client.tax_setting.filing_frequency
        except Exception:
            freq = 'bimonthly'
        through_month = min(selected_period + 1 if freq == 'bimonthly' else selected_period, 12)
        is_full_year = (through_month >= 12)
        context['through_month'] = through_month
        context['is_full_year'] = is_full_year

        # ── 趨勢圖資料（全年）──
        context['chart_labels'] = json.dumps(
            [f"{p.period_start_month:02d}-{p.period_start_month+1:02d}月" for p in vat_periods]
        )
        context['chart_sales'] = json.dumps([float(p.sales_amount) for p in vat_periods])
        context['chart_input'] = json.dumps([float(p.input_amount) for p in vat_periods])

        # ── 營所稅試算資料（損益表）──
        corporate_tax = None
        try:
            bk_year = BookkeepingYear.objects.get(client=client, year=selected_year)
            corporate_tax = bk_year.corporate_tax_filing
        except (BookkeepingYear.DoesNotExist, CorporateTaxFiling.DoesNotExist):
            pass
        context['corporate_tax'] = corporate_tax

        if corporate_tax:
            adjustments = list(corporate_tax.adjustments.all().order_by('account_code'))
            revenue_items = [a for a in adjustments if a.account_code.startswith('4')]
            cost_items    = [a for a in adjustments if a.account_code.startswith('5')]
            expense_items = [a for a in adjustments if a.account_code.startswith('6')]
            non_op_rev    = [a for a in adjustments if a.account_code.startswith('7')]
            non_op_exp    = [a for a in adjustments if a.account_code.startswith('8')]

            def book(items): return sum(a.book_amount for a in items)
            def audit(items): return sum(a.declared_amount for a in items)

            a_rev  = audit(revenue_items)
            a_cost = audit(cost_items)
            a_exp  = audit(expense_items)
            a_nor  = audit(non_op_rev)
            a_noe  = audit(non_op_exp)

            a_gross  = a_rev - a_cost
            a_op     = a_gross - a_exp
            a_net    = a_op + a_nor - a_noe
            tax_rate = float(corporate_tax.tax_rate)
            a_tax    = max(0, round(float(a_net) * tax_rate / 100))

            profit_rate     = float(corporate_tax.industry_profit_rate)
            income_std_rate = float(corporate_tax.income_standard_rate)
            a_rev_f = float(a_rev)

            if corporate_tax.industry_profit_rate is None:
                mode = 'na'
            elif a_rev_f >= 30_000_000:
                mode = 'income_standard'
            elif profit_rate < 0 and a_rev_f >= 10_000_000:
                mode = 'income_standard'
            else:
                mode = 'book_review'

            if mode == 'book_review':
                review_income = round(a_rev_f * profit_rate / 100) + float(a_nor)
            elif mode == 'income_standard':
                review_income = round(a_rev_f * income_std_rate / 100) + float(a_nor) - float(a_noe)
            else:
                review_income = None

            review_tax   = max(0, round(float(review_income) * tax_rate / 100)) if review_income is not None else None
            tax_savings  = (a_tax - review_tax) if (review_tax is not None and a_tax is not None) else None

            ytd_scale            = 12 / through_month if not is_full_year else 1
            estimated_audit_tax  = round(float(a_tax) * ytd_scale)
            estimated_review_tax = round(float(review_tax) * ytd_scale) if review_tax is not None else None
            estimated_tax_savings = (estimated_audit_tax - estimated_review_tax) if estimated_review_tax is not None else None

            # ── 稅務風險 checklist ──
            checklist = []

            # 1. 帳列純益率 vs 書審標準
            if a_rev_f > 0:
                actual_pr = float(a_net) / a_rev_f * 100
                std_pr = float(corporate_tax.industry_profit_rate)
                if actual_pr >= std_pr:
                    pr_status, pr_detail = 'ok', f'帳列 {actual_pr:.1f}% 達到書審標準，申報風險低'
                elif actual_pr >= std_pr * 0.5:
                    pr_status, pr_detail = 'warning', f'帳列 {actual_pr:.1f}% 低於書審標準 {std_pr:.1f}%，差距尚在合理範圍'
                else:
                    pr_status, pr_detail = 'danger', f'帳列 {actual_pr:.1f}% 明顯低於書審標準 {std_pr:.1f}%，費用偏高需留意'
                checklist.append({
                    'label': '帳列純益率', 'your_value': f'{actual_pr:.1f}%',
                    'standard': f'≥ {std_pr:.1f}%', 'status': pr_status, 'detail': pr_detail,
                })

            # 2. 年營收規模
            if a_rev_f > 0:
                rev_wan = a_rev_f / 10_000
                if a_rev_f < 10_000_000:
                    rev_status = 'ok'
                    rev_detail = '收入未達千萬，國稅局抽查機率較低'
                elif a_rev_f < 30_000_000:
                    rev_status = 'warning'
                    rev_detail = '收入介於千萬至三千萬，建議帳務完整留存'
                else:
                    rev_status = 'danger'
                    rev_detail = '收入逾三千萬，必須以查帳方式申報，帳冊須完備'
                checklist.append({
                    'label': '年營收規模', 'your_value': f'{rev_wan:,.0f} 萬',
                    'standard': '< 1,000 萬最低風險', 'status': rev_status, 'detail': rev_detail,
                })

            # 3. 費用占收入比率
            if a_rev_f > 0 and float(a_exp) > 0:
                exp_ratio = float(a_exp) / a_rev_f * 100
                if exp_ratio < 35:
                    exp_status = 'ok'
                    exp_detail = f'費用占比 {exp_ratio:.1f}%，在正常範圍內'
                elif exp_ratio < 50:
                    exp_status = 'warning'
                    exp_detail = f'費用占比 {exp_ratio:.1f}%，略偏高，建議確認憑證齊全'
                else:
                    exp_status = 'danger'
                    exp_detail = f'費用占比 {exp_ratio:.1f}%，偏高，容易引發稅務查核'
                checklist.append({
                    'label': '費用占收入比率', 'your_value': f'{exp_ratio:.1f}%',
                    'standard': '< 35%', 'status': exp_status, 'detail': exp_detail,
                })

            # 4. 業外收入占比
            if a_rev_f > 0:
                nor_ratio = float(a_nor) / a_rev_f * 100
                if nor_ratio < 5:
                    nor_status = 'ok'
                    nor_detail = f'業外收入占比 {nor_ratio:.1f}%，屬正常範圍'
                elif nor_ratio < 15:
                    nor_status = 'warning'
                    nor_detail = f'業外收入占比 {nor_ratio:.1f}%，建議確認科目歸屬正確'
                else:
                    nor_status = 'danger'
                    nor_detail = f'業外收入占比 {nor_ratio:.1f}%，比例偏高，建議與本所確認'
                checklist.append({
                    'label': '業外收入占比', 'your_value': f'{nor_ratio:.1f}%',
                    'standard': '< 5%', 'status': nor_status, 'detail': nor_detail,
                })

            # 5. VAT 銷進比（使用累計 VAT 資料）
            total_sales_f = float(context.get('total_sales', 0))
            total_input_f = float(context.get('total_input', 0))
            if total_input_f > 0:
                vat_ratio = total_sales_f / total_input_f
                if vat_ratio >= 1.2:
                    vat_status = 'ok'
                    vat_detail = f'銷項為進項的 {vat_ratio:.2f} 倍，稅務結構健全'
                elif vat_ratio >= 1.0:
                    vat_status = 'warning'
                    vat_detail = f'銷項為進項的 {vat_ratio:.2f} 倍，獲利空間偏薄'
                else:
                    vat_status = 'danger'
                    vat_detail = f'進項金額高於銷售額（比值 {vat_ratio:.2f}），請確認進項憑證正確性'
                checklist.append({
                    'label': '銷項 / 進項比值', 'your_value': f'{vat_ratio:.2f}',
                    'standard': '≥ 1.2', 'status': vat_status, 'detail': vat_detail,
                })

            # ── 風險分數與等級 ──
            score = sum(1 if i['status'] == 'warning' else (2 if i['status'] == 'danger' else 0) for i in checklist)
            if score <= 1:
                audit_risk_level = 'low'
            elif score <= 3:
                audit_risk_level = 'medium'
            else:
                audit_risk_level = 'high'

            # ── 因應策略 ──
            strategies = []
            def _flagged(label): return any(i['label'] == label and i['status'] != 'ok' for i in checklist)
            def _danger(label): return any(i['label'] == label and i['status'] == 'danger' for i in checklist)

            if _flagged('帳列純益率'):
                strategies.append('建議與本所一同檢視費用科目，確認可合法申報之項目，使純益率更接近書審標準，降低被調整的機率。')
            if _danger('年營收規模'):
                strategies.append('年收入已超過三千萬，須採查帳申報，請提前整理完整帳冊，並確保每筆費用均有合規憑證。')
            elif _flagged('年營收規模'):
                strategies.append('收入接近三千萬門檻，建議提早與本所確認本年度申報方式，避免臨時調整。')
            if _flagged('費用占收入比率'):
                strategies.append('費用比率偏高，建議盤點各項費用憑證的合規性，並與本所討論哪些項目可以正常申報。')
            if _flagged('業外收入占比'):
                strategies.append('業外收入比重較高，建議確認相關收入的科目歸屬與計算方式是否正確。')
            if _flagged('銷項 / 進項比值'):
                strategies.append('進項金額偏高，建議仔細核對進項憑證的真實性與完整性，避免進項異常引發查核。')
            if not strategies:
                strategies.append('目前各項財務指標均在正常範圍內，請繼續保持良好的帳務管理習慣，本所將於申報季前主動與您確認最終申報方式。')

            context.update({
                'revenue_items': revenue_items,
                'cost_items': cost_items,
                'expense_items': expense_items,
                'non_op_rev_items': non_op_rev,
                'non_op_exp_items': non_op_exp,
                'book_revenue': book(revenue_items),
                'book_cost': book(cost_items),
                'book_expense': book(expense_items),
                'book_non_op_rev': book(non_op_rev),
                'book_non_op_exp': book(non_op_exp),
                'audit_revenue': a_rev,    'audit_cost': a_cost,
                'audit_expense': a_exp,    'audit_non_op_rev': a_nor,
                'audit_non_op_exp': a_noe,
                'audit_gross_profit': a_gross, 'audit_op_income': a_op,
                'audit_net_income': a_net, 'audit_tax': a_tax,
                'review_mode': mode,
                'review_income': review_income,
                'review_tax': review_tax,
                'tax_savings': tax_savings,
                'estimated_audit_tax': estimated_audit_tax,
                'estimated_review_tax': estimated_review_tax,
                'estimated_tax_savings': estimated_tax_savings,
                'audit_risk_level': audit_risk_level,
                'risk_checklist': checklist,
                'risk_score': score,
                'risk_strategies': strategies,
                'risk_max_score': len(checklist) * 2,
                'risk_dash_offset': round(314.16 * (1 - min(score, len(checklist) * 2) / (len(checklist) * 2)), 2) if checklist else 314.16,
                'risk_color': {'low': '#10b981', 'medium': '#f59e0b', 'high': '#ef4444'}.get(audit_risk_level, '#94a3b8'),
            })

            pie_items = [a for a in expense_items if a.declared_amount > 0]
            context['pie_labels'] = json.dumps([a.account_name for a in pie_items], ensure_ascii=False)
            context['pie_data']   = json.dumps([float(a.declared_amount) for a in pie_items])
        else:
            for key in ('revenue_items', 'cost_items', 'expense_items', 'non_op_rev_items', 'non_op_exp_items'):
                context[key] = []
            context['pie_labels'] = '[]'
            context['pie_data']   = '[]'
            context['review_mode'] = None
            context['audit_risk_level'] = None
            context['risk_checklist'] = []
            context['risk_score'] = 0
            context['risk_strategies'] = []

        context['faq_items'] = [
            ('什麼是書審申報？', '擴大書審申報是指依財政部公告之同業利潤標準（純益率），以「營業收入 × 純益率 + 業外收入」計算所得額，適用對象為收入未達 3 千萬元且純益率為正數之營利事業。'),
            ('什麼是查帳申報？', '查帳申報是依據實際帳冊記載之收入、成本、費用計算所得額，並扣除稅法不允許之費用（帳外剔除），適用於超過書審門檻或選擇以實際帳列數申報之營利事業。'),
            ('建議申報方式以哪個為準？', '本所會依據您的實際收入金額、行業別純益率，以及查帳、書審試算結果，比較兩者應納稅額後，建議對您最有利的申報方式，並於申報期前主動通知。'),
            ('損益表資料何時更新？', '損益表資料由本所記帳師於完成帳務整理後匯入，通常於每年 3-4 月申報季前更新完畢。如需最新資料請聯絡本所。'),
            ('累積銷售額和進項金額是什麼？', '累積銷售額為您在選定期間內的含稅銷售總額（銷項金額）；累計進項金額為同期間可供扣抵之進貨及費用憑證金額。兩者均來自每期營業稅（401/403）申報資料。'),
        ]

        return context
