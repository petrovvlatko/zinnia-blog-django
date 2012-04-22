"""Views for Zinnia archives"""
import datetime

from django.views.generic.dates import ArchiveIndexView
from django.views.generic.dates import YearArchiveView
from django.views.generic.dates import MonthArchiveView
from django.views.generic.dates import WeekArchiveView
from django.views.generic.dates import DayArchiveView
from django.views.generic.dates import TodayArchiveView

from zinnia.models import Entry
from zinnia.views.mixins.archives import ArchiveMixin
from zinnia.views.mixins.archives import PreviousNextPublishedMixin
from zinnia.views.mixins.callable_queryset import CallableQuerysetMixin
from zinnia.views.mixins.templates import \
     EntryQuerysetArchiveTemplateResponseMixin


class EntryArchiveMixin(ArchiveMixin,
                        PreviousNextPublishedMixin,
                        CallableQuerysetMixin,
                        EntryQuerysetArchiveTemplateResponseMixin):
    """
    Mixin combinating :

    - ArchiveMixin configuration centralizing conf for archive views
    - PreviousNextPublishedMixin for returning published archives
    - CallableQueryMixin to force the update of the queryset
    - EntryQuerysetArchiveTemplateResponseMixin to provide a
      custom templates for archives
    """
    queryset = Entry.published.all


class EntryIndex(EntryArchiveMixin, ArchiveIndexView):
    """View returning the archive index"""
    context_object_name = 'entry_list'


class EntryYear(EntryArchiveMixin, YearArchiveView):
    """View returning the archive for a year"""
    make_object_list = True


class EntryMonth(EntryArchiveMixin, MonthArchiveView):
    """View returning the archive for a month"""


class EntryWeek(EntryArchiveMixin, WeekArchiveView):
    """View returning the archive for a week"""

    def get_dated_items(self):
        """Override get_dated_items to add a useful 'week_end_day'
        variable in the extra context of the view"""
        self.date_list, self.object_list, extra_context = super(
            EntryWeek, self).get_dated_items()
        extra_context['week_end_day'] = extra_context[
            'week'] + datetime.timedelta(days=6)
        return self.date_list, self.object_list, extra_context


class EntryDay(EntryArchiveMixin, DayArchiveView):
    """View returning the archive for a day"""


class EntryToday(EntryArchiveMixin, TodayArchiveView):
    """View returning the archive for the current day"""
    template_name_suffix = '_archive_today'

    def get_dated_items(self):
        """Return (date_list, items, extra_context) for this request.
        And defines self.year/month/day for
        EntryQuerysetArchiveTemplateResponseMixin."""
        today = datetime.date.today()
        self.year, self.month, self.day = today.isoformat().split('-')
        return self._get_dated_items(today)
