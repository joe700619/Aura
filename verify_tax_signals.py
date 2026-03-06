from modules.bookkeeping.models import BookkeepingClient, TaxFilingSetting

BookkeepingClient.objects.filter(name="Test Tax Client").delete()

client = BookkeepingClient.objects.create(
    name="Test Tax Client",
    service_type=BookkeepingClient.ServiceType.VAT_BUSINESS
)

setting = TaxFilingSetting.objects.filter(client=client).first()
if setting:
    print(f"SUCCESS: Auto-created setting for {client.name} with form type {setting.form_type}")
else:
    print(f"FAIL: No setting created for {client.name}")

client.delete()
