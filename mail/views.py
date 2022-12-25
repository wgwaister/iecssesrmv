import random, json, re, os, pytz, base64, hashlib, requests, string, zipfile, shutil
from time import sleep

from django.shortcuts import *
from datetime import datetime
from email.header import make_header
import datetime as dt
from django.template.loader import render_to_string
from django.views.generic import *
from django.http import *
from django.contrib.auth import *
from django.contrib.auth.views import *
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from guardian.decorators import *
from guardian.shortcuts import *
from django.contrib import messages
from django.conf import settings
from django.core.mail import EmailMessage, EmailMultiAlternatives
from .forms import *
from .models import *
from .resources import *
from tablib import Dataset
# import plotly.express as px
# import plotly.graph_objs as go
# import plotly.offline as po
# import pandas as pd
from itsdangerous import URLSafeTimedSerializer as utsr
from django.contrib.auth import password_validation
from django.core.files.storage import *
import django.contrib.auth.views as auth_views


# 測試GIT用嗨
class ProjectView(ListView):
    queryset = Company.objects.all()
    template_name = 'project/Project.html'
    context_object_name = 'Company'
    form_class = ProjectSearch

    @method_decorator(login_required(login_url='login'))
    @method_decorator(permission_required('SE_server.view_company', return_403=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(ProjectView, self).get_context_data(**kwargs)
        get_perm = get_objects_for_user(user=self.request.user, perms=('SE_server.view_project',))
        context['SearchValue'] = False
        if self.request.method == "POST":
            company_code_input = self.request.POST.get('CompanyCode')
            project_name_input = self.request.POST.get('ProjectName')
            if company_code_input not in 'default':
                company = Company.objects.filter(CompanyCode=company_code_input)
                project_name = project_name_input
                for c in company:
                    if project_name:
                        c.ProjectCount = get_perm.filter(CompanyCode=c, ProjectName__contains=project_name).count()
                        c.save()
                    else:
                        c.ProjectCount = get_perm.filter(CompanyCode=c).count()
                        c.save()
            else:
                company = Company.objects.all()
                project_name = project_name_input
                for c in company:
                    if project_name:
                        c.ProjectCount = get_perm.filter(CompanyCode=c, ProjectName__contains=project_name).count()
                        c.save()
                    else:
                        c.ProjectCount = get_perm.filter(CompanyCode=c).count()
                        c.save()
            if Project.objects.filter(ProjectName__contains=project_name):
                context['NULL'] = False
            else:
                context['NULL'] = True
            context['Company'] = company
            context['ProjectName'] = project_name
            context['SearchValue'] = True

        else:
            company = Company.objects.exclude(CompanyCode='AAA')
            user = self.request.user
            group = user.groups.all()
            for c in company:
                c.ProjectCount = get_perm.filter(CompanyCode=c).count()
                c.save()
            context['Company'] = company
        context['time'] = datetime.now()
        context['Form'] = self.form_class
        context['CompanyList'] = Company.objects.all()
        return context


class ProjectCreateView(View):
    form_class = ProjectForm
    template_name = 'project/Project_Create_Forms.html'

    @method_decorator(login_required(login_url='login'))
    @method_decorator(permission_required('SE_server.exe_company', (Company, 'CompanyCode', 'pk'), return_403=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, pk):
        company = Company.objects.get(pk=pk)
        print(pk)
        print(company)
        year = datetime.now()
        code = company.Company.filter(ProjectCode__contains=str(year)[0:4])
        project_count = code.count()
        project_code = []
        if code:
            for c in code:
                project_code.append(c.ProjectCode[c.ProjectCode.index(str(year)[0:4]) + 5:])
            for i in range(project_count + 1):
                if i + 1 < 9:
                    temp = '0' + str(i + 1)
                    if temp not in project_code:
                        project_code = company.CompanyCode + str(year)[0:4] + 'P' + temp
                        break
        else:
            project_code = company.CompanyCode + str(year)[0:4] + 'P01'
        context = {
            'Company': company,
            'form': self.form_class,
            'Project_Code': project_code
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)

        if form.is_valid():
            company_code = request.POST.get('CompanyCode')
            project_name = request.POST.get('ProjectName')
            start_time = request.POST.get('CalculateStartDate')
            end_time = request.POST.get('CalculateEndDate')
            project_code = request.POST.get('ProjectCode')
            company = Company.objects.get(CompanyCode=company_code)
            project = company.Company.filter(ProjectName=project_name)
            if project.exists():
                messages.error(request, '專案名稱:%s已存在' % project_name)
                return redirect('/')
            datetime_format = ('%Y-%m-%dT%H:%M')
            start = datetime.strptime(start_time, datetime_format)
            end = datetime.strptime(end_time, datetime_format)
            if end < start:
                messages.error(request, '結束時間不能先於開始時間')
                return redirect('/')
            form.save()
            project = Project.objects.get(pk=project_code)
            group = project.CompanyCode.GroupCode
            ex = '%s_執行人' % project.CompanyCode.CompanyName
            technology = Group.objects.get(name=ex)
            project_M = Group.objects.get(name='專案經理')
            admin = Group.objects.get(name='系統管理員')
            assign_perm('view_project', project_M, project)

            assign_perm('view_project', technology, project)
            assign_perm('exe_project', technology, project)

            assign_perm('view_project', admin, project)
            assign_perm('change_project', admin, project)
            assign_perm('add_project', admin, project)
            assign_perm('delete_project', admin, project)
            assign_perm('exe_project', admin, project)

            assign_perm('view_project', group, project)
            return redirect('/')
        else:
            messages.error(request, '輸入資訊有誤，請確認輸入資訊')
            return redirect('/')


class ProjectEditView(View):
    form_class = ProjectForm
    template_name = 'project/Project_Edit.html'

    @method_decorator(login_required(login_url='login'))
    @method_decorator(permission_required('SE_server.exe_project', (Project, 'ProjectCode', 'pk'), return_403=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, pk):
        request.session['Project_Edit_from'] = request.META.get('HTTP_REFERER', '/')
        project = Project.objects.get(pk=pk)
        form = self.form_class(instance=project)
        context = {
            'form': form,
            'Project': project,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        project = Project.objects.get(pk=pk)
        form = self.form_class(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, '修改成功')
            return HttpResponseRedirect(request.session['Project_Edit_from'])
        else:
            messages.error(request, '輸入資訊有誤，請確認輸入資訊')
            return HttpResponseRedirect(request.session['Project_Edit_from'])


class ProjectDeleteView(DeleteView):
    model = Project
    template_name = 'project/Project_Delete.Html'
    context_object_name = 'Project'
    success_url = '/'

    @method_decorator(login_required(login_url='login'))
    @method_decorator(permission_required('SE_server.delete_project', return_403=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class ProjectInformation(DetailView):
    model = Project
    context_object_name = 'Project'
    template_name = 'project/Project_Information.html'

    @method_decorator(login_required(login_url='login'))
    @method_decorator(permission_required('SE_server.view_project', (Project, 'ProjectCode', 'pk'), return_403=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ProjectInformation, self).get_context_data(**kwargs)
        pk = str(kwargs.get('object'))
        project = Project.objects.get(pk=pk)
        unitName = []
        unitCode = []
        project_member_list = project.TestML.all().order_by('UnitName')
        project_mail_list = project.Mail.all()
        project.PersonCount = project_member_list.count()
        project.MailCount = project_mail_list.count()
        for member in project_member_list:
            if member.UnitName not in unitName:
                unitName.append(member.UnitName)
        for i in range(1, len(unitName) + 1):
            unitCode.append('A' + '%02d' % i)
        for member in project_member_list:
            member.Unit = unitCode[unitName.index(member.UnitName)]
            member.save()
        project.UnitList = sorted(unitName)
        project.save()
        context['Project'] = project
        return context


class TestMemberView(DetailView):
    model = Project
    context_object_name = 'Project'
    template_name = 'project/Test_Member_Detail.html'

    @method_decorator(login_required(login_url='login'))
    @method_decorator(permission_required('SE_server.view_project', (Project, 'ProjectCode', 'pk'), return_403=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(TestMemberView, self).get_context_data(**kwargs)
        pk = str(kwargs.get('object'))
        project = Project.objects.get(pk=pk)
        project_member_list = project.TestML.all().order_by('UnitName')
        email_duplicate = []
        project_member_temp_list = project.TestML_Temp.all()
        if project_member_temp_list:
            for temp_member in project_member_temp_list:
                if project_member_list.filter(Email=temp_member.Email).exists():
                    email_duplicate.append(temp_member)
                    temp_member.delete()
                    continue
                if project_member_list.filter(MemberNumber=temp_member.MemberNumber).exists():
                    email_duplicate.append(temp_member)
                    temp_member.delete()
                    continue
            context['email_duplicate'] = email_duplicate
            email_duplicate = []
        project.PersonCount = project_member_list.count()
        project.save()
        if project_member_list:
            context['Have'] = True
        else:
            context['Have'] = False
        context['Project'] = project
        return context


class TestMemberUploadView(View):
    template_name = 'project/Test_Member_Upload.html'
    form_class = UploadForm

    @method_decorator(login_required(login_url='login'))
    @method_decorator(permission_required('SE_server.exe_project', (Project, 'ProjectCode', 'pk'), return_403=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        request.session['Test_Member_Upload_from'] = request.META.get('HTTP_REFERER', '/')
        context = {
            'Form': self.form_class
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        project = Project.objects.get(pk=pk)
        test_member_resource = TestMemberResources(ProjectCode=project)
        dataset = Dataset()
        new_test_member = request.FILES['upload']
        if not (new_test_member.name.endswith('csv') or new_test_member.name.endswith('json')):
            messages.error(request, '錯誤檔案類型,請選擇副檔名為csv或者json的檔案')
            return HttpResponseRedirect(request.session['Test_Member_Upload_from'])
        if new_test_member.name.endswith('csv'):
            imported_data = dataset.load(new_test_member.read().decode(), format='csv')
        if new_test_member.name.endswith('json'):
            imported_data = dataset.load(new_test_member.read().decode(), format='json')
        result = test_member_resource.import_data(dataset, raise_errors=True, dry_run=True)  # Test the data import
        if not result.has_errors():
            test_member_resource.import_data(dataset, dry_run=False)  # Actually import now
        else:
            messages.error(request, '格式錯誤,請確認內容包含流水號(Number),部門名稱(UnitName),電子郵件(Email)')
            return HttpResponseRedirect(request.session['Test_Member_Upload_from'])
        test_member_list = project.TestML.all().order_by('UnitName')
        test_member_temp_list = project.TestML_Temp.all()
        for temp_member in test_member_temp_list:
            if not test_member_list.filter(MemberNumber=temp_member.MemberNumber).exists():
                if not test_member_list.filter(Email=temp_member.Email).exists():
                    TestMemberList.objects.create(MemberNumber=temp_member.MemberNumber, UnitName=temp_member.UnitName,
                                                  Email=temp_member.Email, ProjectCode=temp_member.ProjectCode)
                    temp_member.delete()
        project.PersonCount = test_member_list.count()
        project.save()
        unit_name = []
        unit_code = []
        for member in test_member_list:
            if member.UnitName not in unit_name:
                unit_name.append(member.UnitName)
        for i in range(1, len(unit_name) + 1):
            unit_code.append('A' + '%02d' % i)
        for member in test_member_list:
            member.Unit = unit_code[unit_name.index(member.UnitName)]
            member.save()
        for test_member in test_member_list:
            src_hash = test_member.ProjectCode.ProjectCode[0:2] + test_member.Unit + test_member.MemberNumber
            src_hash_s = src_hash + test_member.ProjectCode.ProjectCode.lower()[0:2]
            m2 = hashlib.md5()
            m2.update(src_hash_s.encode(encoding='utf-8'))
            key = src_hash + (m2.hexdigest()[0:3]).upper()
            test_member.UUID = key
            test_member.save()
        return HttpResponseRedirect(request.session['Test_Member_Upload_from'])


class TestMemberUploadUIDView(View):
    template_name = 'project/Test_Member_Upload_UID.html'
    form_class = UploadForm

    @method_decorator(login_required(login_url='login'))
    @method_decorator(permission_required('SE_server.exe_project', (Project, 'ProjectCode', 'pk'), return_403=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        request.session['Test_Member_Upload_from'] = request.META.get('HTTP_REFERER', '/')
        context = {
            'Form': self.form_class
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        project = Project.objects.get(pk=pk)
        test_member_resource = TestMemberUIDResources(ProjectCode=project)
        dataset = Dataset()
        new_test_member = request.FILES['upload']
        if not (new_test_member.name.endswith('csv') or new_test_member.name.endswith('json')):
            messages.error(request, '錯誤檔案類型,請選擇副檔名為csv或者json的檔案')
            return HttpResponseRedirect(request.session['Test_Member_Upload_from'])
        if new_test_member.name.endswith('csv'):
            imported_data = dataset.load(new_test_member.read().decode(), format='csv')
        if new_test_member.name.endswith('json'):
            imported_data = dataset.load(new_test_member.read().decode(), format='json')
        result = test_member_resource.import_data(dataset, raise_errors=True, dry_run=True)  # Test the data import
        if not result.has_errors():
            test_member_resource.import_data(dataset, dry_run=False)  # Actually import now
        else:
            messages.error(request, '格式錯誤,請確認內容包含流水號(Number),部門名稱(UnitName),UUID,電子郵件(Email)')
            return HttpResponseRedirect(request.session['Test_Member_Upload_from'])
        test_member_list = project.TestML.all().order_by('UnitName')
        test_member_temp_list = project.TestML_Temp.all()
        for temp_member in test_member_temp_list:
            if not test_member_list.filter(Email=temp_member.Email).exists():
                TestMemberList.objects.create(MemberNumber=temp_member.MemberNumber, UnitName=temp_member.UnitName,
                                              Email=temp_member.Email, ProjectCode=temp_member.ProjectCode,
                                              UUID=temp_member.UUID)
                temp_member.delete()
        project.PersonCount = test_member_list.count()
        project.save()
        unit_name = []
        unit_code = []
        for member in test_member_list:
            if member.UnitName not in unit_name:
                unit_name.append(member.UnitName)
        for i in range(1, len(unit_name) + 1):
            unit_code.append('A' + '%02d' % i)
        for member in test_member_list:
            member.Unit = unit_code[unit_name.index(member.UnitName)]
            member.save()
        return HttpResponseRedirect(request.session['Test_Member_Upload_from'])


class TestMemberCreateView(View):
    model = Project
    context_object_name = 'Project'
    template_name = 'project/Test_Member_Create.html'
    form_class = TestMemberForm

    @method_decorator(login_required(login_url='login'))
    @method_decorator(permission_required('SE_server.exe_project', (Project, 'ProjectCode', 'pk'), return_403=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, pk):
        request.session['Test_Member_Create_from'] = request.META.get('HTTP_REFERER', '/')
        project = Project.objects.get(pk=pk)
        context = {
            'Project': project,
            'form': self.form_class,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            form.save()
            pk = kwargs.get('pk')
            project = Project.objects.get(pk=pk)
            test_member_list = project.TestML.all().order_by('UnitName')
            unitName = []
            unitCode = []
            project.PersonCount = test_member_list.count()
            project.save()
            for member in test_member_list:
                if member.UnitName not in unitName:
                    unitName.append(member.UnitName)
            for i in range(1, len(unitName) + 1):
                unitCode.append('A' + '%02d' % i)
            for member in test_member_list:
                member.Unit = unitCode[unitName.index(member.UnitName)]
                member.save()
            for test_member in test_member_list:
                srcHash = test_member.ProjectCode.ProjectCode[0:2] + test_member.Unit + test_member.MemberNumber
                srcHashS = srcHash + test_member.ProjectCode.ProjectCode.lower()[0:2]
                m2 = hashlib.md5()
                m2.update(srcHashS.encode(encoding='utf-8'))
                key = srcHash + (m2.hexdigest()[0:3]).upper()
                test_member.UUID = key
                test_member.save()
            return HttpResponseRedirect(request.session['Test_Member_Create_from'])
        else:
            messages.error(request, '輸入資訊有誤，請確認輸入資訊')
            return HttpResponseRedirect(request.session['Test_Member_Create_from'])


class TestMemberEditView(View):
    context_object_name = 'Member'
    template_name = 'project/Test_Member_Edit.html'
    form_class = TestMemberForm

    @method_decorator(login_required(login_url='login'))
    @method_decorator(permission_required('SE_server.exe_project', (Project, 'ProjectCode', 'pk'), return_403=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, pk, id):
        request.session['Test_Member_Edit_from'] = request.META.get('HTTP_REFERER', '/')
        project = Project.objects.get(pk=pk)
        member = project.TestML.get(pk=id)
        form = self.form_class(instance=member)
        context = {
            'form': form,
            'Member': member,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk, id):
        project = Project.objects.get(pk=pk)
        member = project.TestML.get(pk=id)
        form = self.form_class(request.POST, instance=member)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(request.session['Test_Member_Edit_from'])
        else:
            messages.error(request, '輸入資訊有誤，請確認輸入資訊')
            return HttpResponseRedirect(request.session['Test_Member_Edit_from'])


class TestMemberDeleteView(View):
    model = TestMemberList
    template_name = 'project/Test_Member_Delete.html'
    context_object_name = 'TestMemberList'
    form_class = TestMemberForm

    @method_decorator(login_required(login_url='login'))
    @method_decorator(permission_required('SE_server.exe_project', (Project, 'ProjectCode', 'pk'), return_403=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, pk, id):
        request.session['Test_Member_Delete_from'] = request.META.get('HTTP_REFERER', '/')
        project = Project.objects.get(pk=pk)
        member = project.TestML.get(pk=id)
        context = {
            'Member': member,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk, id):
        project = Project.objects.get(pk=pk)
        member = project.TestML.get(pk=id)
        member.delete()
        project.PersonCount = project.TestML.all().count()
        project.save()
        return HttpResponseRedirect(request.session['Test_Member_Delete_from'])


class ProjectMail(DetailView):
    model = Project
    template_name = 'project/Project_Mail.html'
    context_object_name = 'Project'

    @method_decorator(login_required(login_url='login'))
    @method_decorator(permission_required('SE_server.view_project', (Project, 'ProjectCode', 'pk'), return_403=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ProjectMail, self).get_context_data(**kwargs)
        pk = str(kwargs.get('object'))
        project = Project.objects.get(pk=pk)
        project_mail_list = project.Mail.all()
        project.MailCount = project_mail_list.count()
        project.save()
        if project_mail_list:
            context['Have'] = True
        else:
            context['Have'] = False
        context['Project'] = project
        return context


class ProjectMailUploadView(View):
    template_name = 'project/Project_Mail_Upload.html'
    form_class = UploadForm

    @method_decorator(login_required(login_url='login'))
    @method_decorator(permission_required('SE_server.exe_project', (Project, 'ProjectCode', 'pk'), return_403=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, pk):
        request.session['Project_Mail_Upload'] = request.META.get('HTTP_REFERER', '/')
        context = {
            'Form': self.form_class
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        project = Project.objects.get(pk=pk)
        project_mail_resource = ProjectMailResources(ProjectCode=project)
        dataset = Dataset()
        new_project_mail = request.FILES['upload']
        if not (new_project_mail.name.endswith('csv') or new_project_mail.name.endswith('json')):
            messages.error(request, '錯誤檔案類型,請選擇副檔名為csv或者json的檔案')
            return HttpResponseRedirect(request.session['Project_Mail_Upload'])
        if new_project_mail.name.endswith('csv'):
            imported_data = dataset.load(new_project_mail.read().decode(), format='csv')
        if new_project_mail.name.endswith('json'):
            imported_data = dataset.load(new_project_mail.read().decode(), format='json')
        result = project_mail_resource.import_data(dataset, dry_run=True)  # Test the data import
        if not result.has_errors():
            project_mail_resource.import_data(dataset, dry_run=False)  # Actually import now
        else:
            messages.error(request,
                           '格式錯誤,請確認內容包含信件編號(Number),有無附件(HasAtt),信件位址(Address),開啟(Open),點擊(Click),附件(Attachment),id')
            return HttpResponseRedirect(request.session['Project_Mail_Upload'])
        project.MailCount = project.Mail.all().count()
        project.save()
        return HttpResponseRedirect(request.session['Project_Mail_Upload'])


class ProjectMailCreateView(View):
    model = Project
    context_object_name = 'Project'
    template_name = 'project/Project_Mail_Create.html'
    form_class = ProjectMailForm

    @method_decorator(login_required(login_url='login'))
    @method_decorator(permission_required('SE_server.exe_project', (Project, 'ProjectCode', 'pk'), return_403=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, pk):
        request.session['Project_Mail_Create_from'] = request.META.get('HTTP_REFERER', '/')
        project = Project.objects.get(pk=pk)
        mail_list = project.Mail.all()
        mail_count = mail_list.count()
        mail_number = []
        number = 0
        for mail in mail_list:
            mail_number.append(int(mail.MailNumber[4:]))
        for i in range(mail_count + 1):
            if i + 1 not in mail_number:
                number = i + 1
                break
        mail_number_tmp = 'Mail' + str(number)
        context = {
            'Project': project,
            'form': self.form_class,
            'mail_number_tmp': mail_number_tmp,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        form = self.form_class(request.POST)
        project = Project.objects.get(pk=pk)
        if form.is_valid():
            form.save()
            project.MailCount = project.Mail.all().count()
            project.save()
            return HttpResponseRedirect(request.session['Project_Mail_Create_from'])
        else:
            messages.error(request, '輸入資訊有誤，請確認輸入資訊')
            return HttpResponseRedirect(request.session['Project_Mail_Create_from'])


class ProjectMailEditView(View):
    model = Project
    context_object_name = 'Project'
    template_name = 'project/Project_Mail_Edit.html'
    form_class = ProjectMailForm

    @method_decorator(login_required(login_url='login'))
    @method_decorator(permission_required('SE_server.exe_project', (Project, 'ProjectCode', 'pk'), return_403=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, pk, id):
        request.session['Project_Mail_Edit_from'] = request.META.get('HTTP_REFERER', '/')
        project = Project.objects.get(pk=pk)
        mail = project.Mail.get(pk=id)
        form = self.form_class(instance=mail)
        context = {
            'form': form,
            'Mail': mail,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk, id):
        project = Project.objects.get(pk=pk)
        mail = project.Mail.get(pk=id)
        form = self.form_class(request.POST, instance=mail)
        if form.is_valid():
            form.save()
            messages.success(request, '修改成功')
            return HttpResponseRedirect(request.session['Project_Mail_Edit_from'])
        else:
            messages.error(request, '輸入資訊有誤，請確認輸入資訊')
            return HttpResponseRedirect(request.session['Project_Mail_Edit_from'])


class ProjectMailDeleteView(View):
    model = Project
    context_object_name = 'Project'
    template_name = 'project/Project_Mail_Delete.html'

    @method_decorator(login_required(login_url='login'))
    @method_decorator(permission_required('SE_server.exe_project', (Project, 'ProjectCode', 'pk'), return_403=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, pk, id):
        request.session['Test_Member_Delete_from'] = request.META.get('HTTP_REFERER', '/')
        project = Project.objects.get(pk=pk)
        mail = project.Mail.get(pk=id)
        context = {
            'Mail': mail,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk, id):
        project = Project.objects.get(pk=pk)
        mail = project.Mail.get(pk=id)
        if mail.filepath:
            default_storage.delete(str(mail.filepath))
        mail.delete()
        project.MailCount = project.Mail.all().count()
        project.save()
        return HttpResponseRedirect(request.session['Test_Member_Delete_from'])


class DownloadExample(View):
    def get(self, request, *args, **kwargs):
        request.session['Download_Example'] = request.META.get('HTTP_REFERER', '/')
        type = kwargs.get('type')
        type = type + '.csv'
        path = settings.STATIC_ROOT
        download_path = os.path.join(path, 'upload', type).replace('\\', '/')
        file = open(download_path, 'rb')
        response = FileResponse(file)

        # 使用urlquote對檔名稱進行編碼
        response['Content-Disposition'] = 'attachment;filename="%s"' % type

        return response


class MailSystem(View):
    template_name = 'mail/Mail_System.html'

    def get(self, request, *args, **kwargs):
        request.session['Mail_System'] = request.META.get('HTTP_REFERER', '/')
        pk = kwargs.get('pk')
        project = Project.objects.get(pk=pk)
        context = {
            'Project': project,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        project = Project.objects.get(pk=pk)
        request.session['choose_mail'] = request.POST.getlist("checkMail")
        print(request.session['choose_mail'])
        if not request.session['choose_mail']:
            messages.error(request, '請至少選取一封信件')
            return HttpResponseRedirect(reverse('Mail_System', kwargs={'pk': pk}))
        return HttpResponseRedirect(reverse('Mail_Recipient', kwargs={'pk': pk}))


class DownloadMail(View):
    def get(self, request, *args, **kwargs):
        request.session['Download_Mail'] = request.META.get('HTTP_REFERER', '/')
        pk = kwargs.get('pk')
        mail_id = kwargs.get('id')
        project = Project.objects.get(pk=pk)
        mail_file = project.Mail.get(pk=mail_id)
        media_root = str(settings.MEDIA_ROOT)
        media_root = str(media_root).replace('\\', '/') + '/' + str(mail_file.filepath).replace('\\', '/')
        html = str(mail_file.filepath).split('/')
        template_name = html[-1]
        file = open(media_root, 'rb')
        response = FileResponse(file)
        # 使用urlquote對檔名稱進行編碼
        response['Content-Disposition'] = 'attachment;filename="%s"' % template_name
        sleep(5)
        return response


class MailRecipients(View):
    template_name = 'mail/Mail_Recipients.html'

    def get(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        project = Project.objects.get(pk=pk)
        context = {
            'Project': project
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        project = Project.objects.get(pk=pk)
        request.session['choose_member'] = request.POST.getlist("checkMember")
        print(request.session['choose_member'])
        if not request.session['choose_member']:
            messages.error(request, '請至少選取一位受測人員')
            return HttpResponseRedirect(reverse('Mail_Recipient', kwargs={'pk': pk}))
        return HttpResponseRedirect(reverse('Mail_Check', kwargs={'pk': pk}))


class MailCheck(View):
    template_name = 'mail/Mail_Check.html'

    def get(self, request, *args, **kwargs):
        request.session['Mail_Check'] = request.META.get('HTTP_REFERER', '/')
        pk = kwargs.get('pk')
        project = Project.objects.get(pk=pk)
        mail_list = request.session['choose_mail']
        member_list = request.session['choose_member']
        mail_file_list = project.Mail.filter(pk__in=mail_list)
        send_member_list = project.TestML.filter(pk__in=member_list)
        mail_file_count = mail_file_list.count()
        send_member_count = send_member_list.count()
        context = {
            'Project': project,
            'mail_file': mail_file_count,
            'send_member': send_member_count,
        }
        return render(request, self.template_name, context)


class MailSend(View):
    media_root = str(settings.MEDIA_ROOT)

    def get(self, request, *args, **kwargs):
        request.session['Mail_Send'] = request.META.get('HTTP_REFERER', '/')
        pk = kwargs.get('pk')
        project = Project.objects.get(pk=pk)
        mail_list = request.session['choose_mail']
        member_list = request.session['choose_member']
        mail_file_list = project.Mail.filter(pk__in=mail_list)
        send_member_list = project.TestML.filter(pk__in=member_list)
        taipei_time_zone = pytz.timezone('Asia/Taipei')
        now = datetime.now()
        now_taipei_time_zone = now.astimezone(taipei_time_zone)
        now_taipei_time_zone_str = datetime.strftime(now_taipei_time_zone, '%Y-%m-%d %H:%M:%S')
        try:
            if project.SendRecord:
                send_record = project.SendRecord
            else:
                send_record = []
            send_member_array = []
            send_mail_array = []
            for send_member in send_member_list:
                for mail_file in mail_file_list:
                    base_dir = str(settings.BASE_DIR).replace('\\', '/') + '/SE_server/templates/MailFile'
                    shutil.rmtree(base_dir)
                    os.mkdir(base_dir)
                    media_root = str(self.media_root).replace('\\', '/') + '/' + str(mail_file.filepath).replace('\\',
                                                                                                                 '/')
                    attachment_file = str(self.media_root).replace('\\', '/') + '/' + str(
                        mail_file.AttachmentFile).replace('\\', '/')
                    shutil.copy(media_root, base_dir)
                    html = str(mail_file.filepath).split('/')
                    template_name = 'MailFile/' + html[-1]
                    email_template = render_to_string(
                        template_name,
                        {'uuid': send_member.UUID}
                    )
                    sender = mail_file.Sender + '<' + mail_file.Sender_Mail + '>'
                    email = EmailMultiAlternatives(
                        mail_file.Title,
                        email_template,
                        sender,
                        [send_member.Email]
                    )

                    email.attach_alternative(email_template, 'text/html')
                    if mail_file.HasAtt:
                        email.attach_file(attachment_file)
                    email.fail_silently = True
                    email.send()
                    if send_member.pk not in send_member_array:
                        send_member_array.append(send_member.pk)
                    if mail_file.pk not in send_mail_array:
                        send_mail_array.append(mail_file.pk)
            if project.ProjectName == '第二階段演練':
                for send_member in send_member_list:
                    base_dir = str(settings.BASE_DIR).replace('\\', '/') + '/SE_server/templates/MailFile'
                    shutil.rmtree(base_dir)
                    os.mkdir(base_dir)
                    media_root = str(self.media_root).replace('\\', '/') + '/' + 'MailFile/Normal/facebook.html'
                    shutil.copy(media_root, base_dir)
                    template_name = 'MailFile/facebook.html'
                    email_template = render_to_string(
                        template_name,
                        {'uuid': send_member.UUID}
                    )
                    sender = 'Facebook<noreply@facebook.com>'
                    email = EmailMultiAlternatives(
                        'Facebook通知',
                        email_template,
                        sender,
                        [send_member.Email]
                    )

                    email.attach_alternative(email_template, 'text/html')
                    email.fail_silently = True
                    email.send()

                    base_dir = str(settings.BASE_DIR).replace('\\', '/') + '/SE_server/templates/MailFile'
                    shutil.rmtree(base_dir)
                    os.mkdir(base_dir)
                    media_root = str(self.media_root).replace('\\', '/') + '/' + 'MailFile/Normal/louisacoffee.html'
                    shutil.copy(media_root, base_dir)
                    template_name = 'MailFile/louisacoffee.html'
                    email_template = render_to_string(
                        template_name,
                        {'uuid': send_member.UUID}
                    )
                    sender = '路易莎<noreply@louisacoffee.com>'
                    email = EmailMultiAlternatives(
                        '7-8月黑卡優惠',
                        email_template,
                        sender,
                        [send_member.Email]
                    )

                    email.attach_alternative(email_template, 'text/html')
                    email.fail_silently = True
                    email.send()

                    base_dir = str(settings.BASE_DIR).replace('\\', '/') + '/SE_server/templates/MailFile'
                    shutil.rmtree(base_dir)
                    os.mkdir(base_dir)
                    media_root = str(self.media_root).replace('\\', '/') + '/' + 'MailFile/Normal/famistore.html'
                    shutil.copy(media_root, base_dir)
                    template_name = 'MailFile/famistore.html'
                    email_template = render_to_string(
                        template_name,
                        {'uuid': send_member.UUID}
                    )
                    sender = '到貨通知<noreply@famistore.com>'
                    email = EmailMultiAlternatives(
                        '蝦皮到貨通知',
                        email_template,
                        sender,
                        [send_member.Email]
                    )

                    email.attach_alternative(email_template, 'text/html')
                    email.fail_silently = True
                    email.send()

                    base_dir = str(settings.BASE_DIR).replace('\\', '/') + '/SE_server/templates/MailFile'
                    shutil.rmtree(base_dir)
                    os.mkdir(base_dir)
                    media_root = str(self.media_root).replace('\\', '/') + '/' + 'MailFile/Normal/pchome.html'
                    shutil.copy(media_root, base_dir)
                    template_name = 'MailFile/pchome.html'
                    email_template = render_to_string(
                        template_name,
                        {'uuid': send_member.UUID}
                    )
                    sender = 'pchome<noreply@pchome.com.tw>'
                    email = EmailMultiAlternatives(
                        'PChome線上購物-發票開立通知',
                        email_template,
                        sender,
                        [send_member.Email]
                    )

                    email.attach_alternative(email_template, 'text/html')
                    email.fail_silently = True
                    email.send()

                    base_dir = str(settings.BASE_DIR).replace('\\', '/') + '/SE_server/templates/MailFile'
                    shutil.rmtree(base_dir)
                    os.mkdir(base_dir)
                    media_root = str(self.media_root).replace('\\', '/') + '/' + 'MailFile/Normal/technews.html'
                    shutil.copy(media_root, base_dir)
                    template_name = 'MailFile/technews.html'
                    email_template = render_to_string(
                        template_name,
                        {'uuid': send_member.UUID}
                    )
                    sender = '科技新聞<noreply@technews.com.tw>'
                    email = EmailMultiAlternatives(
                        '你的電話號碼在網上？Google 現在接受移除要求',
                        email_template,
                        sender,
                        [send_member.Email]
                    )

                    email.attach_alternative(email_template, 'text/html')
                    email.fail_silently = True
                    email.send()
            send_record.append(
                {"send": {"send_date_time": str(now_taipei_time_zone_str), "send_user": request.user.username,
                          "send_member": send_member_array, "send_mail": send_mail_array}})
            project.SendRecord = send_record
            project.save()
            messages.success(request, '發送成功')
            del request.session['choose_mail']
            del request.session['choose_member']

            return HttpResponseRedirect(reverse('mail_record', kwargs={'pk': pk}))
        except Exception as e:
            messages.error(self.request, e)
            del request.session['choose_mail']
            del request.session['choose_member']
            return HttpResponseRedirect(reverse('mail_record', kwargs={'pk': pk}))


class MailView(View):
    media_root = str(settings.MEDIA_ROOT)

    def get(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        file_id = kwargs.get('id')
        project = Project.objects.get(pk=pk)
        file = project.Mail.get(pk=file_id)
        base_dir = str(settings.BASE_DIR).replace('\\', '/') + '/SE_server/templates/MailFile'
        shutil.rmtree(base_dir)
        os.mkdir(base_dir)
        media_root = str(self.media_root).replace('\\', '/') + '/' + str(file.filepath).replace('\\', '/')
        shutil.copy(media_root, base_dir)
        html = str(file.filepath).split('/')
        template_name = 'MailFile/' + html[-1]
        context = {
            'uuid': 'aaasec',
        }
        return render(request, template_name, context)


class MailUpload(View):
    template_name = 'mail/Mail_Upload.html'
    form_class = HTMLUploadForm

    def get(self, request, *args, **kwargs):
        request.session['Mail_File_Upload'] = request.META.get('HTTP_REFERER', '/')
        pk = kwargs.get('pk')
        project = Project.objects.get(pk=pk)
        context = {
            'Project': project,
            'Form': self.form_class,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        project = Project.objects.get(pk=pk)
        mail_id = kwargs.get('id')
        uploaded_file = request.FILES["uploaded_file"]
        file_path = 'MailFile/' + project.ProjectCode + '/' + str(uploaded_file)
        if not uploaded_file.name.endswith('html'):
            messages.error(request, '檔案類型錯誤,請確認檔案為html')
            return HttpResponseRedirect(request.session['Mail_File_Upload'])
        if default_storage.exists(file_path):
            messages.error(request, '檔案重複，請重新上傳')
        else:
            mail = project.Mail.get(pk=mail_id)
            mail.filepath = uploaded_file
            mail.save()
            messages.success(request, '上傳成功')
        return HttpResponseRedirect(request.session['Mail_File_Upload'])


class AttachUpload(View):
    template_name = 'mail/Attachment_Upload.html'
    form_class = HTMLUploadForm

    def get(self, request, *args, **kwargs):
        request.session['Attachment_Upload'] = request.META.get('HTTP_REFERER', '/')
        pk = kwargs.get('pk')
        project = Project.objects.get(pk=pk)
        context = {
            'Project': project,
            'Form': self.form_class,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        project = Project.objects.get(pk=pk)
        mail_id = kwargs.get('id')
        uploaded_file = request.FILES["uploaded_file"]
        file_path = 'MailFile/' + project.ProjectCode + '/' + str(uploaded_file)
        if default_storage.exists(file_path):
            messages.error(request, '檔案重複，請重新上傳')
        else:
            mail = project.Mail.get(pk=mail_id)
            mail.AttachmentFile = uploaded_file
            mail.save()
            messages.success(request, '上傳成功')
        return HttpResponseRedirect(request.session['Attachment_Upload'])


class SendRecord(View):
    template_name = 'mail/Send_Record.html'

    def get(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        project = Project.objects.get(pk=pk)
        context = {
            'Project': project
        }
        return render(request, self.template_name, context)


def unit_people_click_bar(data, unit):
    graph = {
        'unit': [],
        'click_count_rate': [],
        'click_count': []
    }
    for unit_code in unit:
        if data[unit_code]['people_click_count_rate'] != 0:
            graph['unit'].append(unit_code)
            graph['click_count_rate'].append(data[unit_code]['people_click_count_rate'])
            graph['click_count'].append(data[unit_code]['click_count'])
    people_click_graph = graph
    return people_click_graph


# def unit_people_open_bar(data, unit):
#     graph = {
#         'unit': [],
#         'open_count_rate': [],
#         'open_count': [],
#     }
#     for unit_code in unit:
#         if data[unit_code]['people_open_count_rate'] != 0:
#             graph['unit'].append(unit_code)
#             graph['open_count_rate'].append(data[unit_code]['people_open_count_rate'])
#             graph['open_count'].append(data[unit_code]['open_count'])
#     df = pd.DataFrame(graph, columns=['unit', 'open_count_rate', 'open_count'])
#     df = df.sort_values(by='open_count_rate', ascending=False)
#     people_open_graph = df.to_dict('list')
#     return people_open_graph


class ProjectResultView(View):
    template_name = 'project/Project_Result.html'

    @method_decorator(login_required(login_url='login'))
    @method_decorator(permission_required('SE_server.view_project', (Project, 'ProjectCode', 'pk'), return_403=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, pk):
        request.session['Project_Result'] = request.META.get('HTTP_REFERER', '/')
        project = Project.objects.get(ProjectCode=pk)
        mail = []
        unit = project.UnitList
        get_list = [self.request.GET]
        mail_list = project.Mail.all()
        for mailc in mail_list:
            mail.append(mailc.MailTag)
        if get_list[0].getlist('Unit'):
            search_unit = get_list[0].getlist('Unit')
        else:
            search_unit = unit
        if get_list[0].getlist('Mail'):
            search_mail = get_list[0].getlist('Mail')
        else:
            search_mail = mail
        if project.MailCount == 0 or project.PersonCount == 0:
            # messages.error(request, '無統計結果')
            return HttpResponseRedirect(request.session['Project_Result'])
        try:
            for member in project.TestML.all():
                member.Result['Total']['open'] = 0
                member.Result['Total']['click'] = 0
                member.Result['Total']['attachment'] = 0
                for mail_number in search_mail:
                    for i in range(project.MailCount):
                        if member.Result['Mail%d' % (i + 1)]['name'] == mail_number:
                            member.Result['Total']['open'] += member.Result['Mail%d' % (i + 1)]['open']
                            member.Result['Total']['click'] += member.Result['Mail%d' % (i + 1)]['click']
                            member.Result['Total']['attachment'] += member.Result['Mail%d' % (i + 1)]['attachment']
                member.save()
        except:
            # messages.error(request, '無統計結果')
            print(1)
            # return HttpResponseRedirect(request.session['Project_Result'])
        second_phase = False
        if project.ProjectName == '第二階段演練':
            second_phase = True
        context = {
            'Project': project,
            'Mail': mail,
            'Unit': unit,
            'Search_Unit': search_unit,
            'Search_Mail': search_mail,
            'second_phase': second_phase,
        }
        return render(request, self.template_name, context)


class ProjectOpenRecordView(View):
    template_name = 'project/Project_Result_Open_Record.html'

    @method_decorator(login_required(login_url='login'))
    @method_decorator(permission_required('SE_server.view_project', (Project, 'ProjectCode', 'pk'), return_403=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, pk):
        project = Project.objects.get(pk=pk)
        open_record = project.OpenRecord
        context = {
            'Open_Record': open_record
        }
        return render(request, self.template_name, context)


class ProjectClickRecordView(View):
    template_name = 'project/Project_Result_Click_Record.html'

    @method_decorator(login_required(login_url='login'))
    @method_decorator(permission_required('SE_server.view_project', (Project, 'ProjectCode', 'pk'), return_403=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, pk):
        project = Project.objects.get(pk=pk)
        click_record = project.ClickRecord
        context = {
            'Click_Record': click_record
        }
        return render(request, self.template_name, context)


class ProjectAttachmentRecordView(View):
    template_name = 'project/Project_Result_Attachment_Record.html'

    @method_decorator(login_required(login_url='login'))
    @method_decorator(permission_required('socialapp.view_project', (Project, 'ProjectCode', 'pk'), return_403=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, pk):
        project = Project.objects.get(pk=pk)
        attachment_record = project.AttachmentRecord
        context = {
            'Attachment_Record': attachment_record
        }
        return render(request, self.template_name, context)


# class ProjectResultGraphView(View):
#     template_name = 'project/Project_Result_Graph.html'
#
#     @method_decorator(login_required(login_url='login'))
#     @method_decorator(permission_required('SE_server.view_project', (Project, 'ProjectCode', 'pk'), return_403=True))
#     def dispatch(self, *args, **kwargs):
#         return super().dispatch(*args, **kwargs)
#
#     def get(self, request, pk):
#         project = Project.objects.get(pk=pk)
#         unit = project.UnitList
#         unit_people_count = '{'
#         mail = []
#         for i in range(project.MailCount):
#             mail.append('Mail%d' % (i + 1))
#         member_list = project.TestML.all()
#
#         for i in range(len(unit)):
#             if i == 0:
#                 unit_people_count = unit_people_count + '"%s":{"people_count":0,"mail_count":0,"open_count":0,' \
#                                                         '"open_rate":0,"click_count":0,"click_rate":0,' \
#                                                         '"people_click_count":0,"people_open_count":0,' \
#                                                         '"people_click_count_rate":0,"people_open_count_rate":0}' % (
#                                         unit[i])
#             else:
#                 unit_people_count = unit_people_count + ',"%s":{"people_count":0,"mail_count":0,"open_count":0,' \
#                                                         '"open_rate":0,"click_count":0,"click_rate":0,' \
#                                                         '"people_click_count":0,"people_open_count":0,' \
#                                                         '"people_click_count_rate":0,"people_open_count_rate":0}' % (
#                                         unit[i])
#         unit_people_count = unit_people_count + '}'
#         data = json.loads(unit_people_count)
#         for member in member_list:
#             people_open_count = False
#             people_click_count = False
#             for mail_count in mail:
#                 if member.Result[mail_count]['open']:
#                     people_open_count = True
#                 if member.Result[mail_count]['click']:
#                     people_click_count = True
#             if people_click_count:
#                 data[member.UnitName]['people_click_count'] += 1
#             if people_open_count:
#                 data[member.UnitName]['people_open_count'] += 1
#         for unit_code in unit:
#             for member in project.TestML.filter(UnitName__contains=unit_code):
#                 for mail_count in mail:
#                     data[member.UnitName]['open_count'] += member.Result[mail_count]['open']
#                     data[member.UnitName]['click_count'] += member.Result[mail_count]['click']
#             data[unit_code]['people_count'] = len(project.TestML.filter(UnitName__contains=unit_code))
#             data[unit_code]['mail_count'] = len(project.TestML.filter(UnitName__contains=unit_code)) * len(mail)
#             data[unit_code]['open_rate'] = data[unit_code]['open_count'] / (
#                     len(mail) * data[unit_code]['people_count']) * 100
#             data[unit_code]['click_rate'] = data[unit_code]['click_count'] / (
#                     len(mail) * data[unit_code]['people_count']) * 100
#             data[unit_code]['people_click_count_rate'] = data[unit_code]['people_click_count'] / project.MailCount * data[unit_code][
#                 'people_count'] * 100
#             data[unit_code]['people_open_count_rate'] = data[unit_code]['people_open_count'] / project.MailCount * data[unit_code][
#                 'people_count'] * 100
#         # open_bar = unit_open_bar(data, unit)
#         # click_bar = unit_click_bar(data, unit)
#         people_click_bar = unit_people_click_bar(data, unit)
#         people_open_bar = unit_people_open_bar(data, unit)
#         context = {
#             'Unit_People_Count': data,
#             # 'open_bar': open_bar,
#             # 'click_bar': click_bar,
#             'people_click_bar': people_click_bar,
#             'people_open_bar': people_open_bar,
#         }
#         return render(request, self.template_name, context)
#

class CompamyView(View):
    template_name = 'user/User_Company.html'
    form_class = CompanySearch

    @method_decorator(login_required(login_url='login'))
    @method_decorator(permission_required('SE_server.add_company', return_403=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request):
        company = Company.objects.exclude(CompanyCode='AAA')
        context = {
            'current_time': str(datetime.now()),
            'Form': self.form_class,
            'Company': company
        }
        return render(request, self.template_name, context)


class CompanyCreateView(View):
    template_name = 'user/User_Company_Create.html'
    form_class = CompanyForm

    @method_decorator(login_required(login_url='login'))
    @method_decorator(permission_required('SE_server.add_company', return_403=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request):
        request.session['Company_Create'] = request.META.get('HTTP_REFERER', '/')
        return render(request, self.template_name, {'form': self.form_class})

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            company_code = request.POST.get('CompanyCode')
            company_name = request.POST.get('CompanyName')
            Group.objects.create(name=company_code)
            group = Group.objects.get(name=company_code)
            company = Company.objects.create(GroupCode=group, CompanyCode=company_code, CompanyName=company_name)
            execute = '%s_執行人' % company.CompanyName
            G_execute = Group.objects.create(name=execute)
            admin = Group.objects.get(name='系統管理員')
            project_M = Group.objects.get(name='專案經理')
            AA = Group.objects.get(name='AAA')
            per = Permission.objects.get(codename='view_company')
            group.permissions.add(per)
            G_execute.permissions.add(per)
            project_M.permissions.add(per)
            admin.permissions.add(per)
            assign_perm('exe_company', G_execute, company)
            assign_perm('view_company', G_execute, company)

            assign_perm('view_company', group, company)
            assign_perm('view_company', project_M, company)

            assign_perm('exe_company', admin, company)
            assign_perm('view_company', admin, company)
            assign_perm('add_company', admin, company)
            assign_perm('change_company', admin, company)
            assign_perm('delete_company', admin, company)
            messages.success(request, '建立成功')

            # 自動新增演練階段
            project_name = '第一階段演練'
            start_time = datetime.now().replace(hour=0, minute=0, second=0)
            end_time = start_time + dt.timedelta(days=7)

            year = datetime.now()
            project_code1 = company.CompanyCode + str(year)[0:4] + 'P01'
            project1 = Project.objects.create(CompanyCode=company, ProjectCode=project_code1, ProjectName=project_name,
                                                  CalculateStartDate=start_time, CalculateEndDate=end_time )
            project_name = '第二階段演練'
            project_code2 = company.CompanyCode + str(year)[0:4] + 'P02'
            project2 = Project.objects.create(CompanyCode=company, ProjectCode=project_code2, ProjectName=project_name,
                                              CalculateStartDate=start_time, CalculateEndDate=end_time)
            group = project1.CompanyCode.GroupCode
            ex = '%s_執行人' % project1.CompanyCode.CompanyName
            technology = Group.objects.get(name=ex)
            project_M = Group.objects.get(name='專案經理')
            admin = Group.objects.get(name='系統管理員')
            assign_perm('view_project', project_M, project1)
            assign_perm('view_project', project_M, project2)

            assign_perm('view_project', technology, project1)
            assign_perm('view_project', technology, project2)
            assign_perm('exe_project', technology, project1)
            assign_perm('exe_project', technology, project2)

            assign_perm('view_project', admin, project1)
            assign_perm('view_project', admin, project2)
            assign_perm('change_project', admin, project1)
            assign_perm('change_project', admin, project2)
            assign_perm('add_project', admin, project1)
            assign_perm('add_project', admin, project2)
            assign_perm('delete_project', admin, project1)
            assign_perm('delete_project', admin, project2)
            assign_perm('exe_project', admin, project1)
            assign_perm('exe_project', admin, project2)

            assign_perm('view_project', group, project1)
            assign_perm('view_project', group, project2)
            assign_perm('exe_project', group, project1)
            assign_perm('exe_project', group, project2)

            # 自動新增學生
            for i in range(1, 21):
                unit_code = 'A' + '%02d' % i
                unit_name = '第' + str(i) + '組'
                member_sumber = 'G' + '%02d' % i
                mail = 'std' + '%02d' % i + '@iecslab.fcu'
                srcHash1 = project_code1[0:2] + unit_code + member_sumber
                m2 = hashlib.md5()
                m2.update(srcHash1.encode(encoding='utf-8'))
                key1 = srcHash1 + (m2.hexdigest()[0:3]).upper()
                srcHash2 = project_code2[0:2] + unit_code + member_sumber
                m2.update(srcHash2.encode(encoding='utf-8'))
                key2 = srcHash2 + (m2.hexdigest()[0:3]).upper()
                TestMemberList.objects.create(ProjectCode=project1, Unit=unit_code, UnitName=unit_name, MemberNumber=member_sumber,
                                              UUID=key1, Email=mail)
                TestMemberList.objects.create(ProjectCode=project2, Unit=unit_code, UnitName=unit_name,
                                              MemberNumber=member_sumber,
                                              UUID=key2, Email=mail)

            #自動新增信件
            mail_1_1 = MailList.objects.create(ProjectCode=project1, MailNumber="Mail1", Title="蝦皮精選特賣商品", Sender="蝦皮購物",
                                               Sender_Mail="shopee@shoppee.com", HasAtt=True, Address="/shopee/", Open="logo.PNG",
                                               Click="index.html", Attachment="att1-1.html", MailTag="第一封",
                                               filepath="MailFile/Sample/shopee.html", AttachmentFile="MailFile/Sample/shopee.zip")
            mail_1_2 = MailList.objects.create(ProjectCode=project1, MailNumber="Mail2", Title="8大通路開賣快篩地點",
                                               Sender="聯合新聞網",
                                               Sender_Mail="udn@udn.org", HasAtt=True, Address="/udn/",
                                               Open="title.jpg",
                                               Click="6298358.html", Attachment="att1-2.html", MailTag="第二封",
                                               filepath="MailFile/Sample/udn.html",
                                               AttachmentFile="MailFile/Sample/8place.zip")
            mail_1_3 = MailList.objects.create(ProjectCode=project1, MailNumber="Mail3", Title="啦啦隊女神3分鐘超兇上下抖片爆紅",
                                               Sender="娛樂星聞",
                                               Sender_Mail="star@sten.com", HasAtt=False, Address="/star/",
                                               Open="3650662-PH.jpg",
                                               Click="link.html", Attachment="att3.html", MailTag="第三封",
                                               filepath="MailFile/Sample/star.html",
                                               AttachmentFile="MailFile/Sample/att3.html")
            mail_2_1 = MailList.objects.create(ProjectCode=project2, MailNumber="Mail1", Title="小茶栽堂2022中秋限定禮盒",
                                               Sender="小茶栽堂",
                                               Sender_Mail="zenique@zenique.com", HasAtt=True, Address="/zenique/",
                                               Open="title.jpeg",
                                               Click="event.html", Attachment="att2-1.html", MailTag="第一封",
                                               filepath="MailFile/Sample/zenique.html",
                                               AttachmentFile="MailFile/Sample/2022event.zip")
            mail_2_2 = MailList.objects.create(ProjectCode=project2, MailNumber="Mail2", Title="Security Alert",
                                               Sender="hacker",
                                               Sender_Mail="bitcoin@bitcoin.org", HasAtt=False, Address="/bitcoin/",
                                               Open="file6593.PNG",
                                               Click="alert.html", Attachment="att2-2.html", MailTag="第二封",
                                               filepath="MailFile/Sample/bitcoin.html",
                                               AttachmentFile="MailFile/Sample/att2.html")
            mail_2_3 = MailList.objects.create(ProjectCode=project2, MailNumber="Mail3", Title="Netflix資訊更新通知",
                                               Sender="Netflix",
                                               Sender_Mail="noreply@netflix.com", HasAtt=True, Address="/netflix/",
                                               Open="netflix.png",
                                               Click="help_center.html", Attachment="att2-3.html", MailTag="第三封",
                                               filepath="MailFile/Sample/netflix.html",
                                               AttachmentFile="MailFile/Sample/NetflixUpdate.zip")
            #自動新增學生帳號
            std_company_code = company_code + "_std"
            std_group = Group.objects.create(name=std_company_code)
            for i in range(1, 21):
                username = company_code + 'std' + '%02d' % i + '@iecslab.com.tw'
                ur = User.objects.create_user(username=username, password=username, email=username)
                ur.groups.add(std_group)
                group_name = '第' + '%02d' % i + '組'
                Score.objects.create(company=company, group_code=std_company_code, group_name=group_name)
            return HttpResponseRedirect(request.session['Company_Create'])


class CompanyDeleteView(View):
    template_name = 'user/User_Company_Delete.html'

    @method_decorator(login_required(login_url='login'))
    @method_decorator(permission_required('SE_server.delete_company', return_403=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        request.session['Company_Delete'] = request.META.get('HTTP_REFERER', '/')
        pk = kwargs.get('pk')
        company = Company.objects.get(pk=pk)
        context = {
            'Company': company
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        company = Company.objects.get(pk=pk)
        if pk in 'AA':
            messages.warning(request, '無法刪除管理員')
            return HttpResponseRedirect(request.session['Company_Delete'])
        group = Group.objects.get(name=company.CompanyCode)
        std_group_name = company.CompanyCode + '_std'
        std_group = Group.objects.get(name=std_group_name)
        execute = '%s_執行人' % company.CompanyName
        G_execute = Group.objects.get(name=execute)
        user_list = group.user_set.all()
        for user in user_list:
            user.delete()
        std_user_list = std_group.user_set.all()
        for user in std_user_list:
            user.delete()
        group.delete()
        std_group.delete()
        G_execute.delete()
        return HttpResponseRedirect(request.session['Company_Delete'])


class CompanyUserView(View):
    template_name = 'user/User.html'

    @method_decorator(login_required(login_url='login'))
    @method_decorator(permission_required('SE_server.change_company', return_403=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, pk):
        company = Company.objects.get(pk=pk)
        group = Group.objects.get(name=company.CompanyCode)
        user = group.user_set.all()
        context = {
            'Company': company,
            'Company_User': user,
        }
        return render(request, self.template_name, context)


class Token:
    def __init__(self, security_key):
        self.security_key = security_key
        self.salt = security_key.encode()

    def generate_validate_token(self, username):
        serializer = utsr(self.security_key)

        return serializer.dumps(username, self.salt)

    def confirm_validate_token(self, token, expiration=60 * 60):
        serializer = utsr(self.security_key)
        return serializer.loads(token, salt=self.salt, max_age=expiration)

    def remove_validate_token(self, token):
        serializer = utsr(self.security_key)
        return serializer.loads(token, salt=self.salt)


class UserCreateView(View):
    template_name = 'user/User_Create.html'
    form_class = RegisterForm
    token_confirm = Token('secret-key')

    @method_decorator(login_required(login_url='login'))
    @method_decorator(permission_required('SE_server.change_company', return_403=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        request.session['User_Create'] = request.META.get('HTTP_REFERER', '/')
        company = Company.objects.get(pk=pk)
        context = {
            'company': company,
            'form': self.form_class
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        company_code = self.request.POST.get('CompanyCode')
        username = self.request.POST.get('email')
        email = self.request.POST.get('email')
        group = Group.objects.get(name=company_code)
        try:
            usr_name = User.objects.filter(username=username)
            if usr_name.exists():
                messages.error(self.request, '該信箱已註冊過')
                return HttpResponseRedirect(request.session['User_Create'])
            pwd = ''.join(random.sample(string.ascii_letters, 12))
            ur = User.objects.create_user(username=username, password=pwd, email=email)
            admin = Group.objects.get(name='系統管理員')
            assign_perm('change_user', ur, ur)
            assign_perm('change_user', admin, ur)
            ur.groups.add(group)
            ur.save()

            # 創建Token，並寄給使用者
            # token = self.token_confirm.generate_validate_token(username)
            #
            # message = "\n".join([
            #     u'{0},'.format(username),
            #     u'請訪問該連結，完成使用者驗證:',
            #     '/'.join(
            #         ['http://{0}'.format(settings.SERVER_IP), 'user/activate', token])
            # ])
            # email = EmailMessage(
            #     '註冊成功通知信',
            #     message,
            #     settings.EMAIL_HOST_USER,
            #     [email]
            # )
            # email.send()
            messages.success(self.request, '創建成功，密碼為'+pwd)
            return HttpResponseRedirect(request.session['User_Create'])

        except Exception as e:
            messages.error(self.request, e)
            return HttpResponseRedirect(request.session['User_Create'])


class EmailValidators:
    def active_user(request, token):
        token_confirm = Token('secret-key')
        try:
            username = token_confirm.confirm_validate_token(token)
            user = User.objects.filter(username=username).get()
        except:
            messages_res = '連結已失效，請聯絡三甲科技！'
            messages.warning(request, messages_res)
            return HttpResponseRedirect(reverse('login'))
        if user.is_active:
            messages_res = '帳號已啟用，請透過帳號密碼進行登入。'
            messages.warning(request, messages_res)
            return HttpResponseRedirect(reverse('login'))
        else:
            try:
                user.is_active = True
                user.save()
                logout(request)
                username = token_confirm.remove_validate_token(token)
                return render(request, 'user/Password_Reset.html', {'pk': user.pk})
            except Exception as e:
                username = token_confirm.remove_validate_token(token)
                messages_res = '連結已失效，請聯絡三甲科技！'
                messages.warning(request, messages_res)
                return HttpResponseRedirect(reverse('login'))

    def user_forgotpsw(request, token):
        token_confirm = Token('secret-key')
        try:
            email = token_confirm.confirm_validate_token(token)
            user = User.objects.filter(email=email).get()
        except:
            messages_res = '連結已失效，請聯絡三甲科技！'
            messages.warning(request, messages_res)
            return HttpResponseRedirect(reverse('login'))
        if user.is_active:
            logout(request)
            username = token_confirm.remove_validate_token(token)
            return render(request, 'user/Password_Reset.html', {'pk': user.pk})
        else:
            username = token_confirm.remove_validate_token(token)
            messages_res = '連結已失效，請聯絡三甲科技！'
            messages.warning(request, messages_res)
            return HttpResponseRedirect(reverse('login'))


class PasswordResetView(View):
    template_name = 'user/Password_Reset.html'
    user_self = False

    @method_decorator(login_required(login_url='login'))
    def get(self, request):
        user = auth.get_user(request)
        self.user_self = True
        print(request.user.is_authenticated, self.user_self)
        return render(request, self.template_name, {'pk': user.pk, 'user_self': self.user_self})

    def post(self, request):
        pk = request.POST.get('pk')
        password = request.POST.get('password')
        password_check = request.POST.get('check_password')
        user = User.objects.get(id=pk)
        try:
            password_validation.validate_password(password, user)
        except ValidationError as e:
            e = ','.join(e)
            messages.error(request, e)
            return render(request, self.template_name, {'pk': pk, 'user_self': self.user_self})
        if password in password_check:
            user.set_password(password)
            user.save()
            messages.success(request, '變更成功，請用新密碼登入')
            return HttpResponseRedirect(reverse('project'))
        else:
            messages.error(request, '兩次密碼不一樣')
            return render(request, self.template_name, {'pk': pk, 'user_self': self.user_self})


class UserEditView(View):
    template_name = 'user/User_Edit.html'

    @method_decorator(login_required(login_url='login'))
    @method_decorator(permission_required('auth.change_user', (User, 'id', 'id'), return_403=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        request.session['User_Edit'] = request.META.get('HTTP_REFERER', '/')
        edit_permission = False
        company_pk = kwargs.get('pk')
        pk = kwargs.get('id')
        url = kwargs.get('url')
        r_user = request.user
        if r_user.groups.filter(name='系統管理員').exists():
            edit_permission = True
        company = Company.objects.get(pk=company_pk)
        company_list = Company.objects.all()
        user = User.objects.get(pk=pk)
        context = {
            'Company_List': company_list,
            'Company': company,
            'User': user,
            'last_url': request.session['User_Edit'],
            'Edit': edit_permission,
            'url': url,
        }
        group_list = []
        if user.groups.filter(name='AA').exists():
            company_list = Company.objects.exclude(CompanyCode='AA')
            per_list = ['系統管理員', '專案經理']
            ex_list = Group.objects.filter(name__contains='執行人')
            for ex in ex_list:
                per_list.append(ex.name)
            print(per_list)
            context['Permission_list'] = per_list
            user_group = user.groups.all()
            for group in user_group:
                group_list.append(group.name)
            print(group_list)
            context['Company_list'] = company_list
            context['Permission'] = group_list
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        company_pk = kwargs.get('pk')
        pk = kwargs.get('id')
        url = kwargs.get('url')
        company = Company.objects.get(pk=company_pk)
        user = User.objects.get(pk=pk)
        edit_permission = False
        r_user = request.user
        if r_user.groups.filter(name='Admin').exists():
            edit_permission = True
        context = {
            'Company': company,
            'User': user,
            'last_url': request.session['User_Edit'],
            'Edit': edit_permission,
            'url': url,
        }
        username = request.POST.get('username')
        email = request.POST.get('email')
        permission = request.POST.getlist('permission')
        per_list = ['系統管理員', '專案經理']
        ex_list = Group.objects.filter(name__contains='執行人')
        for ex in ex_list:
            per_list.append(ex.name)
        print(per_list)
        context['Permission_list'] = per_list
        if url == 'company':
            for group_name in per_list:
                if group_name in permission:
                    if not user.groups.filter(name=group_name).exists():
                        group = Group.objects.get(name=group_name)
                        user.groups.add(group)
                else:
                    if user.groups.filter(name=group_name).exists():
                        group = Group.objects.get(name=group_name)
                        user.groups.remove(group)
        group_list = []
        if user.groups.filter(name='AA').exists():
            company_list = Company.objects.exclude(CompanyCode='AA')
            user_group = user.groups.all()
            for group in user_group:
                group_list.append(group.name)
            context['Company_list'] = company_list
            context['Permission'] = group_list
        if username is not None and username != user.username:
            if User.objects.filter(username__contains=username).exists():
                messages.error(request, '使用者名稱已存在')
                return render(request, self.template_name, context)
            else:
                user.username = username
                user.save()
        if email is not None and email != user.email:
            if User.objects.filter(email=email).exists():
                messages.error(request, '電子郵件已存在')
                return render(request, self.template_name, context)
            else:
                user.email = email
                user.save()
        old_password = request.POST.get('old_password')
        if old_password:
            if not user.check_password(old_password):
                messages.error(request, '密碼輸入錯誤')
                return render(request, self.template_name, context)
            new_password = request.POST.get('new_password')
            password_check = request.POST.get('check_password')
            try:
                password_validation.validate_password(new_password, user)
            except ValidationError as e:
                e = ','.join(e)
                messages.error(request, e)
                return render(request, self.template_name, context)
            if new_password in password_check:
                user.set_password(new_password)
                user.save()
                messages.success(request, '變更成功，請用新密碼登入')
                return HttpResponseRedirect(reverse('project'))
            else:
                messages.error(request, '兩次密碼不一樣')
                return render(request, self.template_name, context)
        return HttpResponseRedirect(request.session['User_Edit'])


class UserDeleteView(View):
    template_name = 'user/User_Delete.html'

    @method_decorator(login_required(login_url='login'))
    @method_decorator(permission_required('SE_server.add_company', return_403=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        pk = kwargs.get('id')
        request.session['User_Delete'] = request.META.get('HTTP_REFERER', '/')
        user = User.objects.get(pk=pk)
        context = {
            'User': user,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        pk = kwargs.get('id')
        user = User.objects.get(pk=pk)
        user.delete()
        return HttpResponseRedirect(request.session['User_Delete'])

@login_required
def report_back(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        user = request.user
        std_group = str(user.groups.all()[0])
        group = Group.objects.get(name=std_group.replace('_std', '', 1))
        company = group.Company.all()[0]
        project = Project.objects.get(ProjectName='第二階段演練', CompanyCode=company)
        mail_1 = project.Mail.get(MailNumber='Mail1').Title
        mail_2 = project.Mail.get(MailNumber='Mail2').Title
        mail_3 = project.Mail.get(MailNumber='Mail3').Title
        std_group_name = '第' + request.user.username.split('@')[0].split('std')[1] + '組'
        target_score = Score.objects.get(company=company, group_code=str(std_group), group_name=std_group_name)
        if target_score is not None:
            if ReportBackRecord.objects.filter(company=company, group_code=str(std_group), group_name=std_group_name).count()>2:
                return redirect('report_back_fail')
            if title == mail_1 and target_score.mail1 is None:
                ReportBackRecord.objects.create(company=company, group_code=str(std_group), group_name=std_group_name,
                                                content=title, check_result=True)
                answer_count = len(Score.objects.filter(company=company).exclude(mail1=None))
                target_score.mail1 = 100 - answer_count*5
                if target_score.mail1 < 60:
                    target_score.mail1 = 60
                target_score.save()
            elif title == mail_2 and target_score.mail2 is None:
                ReportBackRecord.objects.create(company=company, group_code=str(std_group), group_name=std_group_name,
                                                content=title, check_result=True)
                answer_count = len(Score.objects.filter(company=company).exclude(mail2=None))
                target_score.mail2 = 100 - answer_count * 5
                if target_score.mail2 < 60:
                    target_score.mail2 = 60
                target_score.save()
            elif title == mail_3 and target_score.mail3 is None:
                ReportBackRecord.objects.create(company=company, group_code=str(std_group), group_name=std_group_name,
                                                content=title, check_result=True)
                answer_count = len(Score.objects.filter(company=company).exclude(mail3=None))
                target_score.mail3 = 100 - answer_count * 5
                if target_score.mail3 < 60:
                    target_score.mail3 = 60
                target_score.save()
            else:
                ReportBackRecord.objects.create(company=company, group_code=str(std_group), group_name=std_group_name,
                                                content=title, check_result=False)
        return redirect('report_back_success')
    else:
        print('AAAA')
        return render(request, 'project/Report_Back.html')


def report_back_success(request):
    return render(request, 'project/Report_Back_Success.html')


def report_back_fail(request):
    return render(request, 'project/Report_Back_Fail.html')


class ProjectAllScoreView(View):
    template_name = 'project/All_Scroe.html'

    @method_decorator(login_required(login_url='login'))
    @method_decorator(permission_required('SE_server.view_project', (Project, 'ProjectCode', 'pk'), return_403=True))
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, pk):
        project = Project.objects.get(pk=pk)
        company = project.CompanyCode
        all_group_score = Score.objects.filter(company=company).order_by('group_name')
        context = {
            'all_group_score': all_group_score
        }
        return render(request, self.template_name, context)


def all_score(request):
    all_group_score = Score.objects.all().order_by('group')
    return render(request, 'project/All_Scroe.html', {'all_group_score': all_group_score})



class LoginView(auth_views.LoginView):
    template_name = 'user/Login.html'
    form_class = LoginForm

    def get(self, request):
        logout(request)
        form = self.form_class()
        request.session['login_from'] = request.META.get('HTTP_REFERER', '/')
        # return render(request, self.template_name,
        #               context={'form': form, 'recaptcha_site_key': settings.RECAPTCHA_SITE_KEY})
        return render(request, self.template_name, context={'form': form,})

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            # secret_key = settings.RECAPTCHA_PRIVATE_KEY
            # recaptcha_response = request.POST.get('g-recaptcha-response')
            # data = {
            #     'response': recaptcha_response,
            #     'secret': secret_key
            # }
            # resp = requests.post('https://www.google.com/recaptcha/api/siteverify', data=data)
            # result_json = resp.json()
            #
            # if result_json.get('success') and result_json.get('score') > 0.5:
            #
            #     user = authenticate(
            #         username=form.cleaned_data['email'],
            #         password=form.cleaned_data['password'],
            #     )
            #     if user is not None:
            #         login(request, user)
            #         return redirect(reverse('project'))
            # else:
            #     messages.error(request, '驗證逾時，請再試一次')
            #     return render(request, self.template_name, context={'form': form,
            #                                                         'recaptcha_site_key': settings.RECAPTCHA_SITE_KEY})
            user = authenticate(
                username=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                )
            print(form.cleaned_data['email'], form.cleaned_data['password'],user)
            if user is not None:
                login(request, user)
                next_to = request.GET.get('next')
                print(next_to)
                if next_to == '/report_back':
                    return redirect('report_back')
                else:
                    return redirect(reverse('project'))
        messages.error(request, '帳號或密碼輸入錯誤，請再試一次')
        # return render(request, self.template_name,
        #               context={'form': form, 'recaptcha_site_key': settings.RECAPTCHA_SITE_KEY})
        return render(request, self.template_name, context={'form': form, })


class ForgotPasswordView(View):
    template_name = 'user/Forgot_Password.html'
    form_class = RegisterForm

    def get(self, request, *args, **kwargs):
        request.session['Forgot_Password'] = request.META.get('HTTP_REFERER', '/')
        context = {
            'form': self.form_class,
            'last_url': request.session['Forgot_Password'],
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        email = self.request.POST.get('email')
        token_confirm = Token('secret-key')
        try:
            try:
                usr_email = User.objects.get(email=email)
            except:
                messages.error(self.request, '該電子郵件未註冊，請聯絡三甲科技')
                return HttpResponseRedirect(request.session['Forgot_Password'])

            # 創建Token，並寄給使用者
            token = token_confirm.generate_validate_token(email)

            message = "\n".join([
                u'{0},'.format(usr_email.username),
                u'請訪問該連結，完成重設密碼:',
                '/'.join(
                    ['http://{0}'.format(settings.SERVER_IP), 'user/forgotpsw', token])
            ])
            email = EmailMessage(
                '重設密碼',
                message,
                '三甲科技<aaa@test.com>',
                [email]
            )
            email.send()
            messages.success(self.request, '發送成功')
            return HttpResponseRedirect(request.session['Forgot_Password'])

        except Exception as e:
            messages.error(self.request, '發送失敗')
            return HttpResponseRedirect(request.session['Forgot_Password'])


class LogoutView(View):
    template_name = 'user/Logout.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        logout(request)
        return redirect(reverse('login'))
# Create your views here.
