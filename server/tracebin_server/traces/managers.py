from django.db.models import Manager
from django.db.models.query import QuerySet


class InheritanceQuerySet(QuerySet):
    @property
    def _child_rels(self):
        return [
            rel
            for rel in self.model._meta.get_all_related_objects()
            if rel.field.rel.parent_link
        ]

    def iterator(self):
        for obj in super(InheritanceQuerySet, self).iterator():
            for rel in self._child_rels:
                if getattr(obj, rel.get_cache_name(), None) is not None:
                    yield getattr(obj, rel.var_name)
                    break
            else:
                yield obj


class InheritanceManager(Manager):
    use_for_related_fields = True

    def get_query_set(self):
        qs = InheritanceQuerySet(self.model, using=self._db)
        return qs.select_related(*[rel.var_name for rel in qs._child_rels])
