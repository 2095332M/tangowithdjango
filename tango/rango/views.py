from django.shortcuts import render
from django.shortcuts import redirect

from django.http import HttpResponseRedirect, HttpResponse
from django.http import HttpResponse

from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.contrib.auth.models import User

from rango.models import UserProfile
from rango.models import Category
from rango.models import Page

from rango.forms import CategoryForm
from rango.forms import PageForm
from rango.forms import UserForm, UserProfileForm

from rango.bing_search import run_query

from datetime import datetime

@login_required
def restricted(request):
    return render(request, 'rango/restricted.html')

def track_url(request):
    page_id = None
    url = '/rango/'
    if request.method == 'GET':
        if 'page_id' in request.GET:
            page_id = request.GET['page_id']
            try:
                page = Page.objects.get(id=page_id)
                page.views = page.views + 1
                page.save()
                url = page.url
            except:
                pass

    return redirect(url)

def register(request):
    

    # A boolean value for telling the template whether the registration was successful.
    # Set to False initially. Code changes value to True when registration succeeds.
    registered = False
    
    # If it's a HTTP POST, we're interested in processing form data.
    if request.method == 'POST':
        # Attempt to grab information from the raw form information.
        # Note that we make use of both UserForm and UserProfileForm.
        user_form = UserForm(data=request.POST)
        profile_form = UserProfileForm(data=request.POST)
        
        # If the two forms are valid...
        if user_form.is_valid() and profile_form.is_valid():
            # Save the user's form data to the database.
            user = user_form.save()
            
            #Hash password and then update user object
            user.set_password(user.password)
            user.save()
            
            #Commit = false until the data is complete
            profile = profile_form.save(commit=False)
            profile.user = user
            
            #Check if user provided picture, we need it for UserProfile
            if 'picture' in request.FILES:
                profile.picture = request.FILES['picture']
        
            # Now we save the UserProfile model instance.
            profile.save()
    
            # Update our variable to tell the template registration was successful.
            registered = True
        
        # Invalid form or forms - mistakes or something else?
        # Print problems to the terminal.
        # They'll also be shown to the user.
        else:
            print user_form.errors, profile_form.errors

    # Not a HTTP POST, so we render our form using two ModelForm instances.
    # These forms will be blank, ready for user input.
    else:
        user_form = UserForm()
        profile_form = UserProfileForm()

    # Render the template depending on the context.
    return render(request,
                  'rango/register.html',
                  {'user_form': user_form, 'profile_form': profile_form, 'registered': registered} )



def user_login(request):
    
    # If the request is a HTTP POST, try to pull out the relevant information.
    if request.method == 'POST':
        # Gather the username and password provided by the user.
        # This information is obtained from the login form.
        username = request.POST['username']
        password = request.POST['password']
        
        # Use Django's machinery to attempt to see if the username/password
        # combination is valid - a User object is returned if it is.
        user = authenticate(username=username, password=password)
        
        # If we have a User object, the details are correct.
        # If None (Python's way of representing the absence of a value), no user
        # with matching credentials was found.
        if user:
            # Is the account active? It could have been disabled.
            if user.is_active:
                # If the account is valid and active, we can log the user in.
                # We'll send the user back to the homepage.
                login(request, user)
                return HttpResponseRedirect('/rango/')
            else:
                # An inactive account was used - no logging in!
                return HttpResponse("Your Rango account is disabled.")
        else:
            #
            #False if exists, True otherwise
            if (not User.objects.filter(username=username).count()):
                print "Invalid login details: {0}, {1}".format(username, password)
                return HttpResponse('Username doesn\'t exist<br /> <a href="/rango/login/">Return to login</a>')
            #If the username exists, then the password must be wrong
            else:
                print "Invalid login details: {0}, {1}".format(username, password)
                return HttpResponse('Incorrect Password for given Username<br /> <a href="/rango/login/">Return to login</a>')


    # The request is not a HTTP POST, so display the login form.
    # This scenario would most likely be a HTTP GET.
    else:
    # No context variables to pass to the template system, hence the
    # blank dictionary object...
        return render(request, 'rango/login.html', {})

# Use the login_required() decorator to ensure only those logged in can access the view.
@login_required
def user_logout(request):
    # Since we know the user is logged in, we can now just log them out.
    logout(request)
    
    # Take the user back to the homepage.
    return HttpResponseRedirect('/rango/add_profile/')




@login_required
def add_page(request, category_name_slug):

    try:
        cat = Category.objects.get(slug=category_name_slug)
    except Category.DoesNotExist:
                cat = None

    if request.method == 'POST':
        form = PageForm(request.POST)
        if form.is_valid():
            if cat:
                page = form.save(commit=False)
                page.category = cat
                page.views = 0
                page.save()
                return category(request, category_name_slug)
        else:
            print form.errors
    else:
        form = PageForm()

    context_dict = {'form':form, 'category': cat}

    return render(request, 'rango/add_page.html', context_dict)


def search(request):

    result_list = []

    if request.method == 'POST':
        query = request.POST['query'].strip()

        if query:
            # Run our Bing function to get the results list!
            result_list = run_query(query)

    return render(request, 'rango/search.html', {'result_list': result_list})


@login_required
def add_category(request):
    # A HTTP POST?
    if request.method == 'POST':
        form = CategoryForm(request.POST)

        # Have we been provided with a valid form?
        if form.is_valid():
            # Save the new category to the database.
            form.save(commit=True)

            # Now call the index() view.
            # The user will be shown the homepage.
            return index(request)
        else:
            # The supplied form contained errors - just print them to the terminal.
            print form.errors
    else:
        # If the request was not a POST, display the form to enter details.
        form = CategoryForm()

    # Bad form (or form details), no form supplied...
    # Render the form with error messages (if any).
    return render(request, 'rango/add_category.html', {'form': form})

def category(request, category_name_slug):
    category = Category.objects.get(slug=category_name_slug)
    # Create a context dictionary which we can pass to the template rendering engine.
    context_dict = {}
    context_dict['result_list'] = None
    context_dict['query'] = category.name
    if request.method == 'POST':
        query = request.POST.get('query', '').strip()
        
        if query:
            # Run our Bing function to get the results list!
            result_list = run_query(query)
            
            context_dict['result_list'] = result_list
            context_dict['query'] = query

    try:
        context_dict['category_name'] = category.name

        pages = Page.objects.filter(category=category)

        context_dict['pages'] = pages
        context_dict['category'] = category
    except Category.DoesNotExist:
        pass
    context_dict['category_name_slug'] = category.slug
    return render(request, 'rango/category.html', context_dict)


def index(request):
    
    category_list = Category.objects.order_by('-likes')[:5]
    pages_list = Page.objects.order_by('-views')[:5]
    context_dict = {'categories': category_list, 'pages': pages_list,}
    
    visits = request.session.get('visits')
    if not visits:
        visits = 1
    reset_last_visit_time = False

    last_visit = request.session.get('last_visit')
    if last_visit:
        last_visit_time = datetime.strptime(last_visit[:-7], "%Y-%m-%d %H:%M:%S")

        if (datetime.now() - last_visit_time).seconds > 0:
            # ...reassign the value of the cookie to +1 of what it was before...
            visits = visits + 1
            # ...and update the last visit cookie, too.
            reset_last_visit_time = True
    else:
        # Cookie last_visit doesn't exist, so create it to the current date/time.
        reset_last_visit_time = True

    if reset_last_visit_time:
        request.session['last_visit'] = str(datetime.now())
        request.session['visits'] = visits
    context_dict['visits'] = visits


    response = render(request,'rango/index.html', context_dict)

    return response

def register_profile(request):
    if request.method == 'POST':
        user_profile_form = UserProfileForm(request.POST)
        if user_profile_form.is_valid():
            if request.user.is_authenticated():
                user_profile = user_profile_form.save(commit = False)
                user = User.objects.get(id=request.user.id)
                user_profile.user = user
                if 'picture' in request.FILES:
                    user_profile.picture = request.FILES['picture']
                user_profile.website = user_profile_form.cleaned_data['website']
                user_profile.save()
        return redirect('/rango/profile')
    else:
        user_profile_form = UserProfileForm()
    return render(request,'rango/profile_registration.html', {'profile_form': user_profile_form})

@login_required
def profile(request):
    user = User.objects.get(username=request.user.username)
    profile = UserProfile.objects.get(user_id=user.id)
    context_dict = { 'user' : user, 'userprofile': profile}
    return render(request,'rango/profile.html',context_dict)

@login_required
def edit_profile(request):
    if request.method == 'POST':
        user_profile_form = UserProfileForm(request.POST)
        if user_profile_form.is_valid():
            if request.user.is_authenticated():
                user_profile = UserProfile.objects.get(user_id=request.user.id)
                if 'picture' in request.FILES:
                    user_profile.picture = request.FILES['picture']
                if 'website' in user_profile_form.cleaned_data:
                    user_profile.website = user_profile_form.cleaned_data['website']
                user_profile.save()
    

        return redirect('rango/profile')
    else:
        user_profile_form = UserProfileForm()
    return render(request,'rango/edit_profile.html', {'profile_form': user_profile_form})

def bad_request(request):
    return render(request,'rango/bad_request.html')

def about(request):
    
    if request.session.get('visits'):
        count = request.session.get('visits')
    else:
        count = 0

    return render(request, 'rango/about.html', {'visits': count})
