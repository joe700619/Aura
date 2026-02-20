from import_export import resources

class DynamicResource(resources.ModelResource):
    def __init__(self, **kwargs):
        self.fields_to_export = kwargs.pop('fields_to_export', None)
        super().__init__(**kwargs)

    def get_export_fields(self, *args, **kwargs):
        fields = super().get_export_fields(*args, **kwargs)
        if self.fields_to_export:
            return [f for f in fields if f.attribute in self.fields_to_export]
        return fields

def resource_factory(model_class, fields=None):
    """
    Factory to create a ModelResource for a specific model with optional field filtering.
    """
    meta_conf = {
        'model': model_class,
    }
    
    # Create the Meta class dynamically
    Meta = type('Meta', (object,), meta_conf)
    
    # Create the Resource class dynamically
    class_name = f"{model_class.__name__}Resource"
    
    # We don't necessarily need the dynamic class if we just want to filter fields, 
    # but using a factory allows us to customize Meta options easily if needed.
    # However, for simple field filtering, we can just instantiate a subclass.
    
    resource = DynamicResource(fields_to_export=fields)
    resource.Meta = Meta
    return resource
