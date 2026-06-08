# 選單管理 SOP

> 用途：所有 sidebar / menu 變動都應該透過 migration 進行，避免 DB 重建後選單遺失。
> 涉及表格：`system_config_menuitem`

---

## 原則

1. **永遠不要在 admin 直接新增/刪除選單後就放著** —— 會在重建環境時消失
2. **任何要保留的選單變動 = 一支新 migration**
3. **migration 要 idempotent**：用 `update_or_create` 而非 `create`

---

## 推薦工作流（最省力）

如果你習慣在 admin 拖拉式調整選單：

1. 在 admin 自由調整（拖順序、改名、加 icon）
2. 一行命令把當前狀態寫成 migration：
   ```powershell
   docker-compose exec web python manage.py snapshot_menus --name reorder_menus --description "重整側選單順序"
   ```
3. 檢視生成的檔案 `modules/system_config/migrations/00XX_reorder_menus_YYYYMMDD.py`
4. `git add` + `commit`

snapshot_menus 命令特性：
- 自動編號接續最新 migration
- 用 `(title, parent_title)` 複合鍵 update_or_create（idempotent）
- 不刪除任何 MenuItem（避免誤刪）
- rollback 是 no-op（保留現狀，不還原）

⚠️ 想刪除某個選單時不能用 snapshot —— 走「場景 B：移除選單」手刻 migration。

---

## 場景 A：新增選單

### 步驟

1. 在 `modules/system_config/migrations/` 新增檔案，編號接續最新的：
   - 看現有最後一支：`ls modules/system_config/migrations/`
   - 新檔名範例：`00XX_add_<feature>_menu.py`

2. 用以下範本：

```python
"""
新增 <功能名稱> 選單項目
"""
from django.db import migrations


def add_menu(apps, schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    parent = MenuItem.objects.filter(title='記帳', parent__isnull=True).first()
    if not parent:
        return  # 防呆：父層不存在就跳過
    MenuItem.objects.update_or_create(
        title='新功能',
        parent=parent,
        defaults={
            'url_name': 'bookkeeping:new_feature_list',
            'icon_svg': '<svg ...>...</svg>',
            'order': 50,
            'is_active': True,
            'required_permission': '',
        },
    )


def remove_menu(apps, schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    parent = MenuItem.objects.filter(title='記帳', parent__isnull=True).first()
    if parent:
        MenuItem.objects.filter(title='新功能', parent=parent).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('system_config', '00YY_previous_migration'),  # 改成上一支
    ]
    operations = [
        migrations.RunPython(add_menu, remove_menu),
    ]
```

3. 執行：`docker-compose exec web python manage.py migrate system_config`
4. **清快取版本**（見下方「⚠️ migrate 後必清快取」）
5. Commit migration 檔案

---

## ⚠️ migrate 後必清快取（強制，否則卡 5 分鐘舊選單）

navbar 選單有 per-user 5 分鐘快取（`menu_tags.py`），靠 `MenuItem.save()` 的
post_save signal bump `sidebar_menu_version` 來失效。**但 migration 用的是
`apps.get_model` 的 historical model，不會觸發那個 signal** → migrate 完選單
DB 已更新，但所有人的 sidebar 仍吃舊快取，重整也看不到變化。

每次用 migration 改選單後，務必手動 bump 版本：

```powershell
docker-compose exec web python manage.py shell -c "from django.core.cache import cache; v=cache.get('sidebar_menu_version') or 1; cache.set('sidebar_menu_version', v+1, None); print('bumped ->', v+1)"
```

（在 admin 拖拉式調整則不用，因為走真正的 model.save() 會自動失效。）

---

## 場景 B：移除選單

```python
def remove_menu(apps, schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    MenuItem.objects.filter(title='舊功能', parent__title='記帳').delete()


def restore_menu(apps, schema_editor):
    """rollback 用，可選擇放空 pass"""
    pass


class Migration(migrations.Migration):
    dependencies = [('system_config', '00YY_previous')]
    operations = [migrations.RunPython(remove_menu, restore_menu)]
```

---

## 場景 C：改名 / 改 url / 改順序

```python
def rename(apps, schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    MenuItem.objects.filter(title='舊名稱', parent__title='記帳').update(
        title='新名稱',
        url_name='bookkeeping:new_url',
        order=20,
    )


def revert(apps, schema_editor):
    MenuItem = apps.get_model('system_config', 'MenuItem')
    MenuItem.objects.filter(title='新名稱', parent__title='記帳').update(
        title='舊名稱',
        url_name='bookkeeping:old_url',
        order=10,
    )


class Migration(migrations.Migration):
    dependencies = [('system_config', '00YY_previous')]
    operations = [migrations.RunPython(rename, revert)]
```

---

## 場景 D：緊急熱修（線上漏了一個選單）

1. 先在 admin 手動補上，讓使用者立刻能用
2. **必須**之後寫一支 migration 把這個變動納入版控
3. PR 描述標明「補既有變動」

---

## 注意事項

### url_name 的 namespace
- 必須帶 namespace：`'administrative:document_receipt_list'`
- 不要寫 `'document_receipt_list'`，會在 dashboard reverse 失敗
- 可用 `python manage.py shell` 驗證：
  ```python
  from django.urls import reverse
  reverse('administrative:document_receipt_list')  # 不報錯就 OK
  ```

### parent_title 同名問題
- 如果某 title 在 top-level 跟子層都出現，需明確指定 `parent__isnull=True` 或 `parent__title='xxx'`
- 範例：`基本資料` 既是 top-level 容器、也是子項

### 權限欄位
- `required_permission` 預設空字串
- 設定後只有有該 permission 的使用者看得到
- 格式：`app_label.permission_codename`（例：`administrative.view_documentreceipt`）

---

## 重要：唯一真相來源

`modules/system_config/migrations/0009_seed_full_menu_tree.py` 是初始選單樹的完整定義。
之後每次 menu 變動都疊加在此之上，**不要修改 0009**（migration 規則：已 apply 的不改）。
