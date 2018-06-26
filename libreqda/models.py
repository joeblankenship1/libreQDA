# -*- coding: utf-8 -*-
import os
import uuid
try:
    set
except NameError:
    from sets import Set as set
from itertools import chain

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User


class Project(models.Model):
    name = models.CharField(max_length=250, blank=False, verbose_name=_("Nombre"))
    owner = models.ForeignKey(User, related_name='projects', on_delete=models.DO_NOTHING)
    version = models.PositiveIntegerField(default=1)
    comment = models.TextField(null=True, blank=True, verbose_name=_("Comentario"))
    modified_date = models.DateTimeField(auto_now=True)
    creation_date = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return "Project %d-%s" % (self.id, self.name)

    def admin_users(self):
        '''
        Return a list of users that have administration
        privileges for the project.
        '''
        admin_perms = self.permissions.filter(permissions='a')
        admins = User.objects.filter(permissions__in=admin_perms)
        return set(list(admins) + [self.owner])


def get_new_document_path(instance, filename):
    doc_uuid = uuid.uuid4().hex
    return os.path.join(
                    'documents',
                    doc_uuid,
                    filename)


class Document(models.Model):
    name = models.CharField(max_length=250)
    type = models.CharField(max_length=250)
    text = models.TextField(blank=True)
    comment = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to=get_new_document_path)
    uploaded_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    creation_date = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return "Document: %s" % (self.name)


class DocumentInstance(models.Model):
    document = models.ForeignKey(Document, related_name='instances', on_delete=models.DO_NOTHING)
    project = models.ForeignKey(Project, related_name='documents', on_delete=models.DO_NOTHING)
    name = models.CharField(max_length=250)
    type = models.CharField(max_length=250)
    comment = models.TextField(blank=True, null=True)
    modified_date = models.DateTimeField(auto_now=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    creation_date = models.DateTimeField(auto_now_add=True)
    annotations = models.ManyToManyField('Annotation', related_name='documents')

    def __unicode__(self):
        return "DocumentInstance: %s" % (self.name)


class Annotation(models.Model):
    project = models.ForeignKey(Project, related_name='annotations', on_delete=models.DO_NOTHING)
    creation_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    text = models.TextField()
    codes = models.ManyToManyField('Code',
                                   blank=True,
                                   related_name=_('annotations'))

    def __unicode__(self):
        return self.text


class Citation(models.Model):
    # TODO: Document instances are no longer needed, should we remove them ?
    document = models.ForeignKey(DocumentInstance, related_name='citations', on_delete=models.DO_NOTHING)
    created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    creation_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    comment = models.TextField(null=True, blank=True)
    start_paragraph = models.PositiveIntegerField()
    end_paragraph = models.PositiveIntegerField()
    start = models.PositiveIntegerField()
    end = models.PositiveIntegerField()
    text = models.TextField(blank=True, null=True)
    serialized = models.TextField(null=True, blank=True)
    annotations = models.ManyToManyField(Annotation,
                                         null=True,
                                         blank=True,
                                         related_name='citations')

    def __unicode__(self):
        return self.comment

    def touches(self, other):
        tlen = len(self.document.document.text) + 1
        ss = self.start_paragraph * tlen + self.start
        se = self.end_paragraph * tlen + self.end
        os = other.start_paragraph * tlen + other.start
        oe = other.end_paragraph * tlen + other.end

        return ss < os < se or ss < oe < ss

    def codes_str(self):
        return ', '.join(self.codes.all().values_list('name', flat=True))

    def html_color(self):
        if not self.codes.all():
            return 'blank'
        return self.codes.all()[0].html_color()

        return ', '.join(self.codes.all().values_list('name', flat=True))


class Code(models.Model):
    CODE_COLORS = (('d', _('Grey')),
                   ('e', _('Red')),
                   ('w', _('Yellow')),
                   ('s', _('Green')),
                   ('i', _('Blue')),
                   ('b', _('Black')),)
    project = models.ForeignKey(Project, related_name='codes', on_delete=models.DO_NOTHING)
    name = models.TextField(max_length=250, verbose_name=_('Nombre'))
    weight = models.IntegerField(validators=[MinValueValidator(-100),
                                             MaxValueValidator(100)],
                                 verbose_name=_('Peso'))
    created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    color = models.CharField(max_length=1,
                             blank=True,
                             null=True,
                             choices=CODE_COLORS,
                             verbose_name=_('Color'))
    comment = models.TextField(null=True,
                               blank=True,
                               verbose_name=_('Comentario'))
    modified_date = models.DateTimeField(auto_now=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    citations = models.ManyToManyField(Citation, related_name='codes')
    parent_codes = models.ManyToManyField('self',
                                          null=True,
                                          blank=True,
                                          symmetrical=False,
                                          related_name='sub_codes',
                                          verbose_name=_(u'Códigos padre'))

    def __unicode__(self):
        return self.name

    def html_color(self):
        return {
            'd': 'grey',
            'e': 'red',
            'w': 'yellow',
            's': 'green',
            'i': 'blue',
            'b': 'black',
        }.get(self.color)


class Category(models.Model):
    CODE_COLORS = (('d', _('Grey')),
                   ('e', _('Red')),
                   ('w', _('Yellow')),
                   ('s', _('Green')),
                   ('i', _('Blue')),
                   ('b', _('Black')),)
    name = models.TextField(max_length=250)
    color = models.CharField(max_length=1,
                             blank=True,
                             null=True,
                             choices=CODE_COLORS,
                             verbose_name=_('Color'))
    creation_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    comment = models.TextField(null=True, blank=True)
    project = models.ForeignKey(Project, related_name='categories', on_delete=models.DO_NOTHING)
    codes = models.ManyToManyField(Code, related_name='categories')
    citations = models.ManyToManyField(Citation, related_name='categories')
    documents = models.ManyToManyField(Document, related_name='categories')
    annotations = models.ManyToManyField(Annotation, related_name='categories')


class UserProjectPermission(models.Model):
    PROJECT_PERMISSIONS = (('a', _('Administrator')),
                          ('e', _('Editor')),
                          ('g', _('Guest')),)
    user = models.ForeignKey(User, related_name='permissions', on_delete=models.DO_NOTHING)
    project = models.ForeignKey(Project, related_name='permissions', on_delete=models.DO_NOTHING)
    modified_date = models.DateTimeField(auto_now=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    permissions = models.CharField(max_length=1, choices=PROJECT_PERMISSIONS)

    class Meta:
        unique_together = ('user', 'project')

    def is_admin_permission(self):
        return self.permissions == 'a'


class BooleanQuery(models.Model):
    OPERATORS = (('|', _('or')),
                 ('&', _('and')))
    project = models.ForeignKey(Project, related_name=_('boolean_queries'), on_delete=models.DO_NOTHING)
    codes = models.ManyToManyField(Code,
                                   related_name='boolean_queries',
                                   verbose_name=_(u'Códigos'))
    operator = models.CharField(max_length=1,
                                choices=OPERATORS,
                                verbose_name=_('Operadores'))
    name = models.CharField(max_length=250, verbose_name=_('Nombre'))

    def __unicode__(self):
        return self.name

    def execute(self):
        result_set = Set()
        codes = self.codes.all()

        for citation in Citation.objects.filter(document__project=self.project):
            ccodes = citation.codes.all()
            if self.operator == '|':
                tests = False
                for c in codes:
                    if c in ccodes:
                        tests = True
                        break
            elif self.operator == '&':
                tests = True
                for c in codes:
                    if c not in ccodes:
                        tests = False
                        break
            else:
                raise ValueError(_('Unknown operator.'))

            if tests:
                result_set.add(citation)

        return result_set


class SemanticQuery(models.Model):
    OPERATORS = (('u', _('up')),
                 ('d', _('down')),)
    project = models.ForeignKey(Project, related_name=_('semantic_queries'), on_delete=models.DO_NOTHING)
    code = models.ForeignKey(Code,
                             related_name='semantic_operand',
                             verbose_name=_(u'Código'), on_delete=models.DO_NOTHING)
    operator = models.CharField(max_length=1,
                                choices=OPERATORS,
                                verbose_name=_('Operador'))
    name = models.CharField(max_length=250, verbose_name=_('Nombre'))

    def __unicode__(self):
        return self.name

    def execute(self):
        if self.operator == 'd':
            return self.__execute_down()
        elif self.operator == 'u':
            return self.__execute_up()
        else:
            raise ValueError(_('Unknown operator.'))

    def __execute_up(self):
        result_set = Set()

        for citation in self.code.citations.all():
            result_set.add(citation)
        for parent in self.code.parent_codes.all():
            for citation in parent.citations.all():
                result_set.add(citation)

        return result_set

    def __execute_down(self):
        hierarchy = Set()
        result_set = Set()

        def traverse_hierarchy(code):
            hierarchy.add(code)
            for sub_code in code.sub_codes.all():
                if sub_code not in hierarchy:
                    traverse_hierarchy(sub_code)
        traverse_hierarchy(self.code)

        for code in hierarchy:
            for citation in code.citations.all():
                result_set.add(citation)

        return result_set


class ProximityQuery(models.Model):
    OPERATORS = (('c', _('coocurrencia')),)
    project = models.ForeignKey(Project, related_name='proximity_queries', on_delete=models.DO_NOTHING)
    code1 = models.ForeignKey(Code,
                              related_name='proximity_operand1',
                              verbose_name=_(u'Código 1'), on_delete=models.DO_NOTHING)
    code2 = models.ForeignKey(Code,
                              related_name='proximity_operand2',
                              verbose_name=_(u'Código 2'), on_delete=models.DO_NOTHING)
    operator = models.CharField(max_length=1,
                                choices=OPERATORS,
                                verbose_name=_('Operador'))
    name = models.CharField(max_length=250, verbose_name=_('Nombre'))

    def __unicode__(self):
        return self.name

    def execute(self):
        if self.operator == 'c':
            return self.__execute_cooccurrence()
        else:
            raise ValueError(_('Unknown operator.'))

    def __execute_cooccurrence(self):
        result_set = Set()

        for doc in self.project.documents.all():
            with_c1 = self.code1.citations.filter(document=doc)
            with_c2 = self.code2.citations.filter(document=doc)

            for c in with_c1:
                for cc in with_c2:
                    if c != cc and c.touches(cc):
                        result_set.add(c)
                        result_set.add(cc)

        return result_set


class SetQuery(models.Model):
    OPERATORS = (('+', _('union')),
                 ('^', _('intersection')))
    project = models.ForeignKey(Project, related_name=_('set_queries'), on_delete=models.DO_NOTHING)
    boolean_queries = models.ManyToManyField(BooleanQuery,
                                             blank=True,
                                             related_name='containing_queries',
                                             verbose_name=_('Consultas booleanas'))
    proximity_queries = models.ManyToManyField(ProximityQuery,
                                               blank=True,
                                               related_name='containing_queries',
                                               verbose_name=_('Consultas proximidad'))
    semantic_queries = models.ManyToManyField(SemanticQuery,
                                              blank=True,
                                              related_name='containing_queries',
                                              verbose_name=_(u'Consultas semánticas'))
    operator = models.CharField(max_length=1,
                                choices=OPERATORS,
                                verbose_name=_('Operador'))
    name = models.CharField(max_length=250, verbose_name=_('Nombre'))

    def __unicode__(self):
        return self.name

    def __queries(self):
        return list(chain(self.boolean_queries.all(),
                          self.proximity_queries.all(),
                          self.semantic_queries.all()))

    def execute(self):
        queries = self.__queries()
        result_set = queries[0].execute()
        for q in queries[1:]:
            if self.operator == '+':
                result_set = result_set.union(q.execute())
            elif self.operator == '^':
                result_set = result_set.intersection(q.execute())
            else:
                raise ValueError(_('Unknown operator.'))
        return result_set
