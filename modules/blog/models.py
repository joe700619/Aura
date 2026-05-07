from django.db import models
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey, ParentalManyToManyField
from taggit.models import TaggedItemBase
from wagtail.admin.panels import FieldPanel, MultiFieldPanel
from wagtail.fields import StreamField
from wagtail.models import Page
from wagtail.search import index
from wagtail.snippets.models import register_snippet

from .blocks import ArticleBody


@register_snippet
class BlogCategory(models.Model):
    name = models.CharField(max_length=80, unique=True, verbose_name="分類名稱")
    slug = models.SlugField(max_length=80, unique=True)
    description = models.CharField(max_length=200, blank=True, verbose_name="說明")

    panels = [FieldPanel("name"), FieldPanel("slug"), FieldPanel("description")]

    class Meta:
        verbose_name = "部落格分類"
        verbose_name_plural = "部落格分類"
        ordering = ["name"]

    def __str__(self):
        return self.name


@register_snippet
class Author(models.Model):
    name = models.CharField(max_length=80, verbose_name="姓名")
    role = models.CharField(max_length=80, blank=True, verbose_name="職稱")
    bio = models.TextField(blank=True, verbose_name="簡介")
    avatar_initial = models.CharField(max_length=4, blank=True, verbose_name="頭像文字（如「林」）")

    panels = [
        FieldPanel("name"),
        FieldPanel("role"),
        FieldPanel("bio"),
        FieldPanel("avatar_initial"),
    ]

    class Meta:
        verbose_name = "作者"
        verbose_name_plural = "作者"
        ordering = ["name"]

    def __str__(self):
        return self.name


class BlogPostTag(TaggedItemBase):
    content_object = ParentalKey(
        "blog.BlogPostPage", related_name="tagged_items", on_delete=models.CASCADE
    )


class BlogIndexPage(Page):
    intro_jp = models.CharField(max_length=80, blank=True, default="勤信季刊", verbose_name="日文標題")
    intro_en = models.CharField(max_length=80, blank=True, default="QUARTERLY", verbose_name="英文副標")
    hero_title = models.CharField(max_length=200, blank=True, verbose_name="主標題（可含 <em> 強調）")
    hero_sub = models.TextField(blank=True, verbose_name="副標說明")

    content_panels = Page.content_panels + [
        MultiFieldPanel(
            [FieldPanel("intro_jp"), FieldPanel("intro_en"), FieldPanel("hero_title"), FieldPanel("hero_sub")],
            heading="Hero 區",
        ),
    ]

    subpage_types = ["blog.BlogPostPage"]
    max_count = 1

    class Meta:
        verbose_name = "部落格首頁"

    def get_context(self, request, *args, **kwargs):
        from django.utils import timezone

        ctx = super().get_context(request, *args, **kwargs)
        posts = (
            BlogPostPage.objects.live().descendant_of(self).order_by("-first_published_at")
        )
        active_cat = request.GET.get("cat", "")
        if active_cat:
            posts = posts.filter(categories__slug=active_cat)
        now = timezone.localtime()
        ctx["posts"] = posts
        ctx["featured"] = posts[:2]
        ctx["rest"] = posts[2:]
        ctx["categories"] = BlogCategory.objects.all()
        ctx["active_cat"] = active_cat
        ctx["mast_vol"] = f"{now.month:02d}"
        ctx["mast_month_en"] = now.strftime("%b").upper()
        ctx["mast_year"] = now.year
        ctx["mast_count"] = posts.count()
        return ctx


class BlogPostPage(Page):
    cover = models.ForeignKey(
        "wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+", verbose_name="封面圖"
    )
    cover_caption = models.CharField(max_length=200, blank=True, verbose_name="封面圖說")
    lead = models.TextField(blank=True, verbose_name="導言（出現在標題下方）")
    categories = ParentalManyToManyField("blog.BlogCategory", blank=True, verbose_name="分類")
    authors = ParentalManyToManyField("blog.Author", blank=True, verbose_name="作者")
    tags = ClusterTaggableManager(through=BlogPostTag, blank=True)
    body = StreamField(ArticleBody(), use_json_field=True, blank=True, verbose_name="內文")
    publish_date = models.DateField(null=True, blank=True, verbose_name="顯示日期")
    read_minutes = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="閱讀分鐘數")

    search_fields = Page.search_fields + [
        index.SearchField("lead"),
        index.SearchField("body"),
    ]

    content_panels = Page.content_panels + [
        FieldPanel("cover"),
        FieldPanel("cover_caption"),
        FieldPanel("lead"),
        MultiFieldPanel(
            [FieldPanel("categories"), FieldPanel("authors"), FieldPanel("tags")],
            heading="分類 / 作者 / 標籤",
        ),
        MultiFieldPanel(
            [FieldPanel("publish_date"), FieldPanel("read_minutes")],
            heading="顯示資訊",
        ),
        FieldPanel("body"),
    ]

    parent_page_types = ["blog.BlogIndexPage"]

    class Meta:
        verbose_name = "部落格文章"
