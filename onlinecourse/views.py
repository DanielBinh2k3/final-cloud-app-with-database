from django.shortcuts import render
from django.http import HttpResponseRedirect
# <HINT> Import any new Models here
from .models import Course, Enrollment, Submission, Choice
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
        num_results = Enrollment.objects.filter(
            user=user, course=course).count()
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
    user = request.user
    course = get_object_or_404(Course, id=course_id)
    enroll_ = Enrollment.objects.get(course=course, user=user)

    submit_exam = Submission.objects.create(enrollment=enroll_)
    submitted_answers = extract_answers(request)
    for choice_q in submitted_answers:
        choicee_ = Choice.objects.get(id=choice_q)
        submit_exam.choices.add(choicee_)
    submit_exam.save()
    return HttpResponseRedirect(reverse(viewname='onlinecourse:show_exam_result', args=(course_id, submit_exam.id)))


# <HINT> A example method to collect the selected choices from the exam form from the request object
def extract_answers(request):
    submitted_anwsers = []
    for key in request.POST:
        if key.startswith('choice'):
            value = request.POST[key]
            choice_id = int(value)
            submitted_anwsers.append(choice_id)
    return submitted_anwsers


# <HINT> Create an exam result view to check if learner passed exam and show their question results and result for each question,
# you may implement it based on the following logic:
    # Get course and submission based on their ids
    # Get the selected choice ids from the submission record
    # For each selected choice, check if it is a correct answer or not
    # Calculate the total score
def show_exam_result(request, course_id, submission_id):
    # Get the course and submission objects based on their IDs
    course = get_object_or_404(Course, id=course_id)
    submission = get_object_or_404(Submission, id=submission_id)

    # Get the selected choice IDs from the submission record
    selected_ids = submission.choices.values_list('id', flat=True)

    # Check each selected choice and calculate the learner's score
    learner_score = 0
    total_score = 0
    question_results = []

    for choice in submission.choices.all():
        question = choice.question
        is_correct = choice.is_correct
        total_score += question.grade
        grade = question.grade if is_correct else 0
        learner_score += grade
        correct_choices = question.choice_set.filter(is_correct=True)
        corrected_answer = ', '.join(
            [choice.text for choice in correct_choices])

        question_results.append({
            'question': question,
            'selected_choice': choice,
            'is_correct': is_correct,
            'corrected_answer': corrected_answer,
        })

    # Check if the learner passed the exam
    pass_score = (1/2)*total_score
    is_passed = learner_score >= pass_score

    context = {
        'course': course,
        'selected_ids': selected_ids,
        'grade': round(learner_score*100/total_score, 2),
        'total_score': total_score,
        'is_passed': is_passed,
        'question_results': question_results,
    }
    return render(request, 'onlinecourse/exam_result_bootstrap.html', context)
