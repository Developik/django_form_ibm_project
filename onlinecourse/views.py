from django.shortcuts import render
from django.http import HttpResponseRedirect
# <HINT> Import any new Models here
from .models import Course, Enrollment, Question, Choice, Submission
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)
# Create your views here.


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        # Check if user exists
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except:
            logger.error("New user")
        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                            password=password)
            login(request, user)
            return redirect("onlinecourse:index")
        else:
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    is_enrolled = False
    if user.id is not None:
        # Check if user enrolled
        num_results = Enrollment.objects.filter(user=user, course=course).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled


# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        # Create an enrollment
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))


# <HINT> Create a submit view to create an exam submission record for a course enrollment,
# you may implement it based on following logic:
         # Get user and course object, then get the associated enrollment object created when the user enrolled the course
         # Create a submission object referring to the enrollment
         # Collect the selected choices from exam form
         # Add each selected choice object to the submission object
         # Redirect to show_exam_result with the submission id
def submit(request, course_id):
    enroll_obj = Enrollment.objects.get(user=request.user, course=get_object_or_404(Course, pk=course_id))
    submitted_answers = []
    submiss_obj = Submission.objects.create(enrollment=enroll_obj)
# <HINT> A example method to collect the selected choices from the exam form from the request object
    def extract_answers(request):
        submitted_anwsers = []
        for key in request.POST:
            if key.startswith('choice'):
                value = request.POST[key]
                choice_id = int(value)
                submitted_anwsers.append(choice_id)
        return submitted_anwsers
    
    #if request.method == 'POST':
    submitted_answers = extract_answers(request)
    for this_id in submitted_answers:
        e = Choice.objects.get(id=this_id)
        submiss_obj.choices.add(e)
    
    return HttpResponseRedirect(reverse(viewname='onlinecourse:show_exam_result',
     args=(course_id, submiss_obj.id,)))


# <HINT> Create an exam result view to check if learner passed exam and show their question results and result for each question,
# you may implement it based on the following logic:
        # Get course and submission based on their ids
        # Get the selected choice ids from the submission record
        # For each selected choice, check if it is a correct answer or not
        # Calculate the total score
def show_exam_result(request, course_id, submission_id):
    course_obj=get_object_or_404(Course, pk=course_id)
    submission_obj = get_object_or_404(Submission, pk=submission_id)

    selected_choices = submission_obj.choices.all()
    selected_ids = []
    selected_question_ids = set()
    final_grade = 100
    choice_structure = []

    all_question_exist = \
         Question.objects.filter(lesson_id=course_id,)
    print("Numresult" + str(all_question_exist.count()))

    for item in selected_choices:
        selected_ids.append(item.id)
        selected_question_ids.add(item.question_id.id)

    count = 0
    for item in all_question_exist:
        choice_structure.append([])
    for item in all_question_exist:
        print("Final Grade : " + str(final_grade))
        choices_exist = Choice.objects.filter(question_id=item.id,)
        choices_exist_ids = []
        grade = True
        selec_ids = []

        # selec ids for curr question
        for curr_ch in selected_choices:
            print(curr_ch.question_id)
            print(item.id)
            if curr_ch.question_id.id == item.id:
                selec_ids.append(curr_ch.id)

        # 0 is not chosen (correct), black
        #  1 is not selected(wrong), yellow
        # 2 is correct chosen, green
        #  3 is incorrect chosen, red

        for curr_ch in choices_exist:

            if not (curr_ch in selected_choices)\
                and not curr_ch.is_correct:
                choice_structure[count].append(
                    ["black", curr_ch.choice_text])
            
            elif not (curr_ch in selected_choices):
                choice_structure[count].append(
                    ["rgb(255, 204, 0)", curr_ch.choice_text])

            elif (curr_ch in selected_choices)\
                and curr_ch.is_correct:
                choice_structure[count].append(
                    ["green", curr_ch.choice_text])
            
            else:
                choice_structure[count].append(
                    ["red", curr_ch.choice_text])

        print(selec_ids)

        grade = item.is_get_score(selec_ids)        


        
        if (not grade):
            final_grade = final_grade - \
                    (100 / all_question_exist.count())

        print("Final Grade : " + str(final_grade))

        count += 1

    if (final_grade < 1):
        final_grade = 0

    print('choice_struct:')
    print(choice_structure)
    print(selected_choices)
    #print(selected_choices[0])
    #print(selected_choices[0].question_id)
    #print(selected_choices[0].question_id.id)
    print("selected choices len:"+str(len(selected_choices)))
    print("all_question_ids:"+str(len(selected_question_ids)))

    print(str(final_grade))

    print("allquestions"+str(len(all_question_exist)))
    question_structure = []
    for item in range(len(all_question_exist)):
        question_structure.append([])
        question_structure[item] = [all_question_exist[item],
        choice_structure[item]]

    print(question_structure[0][0].question_text)

    context = {}
    context['course'] = course_obj
    context['selected_ids'] = selected_ids
    context['grade'] = round(final_grade, 2)
    context['questions'] = question_structure
    context['user'] = request.user
    return render(request, 'onlinecourse/exam_result_bootstrap.html',
     context)
            

