
二、雲端環境排程（Linux Crontab）
部署到雲端（Linux）後，用系統 crontab 即可，不需要額外套件。

設定步驟：


# 編輯 crontab
crontab -e
加入以下一行（每天早上 9:00 執行）：


0 9 * * * /path/to/venv/bin/python /path/to/project/manage.py send_overdue_notices >> /path/to/logs/overdue_notices.log 2>&1
實際路徑範例（假設部署在 /var/www/aura）：


0 9 * * * /var/www/aura/.venv/bin/python /var/www/aura/manage.py send_overdue_notices >> /var/www/aura/logs/overdue_notices.log 2>&1
注意事項：

>> logs/overdue_notices.log 會將每次執行輸出附加到 log 檔，方便查錯
crontab 執行時沒有環境變數，建議在 command 裡明確指定 DJANGO_SETTINGS_MODULE：

0 9 * * * cd /var/www/aura && DJANGO_SETTINGS_MODULE=config.settings .venv/bin/python manage.py send_overdue_notices >> logs/overdue_notices.log 2>&1
確認 logs/ 目錄存在且有寫入權限：mkdir -p /var/www/aura/logs