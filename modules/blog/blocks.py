"""StreamField blocks，對應 blog-article.css 的雜誌型內容區塊。"""
from wagtail import blocks
from wagtail.contrib.table_block.blocks import TableBlock as WagtailTableBlock
from wagtail.images.blocks import ImageChooserBlock


class HeadingBlock(blocks.StructBlock):
    number = blocks.CharBlock(required=False, max_length=8, label="編號（如 01）")
    text = blocks.CharBlock(required=True, max_length=200, label="標題文字")

    class Meta:
        icon = "title"
        label = "段落標題（H2）"
        template = "blog/blocks/heading.html"


class SubHeadingBlock(blocks.CharBlock):
    class Meta:
        icon = "title"
        label = "次標題（H3）"
        template = "blog/blocks/subheading.html"


class ParagraphBlock(blocks.RichTextBlock):
    class Meta:
        icon = "pilcrow"
        label = "段落"
        template = "blog/blocks/paragraph.html"
        features = ["bold", "italic", "ol", "ul", "link", "document-link"]


class NewsClipBlock(blocks.StructBlock):
    source = blocks.CharBlock(required=True, max_length=80, label="新聞來源")
    date = blocks.CharBlock(required=False, max_length=40, label="日期")
    title = blocks.CharBlock(required=True, max_length=200, label="新聞標題")
    quote = blocks.TextBlock(required=True, label="引言內容")
    link = blocks.URLBlock(required=False, label="原文連結")

    class Meta:
        icon = "doc-full"
        label = "新聞剪報"
        template = "blog/blocks/news_clip.html"


class EditorTakeBlock(blocks.StructBlock):
    body = blocks.TextBlock(required=True, label="勤信觀點內容")
    sign = blocks.CharBlock(required=False, max_length=80, label="署名")

    class Meta:
        icon = "edit"
        label = "勤信觀點"
        template = "blog/blocks/editor_take.html"


class StatCalloutBlock(blocks.StructBlock):
    number = blocks.CharBlock(required=True, max_length=20, label="主要數字")
    unit = blocks.CharBlock(required=False, max_length=20, label="單位（%、萬等）")
    text = blocks.TextBlock(required=True, label="說明文字")
    source = blocks.CharBlock(required=False, max_length=120, label="資料來源")

    class Meta:
        icon = "plus"
        label = "統計數字"
        template = "blog/blocks/stat_callout.html"


class CpaNoteBlock(blocks.StructBlock):
    label = blocks.CharBlock(required=False, max_length=40, default="會計師補充", label="標籤")
    body = blocks.RichTextBlock(
        required=True,
        label="補充內容",
        features=["bold", "italic", "ol", "ul", "link"],
    )

    class Meta:
        icon = "help"
        label = "會計師補充"
        template = "blog/blocks/cpa_note.html"


class TimelineItemBlock(blocks.StructBlock):
    date = blocks.CharBlock(required=True, max_length=40)
    title = blocks.CharBlock(required=True, max_length=200)
    desc = blocks.TextBlock(required=False)


class TimelineBlock(blocks.StructBlock):
    items = blocks.ListBlock(TimelineItemBlock(), label="時間軸項目")

    class Meta:
        icon = "list-ul"
        label = "時間軸"
        template = "blog/blocks/timeline.html"


class FigureBlock(blocks.StructBlock):
    image = ImageChooserBlock(required=True)
    caption = blocks.CharBlock(required=False, max_length=200, label="圖說")

    class Meta:
        icon = "image"
        label = "圖片"
        template = "blog/blocks/figure.html"


TABLE_OPTIONS = {
    "minSpareRows": 0,
    "startRows": 3,
    "startCols": 3,
    "colHeaders": False,
    "rowHeaders": False,
    "contextMenu": ["row_above", "row_below", "---------", "col_left", "col_right", "---------", "remove_row", "remove_col", "---------", "undo", "redo"],
    "editor": "text",
    "stretchH": "all",
    "height": 240,
    "language": "zh-TW",
    "renderer": "html",
    "autoColumnSize": False,
}


class ArticleTableBlock(WagtailTableBlock):
    class Meta:
        icon = "table"
        label = "對比表格"


class ArticleBody(blocks.StreamBlock):
    heading = HeadingBlock()
    subheading = SubHeadingBlock()
    paragraph = ParagraphBlock()
    news_clip = NewsClipBlock()
    editor_take = EditorTakeBlock()
    stat_callout = StatCalloutBlock()
    cpa_note = CpaNoteBlock()
    timeline = TimelineBlock()
    figure = FigureBlock()
    table = ArticleTableBlock(table_options=TABLE_OPTIONS)

    class Meta:
        block_counts = {}
