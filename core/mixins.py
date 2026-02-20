from django.db.models import Min, Max

class PrevNextMixin:
    """
    Mixin to add previous and next object navigation to context.
    Expects `self.object` to be set (UpdateView/DetailView).
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Ensure we have an object to navigate from
        if not hasattr(self, 'object') or not self.object:
            return context

        # Determine the queryset to use for navigation.
        # Ideally, this should respect any filtering applied in get_queryset(),
        # but for simplicity in administrative views, we typically use the default manager.
        # If get_queryset is overridden with complex logic, navigation might need adjustment.
        queryset = self.model.objects.all()

        current_pk = self.object.pk

        # Next Object (pk > current_pk, order by pk asc)
        next_obj = queryset.filter(pk__gt=current_pk).order_by('pk').first()
        
        # Previous Object (pk < current_pk, order by pk desc)
        prev_obj = queryset.filter(pk__lt=current_pk).order_by('-pk').first()

        context['next_object'] = next_obj
        context['prev_object'] = prev_obj
        
        return context


class CopyMixin:
    """
    Mixin to handle copying an existing object when creating a new one.
    Expects `?source_id=<pk>` in the URL query parameters.
    
    Usage in CreateView:
        class MyModelCreateView(CopyMixin, CreateView):
            model = MyModel
            fields = [...]
            
            def get_copy_exclude_fields(self):
                # Customize which fields should NOT be copied
                return ['id', 'unique_field', 'created_at']
    """
    
    def get_copy_exclude_fields(self):
        """
        Override this method to specify which fields should be excluded from copying.
        By default, excludes: id, pk, created_at, updated_at, created_by, updated_by
        """
        return ['id', 'pk', 'created_at', 'updated_at', 'created_by', 'updated_by']
    
    def get_initial(self):
        """Handle copying data from source object if source_id is provided."""
        initial = super().get_initial()
        source_id = self.request.GET.get('source_id')
        
        if source_id:
            try:
                source_object = self.model.objects.get(pk=source_id)
                exclude_fields = self.get_copy_exclude_fields()
                
                # Copy all fields that are in self.fields (if defined)
                if hasattr(self, 'fields') and self.fields:
                    fields_to_copy = self.fields
                else:
                    # If fields not defined, copy all model fields except excluded
                    fields_to_copy = [f.name for f in self.model._meta.get_fields() 
                                     if not f.many_to_many and not f.one_to_many]
                
                for field_name in fields_to_copy:
                    if field_name not in exclude_fields:
                        try:
                            value = getattr(source_object, field_name, None)
                            if value is not None:
                                initial[field_name] = value
                        except AttributeError:
                            # Skip fields that don't exist on the source object
                            pass
                            
            except self.model.DoesNotExist:
                # Source object not found, proceed normally
                pass
        
        return initial


class ListActionMixin:
    """
    Mixin for ListView to provide model metadata for list actions.
    Automatically adds model_app_label, model_name, and model_class to context.
    
    Usage in ListView:
        class MyModelListView(ListActionMixin, ListView):
            model = MyModel
            template_name = 'myapp/list.html'
    """
    
    # Optional: Override to customize the create button label
    create_button_label = None
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['model_app_label'] = self.model._meta.app_label
        context['model_name'] = self.model._meta.model_name
        context['model_class'] = self.model
        
        # Add custom create button label if set
        if self.create_button_label:
            context['create_button_label'] = self.create_button_label
        
        return context
