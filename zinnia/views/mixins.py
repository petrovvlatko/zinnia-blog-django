"""Mixins for Zinnia views"""
from datetime import datetime

from django.contrib.auth.views import login
from django.views.generic.base import TemplateView
from django.views.generic.base import TemplateResponseMixin
from django.core.exceptions import ImproperlyConfigured

from zinnia.settings import PAGINATION
from zinnia.settings import ALLOW_EMPTY
from zinnia.settings import ALLOW_FUTURE


class ArchiveMixin(object):
    """Mixin centralizing the configuration
    of the archives views"""
    paginate_by = PAGINATION
    allow_empty = ALLOW_EMPTY
    allow_future = ALLOW_FUTURE
    date_field = 'creation_date'
    month_format = '%m'
    week_format = '%W'


class CallableQuerysetMixin(object):
    """Mixin for handling a callable queryset.
    Who will force the update of the queryset.
    Related to issue http://code.djangoproject.com/ticket/8378"""
    queryset = None

    def get_queryset(self):
        """Check that the queryset is defined and call it"""
        if self.queryset is None:
            raise ImproperlyConfigured(
                u"'%s' must define 'queryset'" % self.__class__.__name__)
        return self.queryset()


class PreviousNextPublishedMixin(object):
    """Mixin for correcting the previous/next
    context variable to return dates with published datas"""

    def get_previous_next_published(self, date, period, previous=True):
        """Return the next or previous published date period with Entries"""
        dates = list(self.get_queryset().dates(
            'creation_date', period,
            order=previous and 'ASC' or 'DESC'))
        try:
            index = dates.index(date)
        except ValueError:
            if previous and dates:
                return dates[-1].date()
            else:
                return None
        if index == 0:
            return None
        return dates[index - 1].date()

    def get_next_month(self, date):
        """Get the next month with published Entries"""
        return self.get_previous_next_published(
            datetime(date.year, date.month, 1), 'month',
            previous=False)

    def get_previous_month(self, date):
        """Get the previous month with published Entries"""
        return self.get_previous_next_published(
            datetime(date.year, date.month, 1), 'month',
            previous=True)

    def get_next_day(self, date):
        """Get the next day with published Entries"""
        return self.get_previous_next_published(
            datetime(date.year, date.month, date.day),
            'day', previous=False)

    def get_previous_day(self, date):
        """Get the previous day with published Entries"""
        return self.get_previous_next_published(
            datetime(date.year, date.month, date.day),
            'day', previous=True)


class MimeTypeMixin(object):
    """Mixin for handling the mimetype parameter"""
    mimetype = None

    def get_mimetype(self):
        """Return the mimetype of the response"""
        if self.mimetype is None:
            raise ImproperlyConfigured(
                u"%s requires either a definition of "
                "'mimetype' or an implementation of 'get_mimetype()'" % \
                self.__class__.__name__)
        return self.mimetype


class TemplateMimeTypeView(MimeTypeMixin, TemplateView):
    """TemplateView with a configurable mimetype"""

    def render_to_response(self, context, **kwargs):
        """Render the view with a custom mimetype"""
        return super(TemplateMimeTypeView, self).render_to_response(
            context, mimetype=self.get_mimetype(), **kwargs)


class EntryQuerysetArchiveTemplateResponseMixin(TemplateResponseMixin):
    """Return a custom template name for the archive views based
    on the type of the archives and the value of the date."""
    template_name_suffix = '_archive'

    def get_archive_part_value(self, part):
        try:
            return getattr(self, 'get_%s' % part)()
        except AttributeError:
            return None

    def get_template_names(self):
        """Return a list of template names to be used for the view"""
        year = self.get_archive_part_value('year')
        week = self.get_archive_part_value('week')
        month = self.get_archive_part_value('month')
        day = self.get_archive_part_value('day')

        path = 'zinnia/archives'
        template_name = 'entry%s.html' % self.template_name_suffix
        templates = ['zinnia/%s' % template_name,
                     '%s/%s' % (path, template_name)]
        if year:
            templates.append(
                '%s/%s/%s' % (path, year, template_name))
        if week:
            templates.extend([
                '%s/week/%s/%s' % (path, week, template_name),
                '%s/%s/week/%s/%s' % (path, year, week, template_name)])
        if month:
            templates.extend([
                '%s/month/%s/%s' % (path, month, template_name),
                '%s/%s/month/%s/%s' % (path, year, month, template_name)])
        if day:
            templates.extend([
                '%s/day/%s/%s' % (path, day, template_name),
                '%s/%s/day/%s/%s' % (path, year, day, template_name),
                '%s/month/%s/day/%s/%s' % (path, month, day, template_name),
                '%s/%s/%s/%s/%s' % (path, year, month, day, template_name)])

        if self.template_name is not None:
            templates.append(self.template_name)

        templates.reverse()
        return templates


class EntryQuerysetTemplateResponseMixin(TemplateResponseMixin):
    """Return a custom template name for views returning
    a queryset of Entry filtered by another model."""
    model_type = None
    model_name = None

    def get_model_type(self):
        """Return the model type for templates"""
        if self.model_type is None:
            raise ImproperlyConfigured(
                u"%s requires either a definition of "
                "'model_type' or an implementation of 'get_model_type()'" % \
                self.__class__.__name__)
        return self.model_type

    def get_model_name(self):
        """Return the model name for templates"""
        if self.model_name is None:
            raise ImproperlyConfigured(
                u"%s requires either a definition of "
                "'model_name' or an implementation of 'get_model_name()'" % \
                self.__class__.__name__)
        return self.model_name

    def get_template_names(self):
        """Return a list of template names to be used for the view"""
        model_type = self.get_model_type()
        model_name = self.get_model_name()

        templates = [
            'zinnia/%s/%s/entry_list.html' % (model_type, model_name),
            'zinnia/%s/%s_entry_list.html' % (model_type, model_name),
            'zinnia/%s/entry_list.html' % model_type,
            'zinnia/entry_list.html']

        if self.template_name is not None:
            templates.insert(0, self.template_name)

        return templates


class EntryProtectionMixin(object):
    """Mixin returning a login view if the current
    entry need authentication and password view
    if the entry is protected by a password"""
    error = False
    session_key = 'zinnia_entry_%s_password'

    def login(self):
        """Return the login view"""
        return login(self.request, 'zinnia/login.html')

    def password(self):
        """Return the password form"""
        return self.response_class(request=self.request,
                                   template='zinnia/password.html',
                                   context={'error': self.error})

    def get(self, request, *args, **kwargs):
        """Do the login protection"""
        response = super(EntryProtectionMixin, self).get(
            request, *args, **kwargs)
        if self.object.login_required and not request.user.is_authenticated():
            return self.login()
        if self.object.password and self.object.password != \
           self.request.session.get(self.session_key % self.object.pk):
            return self.password()
        return response

    def post(self, request, *args, **kwargs):
        """Do the login protection"""
        self.object = self.get_object()
        self.login()
        if self.object.password:
            entry_password = self.request.POST.get('entry_password')
            if entry_password:
                if entry_password == self.object.password:
                    self.request.session[self.session_key % \
                                         self.object.pk] = self.object.password
                    return self.get(request, *args, **kwargs)
                else:
                    self.error = True
            return self.password()
        return self.get(request, *args, **kwargs)
