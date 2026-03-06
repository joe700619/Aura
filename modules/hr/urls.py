"""
HR Module URL Configuration
"""
from django.urls import path
app_name = 'hr'
from .views.employee import (
    EmployeeListView, EmployeeCreateView, EmployeeUpdateView, EmployeeDeleteView,
    employee_submit_approval, employee_approve, employee_reject, employee_return, employee_cancel_approval,
)
from .views.api import EmployeeSearchApiView, InsuranceBracketListAPIView
from .views.work_calendar import (
    WorkCalendarListView, WorkCalendarCreateView, WorkCalendarUpdateView, WorkCalendarDeleteView,
)
from .views.attendance import (
    AttendanceListView, AttendanceCreateView, AttendanceUpdateView, AttendanceDeleteView, ClockInOutView,
)
from .views.leave import (
    LeaveTypeListView, LeaveTypeCreateView, LeaveTypeUpdateView, LeaveTypeDeleteView,
    LeaveBalanceListView, LeaveBalanceCreateView, LeaveBalanceUpdateView, LeaveBalanceDeleteView,
    RecalculateLeaveView,
    LeaveRequestListView, LeaveRequestCreateView, LeaveRequestUpdateView, LeaveRequestDeleteView,
    leave_request_submit_approval, leave_request_approve,
    leave_request_reject, leave_request_return, leave_request_cancel_approval,
)
from .views.payroll import (
    InsuranceBracketListView, InsuranceBracketCreateView, InsuranceBracketUpdateView, InsuranceBracketDeleteView,
    SalaryStructureListView, SalaryStructureCreateView, SalaryStructureUpdateView, SalaryStructureDeleteView,
    OvertimeListView, OvertimeCreateView, OvertimeUpdateView, OvertimeDeleteView,
    PayrollListView, PayrollCreateView, PayrollUpdateView, PayrollDeleteView, PayrollBatchGenerateView,
    AdvancePaymentListView, AdvancePaymentCreateView, AdvancePaymentUpdateView, AdvancePaymentDeleteView,
    advancepayment_submit_approval, advancepayment_approve,
    advancepayment_reject, advancepayment_return, advancepayment_cancel_approval,
    overtime_submit_approval, overtime_approve,
    overtime_reject, overtime_return, overtime_cancel_approval,
)
from .views.line_clock import LineWebhookView, LineClockSimulateView

urlpatterns = [
    # API
    path('api/employees/search/', EmployeeSearchApiView.as_view(), name='employee_search_api'),
    path('api/insurance-brackets/', InsuranceBracketListAPIView.as_view(), name='insurance_brackets_api'),

    # Employee CRUD
    path('employees/', EmployeeListView.as_view(), name='employee_list'),
    path('employees/new/', EmployeeCreateView.as_view(), name='employee_create'),
    path('employees/<int:pk>/', EmployeeUpdateView.as_view(), name='employee_update'),
    path('employees/<int:pk>/delete/', EmployeeDeleteView.as_view(), name='employee_delete'),
    path('employees/<int:pk>/submit-approval/', employee_submit_approval, name='employee_submit_approval'),
    path('employees/<int:pk>/approve/', employee_approve, name='employee_approve'),
    path('employees/<int:pk>/reject/', employee_reject, name='employee_reject'),
    path('employees/<int:pk>/return/', employee_return, name='employee_return'),
    path('employees/<int:pk>/cancel-approval/', employee_cancel_approval, name='employee_cancel_approval'),

    # Work Calendar
    path('work-calendar/', WorkCalendarListView.as_view(), name='work_calendar_list'),
    path('work-calendar/add/', WorkCalendarCreateView.as_view(), name='work_calendar_create'),
    path('work-calendar/<int:pk>/edit/', WorkCalendarUpdateView.as_view(), name='work_calendar_update'),
    path('work-calendar/<int:pk>/delete/', WorkCalendarDeleteView.as_view(), name='work_calendar_delete'),

    # Attendance
    path('attendance/', AttendanceListView.as_view(), name='attendance_list'),
    path('attendance/add/', AttendanceCreateView.as_view(), name='attendance_create'),
    path('attendance/<int:pk>/edit/', AttendanceUpdateView.as_view(), name='attendance_update'),
    path('attendance/<int:pk>/delete/', AttendanceDeleteView.as_view(), name='attendance_delete'),
    path('clock/', ClockInOutView.as_view(), name='clock_in_out'),

    # Leave Type
    path('leave-types/', LeaveTypeListView.as_view(), name='leave_type_list'),
    path('leave-types/add/', LeaveTypeCreateView.as_view(), name='leave_type_create'),
    path('leave-types/<int:pk>/edit/', LeaveTypeUpdateView.as_view(), name='leave_type_update'),
    path('leave-types/<int:pk>/delete/', LeaveTypeDeleteView.as_view(), name='leave_type_delete'),

    # Leave Balance
    path('leave-balances/', LeaveBalanceListView.as_view(), name='leave_balance_list'),
    path('leave-balances/add/', LeaveBalanceCreateView.as_view(), name='leave_balance_create'),
    path('leave-balances/<int:pk>/edit/', LeaveBalanceUpdateView.as_view(), name='leave_balance_update'),
    path('leave-balances/<int:pk>/delete/', LeaveBalanceDeleteView.as_view(), name='leave_balance_delete'),
    path('leave-balances/recalculate/', RecalculateLeaveView.as_view(), name='leave_balance_recalculate'),

    # Leave Request
    path('leave-requests/', LeaveRequestListView.as_view(), name='leave_request_list'),
    path('leave-requests/add/', LeaveRequestCreateView.as_view(), name='leave_request_create'),
    path('leave-requests/<int:pk>/edit/', LeaveRequestUpdateView.as_view(), name='leave_request_update'),
    path('leave-requests/<int:pk>/delete/', LeaveRequestDeleteView.as_view(), name='leave_request_delete'),
    path('leave-requests/<int:pk>/approval/submit/', leave_request_submit_approval, name='leaverequest_submit_approval'),
    path('leave-requests/<int:pk>/approval/approve/', leave_request_approve, name='leaverequest_approve'),
    path('leave-requests/<int:pk>/approval/reject/', leave_request_reject, name='leaverequest_reject'),
    path('leave-requests/<int:pk>/approval/return/', leave_request_return, name='leaverequest_return'),
    path('leave-requests/<int:pk>/approval/cancel/', leave_request_cancel_approval, name='leaverequest_cancel_approval'),

    # Insurance Brackets
    path('insurance-brackets/', InsuranceBracketListView.as_view(), name='insurance_bracket_list'),
    path('insurance-brackets/add/', InsuranceBracketCreateView.as_view(), name='insurance_bracket_create'),
    path('insurance-brackets/<int:pk>/edit/', InsuranceBracketUpdateView.as_view(), name='insurance_bracket_update'),
    path('insurance-brackets/<int:pk>/delete/', InsuranceBracketDeleteView.as_view(), name='insurance_bracket_delete'),

    # Salary Structure
    path('salary-structures/', SalaryStructureListView.as_view(), name='salary_structure_list'),
    path('salary-structures/add/', SalaryStructureCreateView.as_view(), name='salary_structure_create'),
    path('salary-structures/<int:pk>/edit/', SalaryStructureUpdateView.as_view(), name='salary_structure_update'),
    path('salary-structures/<int:pk>/delete/', SalaryStructureDeleteView.as_view(), name='salary_structure_delete'),

    # Overtime
    path('overtime/', OvertimeListView.as_view(), name='overtime_list'),
    path('overtime/add/', OvertimeCreateView.as_view(), name='overtime_create'),
    path('overtime/<int:pk>/edit/', OvertimeUpdateView.as_view(), name='overtime_update'),
    path('overtime/<int:pk>/delete/', OvertimeDeleteView.as_view(), name='overtime_delete'),
    path('overtime/<int:pk>/approval/submit/', overtime_submit_approval, name='overtimerecord_submit_approval'),
    path('overtime/<int:pk>/approval/approve/', overtime_approve, name='overtimerecord_approve'),
    path('overtime/<int:pk>/approval/reject/', overtime_reject, name='overtimerecord_reject'),
    path('overtime/<int:pk>/approval/return/', overtime_return, name='overtimerecord_return'),
    path('overtime/<int:pk>/approval/cancel/', overtime_cancel_approval, name='overtimerecord_cancel_approval'),

    # Payroll
    path('payroll/', PayrollListView.as_view(), name='payroll_list'),
    path('payroll/add/', PayrollCreateView.as_view(), name='payroll_create'),
    path('payroll/<int:pk>/edit/', PayrollUpdateView.as_view(), name='payroll_update'),
    path('payroll/<int:pk>/delete/', PayrollDeleteView.as_view(), name='payroll_delete'),
    path('payroll/batch-generate/', PayrollBatchGenerateView.as_view(), name='payroll_batch_generate'),

    # Advance Payment (代墊款)
    path('advance-payments/', AdvancePaymentListView.as_view(), name='advance_payment_list'),
    path('advance-payments/add/', AdvancePaymentCreateView.as_view(), name='advance_payment_create'),
    path('advance-payments/<int:pk>/edit/', AdvancePaymentUpdateView.as_view(), name='advance_payment_update'),
    path('advance-payments/<int:pk>/delete/', AdvancePaymentDeleteView.as_view(), name='advance_payment_delete'),
    path('advance-payments/<int:pk>/approval/submit/', advancepayment_submit_approval, name='advancepayment_submit_approval'),
    path('advance-payments/<int:pk>/approval/approve/', advancepayment_approve, name='advancepayment_approve'),
    path('advance-payments/<int:pk>/approval/reject/', advancepayment_reject, name='advancepayment_reject'),
    path('advance-payments/<int:pk>/approval/return/', advancepayment_return, name='advancepayment_return'),
    path('advance-payments/<int:pk>/approval/cancel/', advancepayment_cancel_approval, name='advancepayment_cancel_approval'),

    # Line 打卡
    path('line/webhook/', LineWebhookView.as_view(), name='line_webhook'),
    path('line/simulate/', LineClockSimulateView.as_view(), name='line_clock_simulate'),
]
